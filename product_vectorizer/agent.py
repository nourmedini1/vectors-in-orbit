import os, sys
from dotenv import load_dotenv
from typing import Union, List, Optional
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm 
import litellm

load_dotenv(override=True)
try:
    from .events import *
    from .tools import (ensure_product_collections, UpsertProductProfile, EvolveTypicalUser, TrackInteraction, LogReviewInsights, ProcessReturnImpact)
except ImportError:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path: sys.path.insert(0, repo_root)
    from product_vectorizer.events import *
    from product_vectorizer.tools import *

# Debug: Check environment variable
api_key = os.getenv("MISTRAL_API_KEY")
if not api_key:
    print("CRITICAL WARNING: MISTRAL_API_KEY is not set in environment variables within agent.py")
else:
    print(f"DEBUG: agent.py sees MISTRAL_API_KEY: {api_key[:4]}...{api_key[-4:]}")
    # Explicitly set the key for litellm to avoid ambiguity
    os.environ["MISTRAL_API_KEY"] = api_key
    litellm.api_key = api_key

# --- LITELMM LOGGING ---
def log_pre_call(kwargs):
    print(f"\n📡 [LLM CALL START] Model: {kwargs.get('model')} | Params: {list(kwargs.keys())}")

def log_post_call(kwargs, response, start, end):
    usage = response.get('usage', {}) if response else {}
    print(f"✅ [LLM CALL END] Time: {end-start:.2f}s | Tokens: {usage.get('total_tokens', '?')}")

litellm.input_callback = [log_pre_call]
litellm.success_callback = [log_post_call]
# -----------------------

mixtral_llm = LiteLlm(model="mistral/mistral-small-latest")
ensure_product_collections()

upsert_profile_tool = UpsertProductProfile()
evolve_user_tool = EvolveTypicalUser()
track_interaction_tool = TrackInteraction()
log_review_tool = LogReviewInsights()
process_return_tool = ProcessReturnImpact()

def upsert_product_profile(product_id: str, name: Optional[str] = None, description: Optional[str] = None, image_url: Optional[str] = None, category: Optional[str] = None, brand: Optional[str] = None, gender: Optional[str] = None, condition: Optional[str] = None, price: Optional[float] = None, stock_quantity: Optional[int] = None, region: Optional[str] = None, tags: Optional[list] = None, is_discounted: Optional[bool] = None):
    return upsert_profile_tool.execute(product_id, name, description, image_url, category, brand, gender, condition, price, stock_quantity, region, tags, is_discounted)

def evolve_typical_user(product_id: str, user_id: str): return evolve_user_tool.execute(product_id, user_id)
def track_interaction(product_id: str, interaction_type: str, desirability_delta: float): return track_interaction_tool.execute(product_id, interaction_type, desirability_delta)
def log_review_insights(product_id: str, sentiment_score: float, extracted_tags: list, is_quality_issue: bool): return log_review_tool.execute(product_id, sentiment_score, extracted_tags, is_quality_issue)
def process_return_impact(product_id: str, user_id: str, is_taste_mismatch: bool): return process_return_tool.execute(product_id, user_id, is_taste_mismatch)

tool_functions = [upsert_product_profile, evolve_typical_user, track_interaction, log_review_insights, process_return_impact]
tool_instances = [upsert_profile_tool, evolve_user_tool, track_interaction_tool, log_review_tool, process_return_tool]

def construct_system_prompt() -> str:
    return f"""
<system_context>
    <role>You are the **Product Vectorizer Agent**. Manage the "Living Product Profile" in Qdrant.</role>
    <mandate>
        1. Sync Catalog: Update vectors/metadata on adds/updates.
        2. Infer Missing Data: Brand/Gender from name/description.
        3. Evolve Profiles: Adjust "Typical User Vector" on purchases.
        4. Score Products: Adjust desirability on feedback.
    </mandate>
</system_context>
<available_tools>{chr(10).join([t.build_prompt() for t in tool_instances])}</available_tools>
<reasoning_protocols>

    <protocol event="ProductAddedEvent">
        <action>
            Call `UpsertProductProfile`.
            - **Direct Mapping**: Map `product_id`, `name`, `description`, `price`, `stock_quantity`, `tags`, `image_url` from the event.
            - **Inference**:
              - `brand`: If missing, extract from `name` (e.g. "Nike Air" -> "Nike").
              - `gender`: Infer from `name`/`category` (e.g. "Women's Dress" -> "Women", "Unisex Hoodie" -> "Unisex"). Default to "Unisex".
              - `condition`: Default to "New" if not specified.
              - `is_discounted`: Set to True if `discount` field > 0.
        </action>
    </protocol>

    <protocol event="ProductUpdatedEvent">
        <context>
            This event contains a `new_values` dictionary with ONLY the changed fields.
        </context>
        <action>
            Call `UpsertProductProfile`.
            - `product_id`: Take directly from event.
            - **Check `new_values`**: For every parameter in the tool (`name`, `price`, `stock_quantity`, etc.), check if it exists in `new_values`.
            - **Pass None**: If a field is NOT in `new_values`, you MUST pass `None`. Do not guess.
        </action>
    </protocol>

    <protocol event="PurchaseMadeEvent">
        <action>
            1. Call `EvolveTypicalUser` (product_id, user_id).
            2. Call `TrackInteraction` (type='buy', desirability_delta=0.5).
        </action>
    </protocol>

    <protocol event="AddToCartEvent">
        <action>
            Call `TrackInteraction` (type='add_to_cart', desirability_delta=0.1).
        </action>
    </protocol>

    <protocol event="RemoveFromCartEvent">
        <action>
            Call `TrackInteraction` (type='remove', desirability_delta=-0.15).
        </action>
    </protocol>

    <protocol event="ReviewSubmittedEvent">
        <logic>
            1. Analyze `review_text` for sentiment (-1.0 to 1.0).
            2. Extract keywords as `extracted_tags` (e.g., ["bad fit", "great color", "runs small"]).
            3. Check for quality issues (broken, defective) -> `is_quality_issue`.
        </logic>
        <action>
            Call `LogReviewInsights` with your analysis.
        </action>
    </protocol>

    <protocol event="ReturnRefundEvent">
        <logic>
            Check `reason`.
            - "Defect/Damaged" -> `is_taste_mismatch` = False.
            - "Don't like/Fit/Style" -> `is_taste_mismatch` = True.
        </logic>
        <action>
            Call `ProcessReturnImpact`.
        </action>
    </protocol>

</reasoning_protocols>
"""

agent = LlmAgent(
    name="ProductVectorizerAgent",
    model=mixtral_llm,
    instruction=construct_system_prompt(),
    tools=tool_functions,
)