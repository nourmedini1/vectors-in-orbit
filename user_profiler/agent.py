import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm 
from .events import *
from .tools import (
    ensure_collections, ReinforcePositiveTaste, LearnNegativeTaste, UpdateBrandAffinity,
    UpdateSizeAffinity, AddPsychographicTrait, LogLifeEvent, UpdateDemographics, 
    ProcessTransactionStats, FlagPriceHesitation, SetAspirationalBudget, UpdateSeasonality, 
    SetActiveSearchIntent, AddPassiveWishlistIntent, FulfillIntent
)

load_dotenv()
ensure_collections()
mixtral_llm = LiteLlm(model="mistral/mistral-small-latest")

# Tool instances
reinforce_positive_taste = ReinforcePositiveTaste()
learn_negative_taste = LearnNegativeTaste()
update_brand_affinity = UpdateBrandAffinity()
update_size_affinity = UpdateSizeAffinity()
add_psychographic_trait = AddPsychographicTrait()
log_life_event = LogLifeEvent()
update_demographics = UpdateDemographics()
process_transaction_stats = ProcessTransactionStats()
flag_price_hesitation = FlagPriceHesitation()
set_aspirational_budget = SetAspirationalBudget()
update_seasonality = UpdateSeasonality()
set_active_search_intent = SetActiveSearchIntent()
add_passive_wishlist_intent = AddPassiveWishlistIntent()
fulfill_intent = FulfillIntent()

tools_instances = [
    reinforce_positive_taste, learn_negative_taste, update_brand_affinity, update_size_affinity,
    add_psychographic_trait, log_life_event, update_demographics, process_transaction_stats,
    flag_price_hesitation, set_aspirational_budget, update_seasonality, set_active_search_intent,
    add_passive_wishlist_intent, fulfill_intent
]

# Unique wrappers
def reinforce_positive_taste_tool(user_id: str, concept_text: str, weight: float): return reinforce_positive_taste.execute(user_id, concept_text, weight)
def learn_negative_taste_tool(user_id: str, concept_text: str, weight: float, reason_category: str): return learn_negative_taste.execute(user_id, concept_text, weight, reason_category)
def update_brand_affinity_tool(user_id: str, brand_name: str, increment: float): return update_brand_affinity.execute(user_id, brand_name, increment)
def update_size_affinity_tool(user_id: str, size_code: str): return update_size_affinity.execute(user_id, size_code)
def add_psychographic_trait_tool(user_id: str, trait: str): return add_psychographic_trait.execute(user_id, trait)
def log_life_event_tool(user_id: str, event_name: str, expiry_days: int): return log_life_event.execute(user_id, event_name, expiry_days)
def update_demographics_tool(user_id: str, field: str, value: str): return update_demographics.execute(user_id, field, value)
def process_transaction_stats_tool(user_id: str, amount: float, category: str, is_discount: bool, is_luxury: bool, is_installment: bool): return process_transaction_stats.execute(user_id, amount, category, is_discount, is_luxury, is_installment)
def flag_price_hesitation_tool(user_id: str, category: str, item_price: float): return flag_price_hesitation.execute(user_id, category, item_price)
def set_aspirational_budget_tool(user_id: str, category: str, min_budget: float, max_budget: float): return set_aspirational_budget.execute(user_id, category, min_budget, max_budget)
def update_seasonality_tool(user_id: str, month: int): return update_seasonality.execute(user_id, month)
def set_active_search_intent_tool(user_id: str, raw_query: str, expanded_keywords: str, filters: dict): return set_active_search_intent.execute(user_id, raw_query, expanded_keywords, filters)
def add_passive_wishlist_intent_tool(user_id: str, product_desc: str, image_url: str, urgency_days: int, budget_min: float, budget_max: float): return add_passive_wishlist_intent.execute(user_id, product_desc, image_url, urgency_days, budget_min, budget_max)
def fulfill_intent_tool(user_id: str, product_id: str, category: str): return fulfill_intent.execute(user_id, product_id, category)

tool_functions = [
    reinforce_positive_taste_tool, learn_negative_taste_tool, update_brand_affinity_tool,
    update_size_affinity_tool, add_psychographic_trait_tool, log_life_event_tool,
    update_demographics_tool, process_transaction_stats_tool, flag_price_hesitation_tool,
    set_aspirational_budget_tool, update_seasonality_tool, set_active_search_intent_tool,
    add_passive_wishlist_intent_tool, fulfill_intent_tool
]

def construct_system_prompt() -> str:
    return f"""
<system_context>
    <role>You are the **Chief User Profiler** (AI Agent). Translate e-commerce events into a Context-Aware User Profile in Qdrant.</role>
    <mandate>Process EVERY event type. Accuracy and logical deduction are paramount.</mandate>
</system_context>

<available_tools>
{chr(10).join([t.build_prompt() for t in tools_instances])}
</available_tools>

<data_models_reference>
    1. ProfileCreatedEvent: age, gender, region, status, device, ip_address.
    2. ProfileUpdatedEvent: updated_fields, new_values.
    3. PurchaseMadeEvent: price, total_amount, installment_plan, discount_applied, payment_method.
    4. WishlistAddedEvent: budget_min/max, urgency_days, desired_attributes, image_url, wishlist_notes.
    5. WishlistRemovedEvent: item_description.
    6. AddToCartEvent: price, product_id, quantity.
    7. RemoveFromCartEvent: price, product_id.
    8. ReviewSubmittedEvent: rating, review_text.
    9. ReturnRefundEvent: reason, condition, refund_amount.
    10. SearchPerformedEvent: query, filters.
    11. FilterAppliedEvent: filters.
</data_models_reference>

<reasoning_protocols>
    <protocol event="ProfileCreatedEvent"><action>Call UpdateDemographics for: age, gender, region, status, device.</action></protocol>
    <protocol event="ProfileUpdatedEvent"><action>Iterate new_values. Call UpdateDemographics.</action></protocol>
    <protocol event="PurchaseMadeEvent">
        <action>
            1. Financials: Call ProcessTransactionStats (discount, luxury, installment).
            2. Preferences: UpdateBrandAffinity (+1.0).
            3. Seasonality: UpdateSeasonality.
            4. Context: FulfillIntent.
            5. Taste: ReinforcePositiveTaste (weight=0.5).
            6. Traits: Check payment_method/product for AddPsychographicTrait.
        </action>
    </protocol>
    <protocol event="WishlistAddedEvent">
        <action>
            1. Intent: AddPassiveWishlistIntent.
            2. Aspirations: SetAspirationalBudget.
            3. Life Events: Analyze notes -> LogLifeEvent.
        </action>
    </protocol>
    <protocol event="WishlistRemovedEvent">
        <action>1. If no Purchase, treat as loss of interest. 2. LearnNegativeTaste (weight=0.2).</action>
    </protocol>
    <protocol event="AddToCartEvent"><action>1. ReinforcePositiveTaste (0.3). 2. UpdateBrandAffinity (0.2).</action></protocol>
    <protocol event="RemoveFromCartEvent"><action>1. FlagPriceHesitation. 2. LearnNegativeTaste (0.2).</action></protocol>
    <protocol event="ReviewSubmittedEvent">
        <action>
            1. Rating >= 4: ReinforcePositiveTaste (0.3).
            2. Rating <= 2: LearnNegativeTaste (0.8).
            3. Traits: Analyze text -> AddPsychographicTrait.
        </action>
    </protocol>
    <protocol event="ReturnRefundEvent">
        <action>
            1. IF reason implies Preference -> LearnNegativeTaste (0.5).
            2. IF "Found cheaper" -> FlagPriceHesitation.
        </action>
    </protocol>
    <protocol event="SearchPerformedEvent"><action>1. SetActiveSearchIntent. 2. LogLifeEvent. 3. AddPsychographicTrait.</action></protocol>
    <protocol event="FilterAppliedEvent"><action>1. 'brand' -> UpdateBrandAffinity (+0.5). 2. 'size' -> UpdateSizeAffinity. 3. 'price' -> SetAspirationalBudget.</action></protocol>
</reasoning_protocols>

<precautions>
    <rule>Only use fields present in input. If null, pass None.</rule>
    <rule>Do not hallucinate. If value missing, assume default/None.</rule>
    <rule>Call MULTIPLE tools for a single event if needed.</rule>
</precautions>
"""

agent = LlmAgent(name="UserProfilingAgent", model=mixtral_llm, instruction=construct_system_prompt(), tools=tool_functions)
















