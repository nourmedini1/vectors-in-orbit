import os, sys, torch, requests
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from PIL import Image
from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue, ScalarQuantization, ScalarQuantizationConfig, ScalarType, HnswConfigDiff
from transformers import CLIPProcessor, CLIPModel
from sentence_transformers import SentenceTransformer

load_dotenv()
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path: sys.path.insert(0, repo_root)
from id_helpers import get_point_id

class Config:
    def __init__(self) -> None:
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        self.text_embed_dim = int(os.getenv("TEXT_EMBED_DIM", 1024))
        self.visual_embed_dim = int(os.getenv("VISUAL_EMBED_DIM", 512))
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.qdrant = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        
        try: self.text_model = SentenceTransformer("BAAI/bge-m3", device=self.device)
        except Exception: self.text_model = None

        self.clip_model, self.clip_processor, self.clip_load_error = None, None, None
        try:
            self.clip_model = CLIPModel.from_pretrained(os.getenv("CLIP_MODEL_ID", "laion/CLIP-ViT-B-32-laion2B-s34B-b79K")).to(self.device)
            self.clip_processor = CLIPProcessor.from_pretrained(os.getenv("CLIP_MODEL_ID", "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"))
        except Exception as e: self.clip_load_error = e

class Helpers:
    def __init__(self, config: Config) -> None: self.config = config

    def get_text_embedding(self, text: str) -> Optional[List[float]]:
        if not text or not text.strip() or not self.config.text_model: return None
        try: return self.config.text_model.encode(text).tolist()
        except: return None

    def get_image_embedding(self, image_url: str) -> Optional[List[float]]:
        if not image_url or not image_url.strip() or not self.config.clip_model or not self.config.clip_processor: return None
        try:
            response = requests.get(image_url, stream=True, timeout=5)
            image = Image.open(response.raw)
            inputs = self.config.clip_processor(images=image, return_tensors="pt").to(self.config.device)
            with torch.no_grad():
                outputs = self.config.clip_model.get_image_features(**inputs)
            return (outputs / outputs.norm(p=2, dim=-1, keepdim=True)).squeeze().tolist()
        except: return None


    def user_point_id(self, user_id: str) -> str:
        return get_point_id(user_id)

    def upsert_user(self, user_id: str, vector: Dict[str, Any], payload: Dict[str, Any]) -> None:
        point_id = self.user_point_id(user_id)
        payload["user_id"] = user_id
        self.config.qdrant.upsert(
            collection_name="users",
            points=[PointStruct(id=point_id, vector=vector, payload=payload)]
        )

    def get_user_point(self, user_id: str, with_vectors: bool = False) -> PointStruct:
        if self.is_null(user_id):
            raise ValueError("user_id is required.")

        point_id = self.user_point_id(user_id)
        try:
            res = self.config.qdrant.retrieve(
                collection_name="users",
                ids=[point_id],
                with_payload=True,
                with_vectors=with_vectors
            )
            if res:
                return res[0]
        except Exception as e:
            raise RuntimeError(f"DB Retrieve Error: {e}") from e

        return PointStruct(
            id=point_id,
            vector={
                "long_term_taste": [0.0] * self.config.text_embed_dim,
                "negative_taste": [0.0] * self.config.text_embed_dim
            },
            payload={
                "user_id": user_id,
                "financials": {
                    "category_stats": {},
                    "global_ltv": 0.0,
                    "global_discount_affinity": 0.0,
                    "installment_affinity": 0.0,
                    "luxury_affinity": 0.0
                },
                "preferences": {"brand_affinity": {}, "size_affinity": {}},
                "demographics": {},
                "traits": [],
                "life_events": [],
                "dislikes": [],
                "seasonality": {"active_months": [], "is_holiday_shopper": False}
            }
        )

    @staticmethod
    def update_rolling_avg(current_avg: float, count: int, new_val: float) -> float:
        if count < 0:
            count = 0
        if current_avg is None:
            current_avg = 0.0
        return ((current_avg * count) + new_val) / (count + 1)


config = Config()
helpers = Helpers(config)


# ==========================================
# 4. INIT UTILS (OPTIMIZED)
# ==========================================

def ensure_collections():
    # Optimization Configuration
    # 1. Quantization: Compresses vectors to Int8 (4x RAM savings)
    # 2. Rescoring: Ensures high accuracy by using original vectors for top-k candidates
    quantization_config = ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            always_ram=True,  # Quantized index stays in RAM for speed
            quantile=0.99,    # Limits outlier impact on quantization
        )
    )

    # HNSW Tuning: Balance between indexing speed and search recall
    hnsw_config = HnswConfigDiff(
        m=32,               # Links per node (Higher = better accuracy, more RAM)
        ef_construct=200,   # Depth of search during index build
    )

    if not config.qdrant.collection_exists("users"):
        print("Creating users collection...")
        config.qdrant.create_collection(
            collection_name="users",
            vectors_config={
                "long_term_taste": VectorParams(
                    size=config.text_embed_dim, 
                    distance=Distance.COSINE,
                    on_disk=True # Keep heavy float32 vectors on disk, RAM has int8 index
                ),
                "negative_taste": VectorParams(
                    size=config.text_embed_dim, 
                    distance=Distance.COSINE,
                    on_disk=True
                ),
            },
            quantization_config=quantization_config,
            hnsw_config=hnsw_config
        )
    else:
        print("users collection already exists.")

    if not config.qdrant.collection_exists("user_intents"):
        print("Creating user_intents collection...")
        config.qdrant.create_collection(
            collection_name="user_intents",
            vectors_config={
                "intent_vector": VectorParams(
                    size=config.text_embed_dim, 
                    distance=Distance.COSINE
                ),
                "visual_vector": VectorParams(
                    size=config.visual_embed_dim, 
                    distance=Distance.COSINE
                )
            },
            quantization_config=quantization_config,
            hnsw_config=hnsw_config
        )
    else:
        print("user_intents collection already exists.")




class Tool(ABC):

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass

    def build_prompt(self) -> str:
        pass

    def _nullable_note(self) -> str:
        return "   <note>Parameters can be null; only act on non-null values.</note>"


class ReinforcePositiveTaste(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='ReinforcePositiveTaste'>",
            "   <when to use>",
            "       When the event is PurchaseMadeEvent OR AddToCartEvent OR ReviewSubmittedEvent with positive sentiment",
            "   </when to use>",
            "   <purpose>To make the positive taste embedded vector more aligned with this preference </purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='concept_text' type='str' nullable='true'>A textual description of the concept to reinforce</param>",
            "       <param name='weight' type='float' nullable='true'>A weight factor indicating the strength of reinforcement</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, concept_text: str, weight: float):
        try:
            if helpers.is_null(user_id) or helpers.is_null(concept_text) or weight is None:
                return "error: missing required params for ReinforcePositiveTaste"

            user = helpers.get_user_point(user_id, with_vectors=True)
            current_vec = user.vector.get("long_term_taste", [0.0] * config.text_embed_dim)
            target_vec = helpers.get_text_embedding(concept_text)
            if target_vec is None:
                return "error: concept_text was null"

            new_vec = [(c * (1 - weight)) + (t * weight) for c, t in zip(current_vec, target_vec)]

            user.vector["long_term_taste"] = new_vec
            helpers.upsert_user(user_id, user.vector, user.payload)
            return "success: positive taste reinforced"
        except Exception as e:
            return f"error: {e}"


class LearnNegativeTaste(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='LearnNegativeTaste'>",
            "   <when to use>",
            "       When the event is RemoveFromCartEvent OR ReviewSubmittedEvent with negative sentiment",
            "   </when to use>",
            "   <purpose>To adjust the user's taste vector away from the negative preference and the dislikes list</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='concept_text' type='str' nullable='true'>A textual description of the concept to avoid</param>",
            "       <param name='reason_category' type='str' nullable='true'>The category of the reason for dislike</param>",
            "       <param name='weight' type='float' nullable='true'>A weight factor indicating the strength of avoidance</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, concept_text: str, weight: float, reason_category: str):
        try:
            if helpers.is_null(user_id) or helpers.is_null(concept_text) or weight is None or helpers.is_null(reason_category):
                return "error: missing required params for LearnNegativeTaste"

            user = helpers.get_user_point(user_id, with_vectors=True)
            current_neg = user.vector.get("negative_taste", [0.0] * config.text_embed_dim)
            target_vec = helpers.get_text_embedding(concept_text)
            if target_vec is None:
                return "error: concept_text was null"

            new_neg = [(c * (1 - weight)) + (t * weight) for c, t in zip(current_neg, target_vec)]

            payload = user.payload
            payload.setdefault("dislikes", [])
            payload["dislikes"].append(f"{reason_category}: {concept_text}")

            user.vector["negative_taste"] = new_neg
            helpers.upsert_user(user_id, user.vector, payload)
            return "success: negative taste updated"
        except Exception as e:
            return f"error: {e}"


class UpdateBrandAffinity(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='UpdateBrandAffinity'>",
            "   <when to use>",
            "       PurchaseMade (+1.0) OR FilterApplied (+0.5) OR SearchPerformed (Brand specific)",
            "   </when to use>",
            "   <purpose>Updates payload.preferences.brand_affinity by incrementing the counter for a brand</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='brand_name' type='str' nullable='true'>The brand to increment</param>",
            "       <param name='increment' type='float' nullable='true'>The increment value</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, brand_name: str, increment: float):
        try:
            if helpers.is_null(user_id) or helpers.is_null(brand_name) or increment is None:
                return "error: missing required params for UpdateBrandAffinity"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            payload.setdefault("preferences", {})
            payload["preferences"].setdefault("brand_affinity", {})

            current_val = payload["preferences"]["brand_affinity"].get(brand_name, 0.0)
            payload["preferences"]["brand_affinity"][brand_name] = current_val + increment

            helpers.upsert_user(user_id, user.vector, payload)
            return "success: brand affinity updated"
        except Exception as e:
            return f"error: {e}"


class UpdateSizeAffinity(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='UpdateSizeAffinity'>",
            "   <when to use>",
            "       PurchaseMade OR FilterApplied",
            "   </when to use>",
            "   <purpose>Updates payload.preferences.size_affinity by tracking most frequent sizes</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='size_code' type='str' nullable='true'>Size code (e.g., M, L, 42)</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, size_code: str):
        try:
            if helpers.is_null(user_id) or helpers.is_null(size_code):
                return "error: missing required params for UpdateSizeAffinity"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            payload.setdefault("preferences", {})
            payload["preferences"].setdefault("size_affinity", {})

            current_val = payload["preferences"]["size_affinity"].get(size_code, 0)
            payload["preferences"]["size_affinity"][size_code] = current_val + 1

            helpers.upsert_user(user_id, user.vector, payload)
            return "success: size affinity updated"
        except Exception as e:
            return f"error: {e}"


class AddPsychographicTrait(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='AddPsychographicTrait'>",
            "   <when to use>",
            "       SearchPerformed (Contextual) OR PurchaseMade (Specific Category) OR ReviewSubmitted (Self-disclosure)",
            "   </when to use>",
            "   <purpose>Appends a unique tag to payload.traits</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='trait' type='str' nullable='true'>Psychographic trait (e.g., Gamer, Parent)</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, trait: str):
        try:
            if helpers.is_null(user_id) or helpers.is_null(trait):
                return "error: missing required params for AddPsychographicTrait"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            payload.setdefault("traits", [])
            if trait not in payload["traits"]:
                payload["traits"].append(trait)
                helpers.upsert_user(user_id, user.vector, payload)

            return "success: psychographic trait updated"
        except Exception as e:
            return f"error: {e}"


class LogLifeEvent(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='LogLifeEvent'>",
            "   <when to use>",
            "       SearchPerformed (e.g., 'wedding gift') OR WishlistAdded (e.g., 'baby crib')",
            "   </when to use>",
            "   <purpose>Appends to payload.life_events with timestamp and expiry</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='event_name' type='str' nullable='true'>Name of the life event</param>",
            "       <param name='expiry_days' type='int' nullable='true'>Days until event expires</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, event_name: str, expiry_days: int):
        try:
            if helpers.is_null(user_id) or helpers.is_null(event_name) or expiry_days is None:
                return "error: missing required params for LogLifeEvent"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            payload.setdefault("life_events", [])

            expiry_date = (datetime.now() + timedelta(days=expiry_days)).isoformat()
            payload["life_events"].append({
                "event": event_name,
                "created_at": datetime.now().isoformat(),
                "expires_at": expiry_date
            })

            helpers.upsert_user(user_id, user.vector, payload)
            return "success: life event logged"
        except Exception as e:
            return f"error: {e}"


class UpdateDemographics(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='UpdateDemographics'>",
            "   <when to use>",
            "       ProfileUpdated OR ProfileCreated",
            "   </when to use>",
            "   <purpose>Updates payload.demographics fields (Region, Age, Gender, Device, Status)</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='field' type='str' nullable='true'>Demographic field name</param>",
            "       <param name='value' type='str' nullable='true'>Demographic value</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, field: str, value: str):
        try:
            if helpers.is_null(user_id) or helpers.is_null(field) or helpers.is_null(value):
                return "error: missing required params for UpdateDemographics"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            payload.setdefault("demographics", {})
            payload["demographics"][field] = value

            helpers.upsert_user(user_id, user.vector, payload)
            return "success: demographics updated"
        except Exception as e:
            return f"error: {e}"


class ProcessTransactionStats(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='ProcessTransactionStats'>",
            "   <when to use>",
            "       PurchaseMade",
            "   </when to use>",
            "   <purpose>Updates payload.financials rolling averages and affinities</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='amount' type='float' nullable='true'>Transaction amount</param>",
            "       <param name='category' type='str' nullable='true'>Product category</param>",
            "       <param name='is_discount' type='bool' nullable='true'>Whether discounted</param>",
            "       <param name='is_luxury' type='bool' nullable='true'>Whether luxury item</param>",
            "       <param name='is_installment' type='bool' nullable='true'>Whether installment payment</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, amount: float, category: str, is_discount: bool, is_luxury: bool, is_installment: bool):
        try:
            if helpers.is_null(user_id) or helpers.is_null(category) or amount is None or is_discount is None or is_luxury is None or is_installment is None:
                return "error: missing required params for ProcessTransactionStats"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload
            fin = payload.get("financials", {})

            fin.setdefault("category_stats", {})
            cat_stats = fin["category_stats"].get(category, {"avg_spend": 0.0, "max_spend": 0.0, "count": 0})

            count = cat_stats["count"]
            cat_stats["avg_spend"] = helpers.update_rolling_avg(cat_stats["avg_spend"], count, amount)
            cat_stats["max_spend"] = max(cat_stats["max_spend"], amount)
            cat_stats["count"] = count + 1
            fin["category_stats"][category] = cat_stats

            fin["global_ltv"] = fin.get("global_ltv", 0.0) + amount

            total_tx = sum([c["count"] for c in fin["category_stats"].values()])

            fin["global_discount_affinity"] = helpers.update_rolling_avg(fin.get("global_discount_affinity", 0.0), total_tx - 1, 1.0 if is_discount else 0.0)
            fin["luxury_affinity"] = helpers.update_rolling_avg(fin.get("luxury_affinity", 0.0), total_tx - 1, 1.0 if is_luxury else 0.0)
            fin["installment_affinity"] = helpers.update_rolling_avg(fin.get("installment_affinity", 0.0), total_tx - 1, 1.0 if is_installment else 0.0)

            payload["financials"] = fin
            helpers.upsert_user(user_id, user.vector, payload)
            return "success: transaction stats updated"
        except Exception as e:
            return f"error: {e}"


class FlagPriceHesitation(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='FlagPriceHesitation'>",
            "   <when to use>",
            "       RemoveFromCart OR WishlistRemoved (without buying)",
            "   </when to use>",
            "   <purpose>Increments hesitation_count if item_price > category_avg_spend</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='category' type='str' nullable='true'>Product category</param>",
            "       <param name='item_price' type='float' nullable='true'>Price of removed item</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, category: str, item_price: float):
        try:
            if helpers.is_null(user_id) or helpers.is_null(category) or item_price is None:
                return "error: missing required params for FlagPriceHesitation"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            fin = payload.get("financials", {})
            cat_stats = fin.get("category_stats", {}).get(category)

            if cat_stats and cat_stats["avg_spend"] > 0:
                if item_price > (cat_stats["avg_spend"] * 1.2):
                    cat_stats["hesitation_count"] = cat_stats.get("hesitation_count", 0) + 1
                    fin["category_stats"][category] = cat_stats
                    payload["financials"] = fin
                    helpers.upsert_user(user_id, user.vector, payload)

            return "success: price hesitation processed"
        except Exception as e:
            return f"error: {e}"


class SetAspirationalBudget(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='SetAspirationalBudget'>",
            "   <when to use>",
            "       WishlistAdded (with budget fields) OR FilterApplied (Price range)",
            "   </when to use>",
            "   <purpose>Updates payload.financials.category_stats.<category>.wishlist_budget</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='category' type='str' nullable='true'>Product category</param>",
            "       <param name='min_budget' type='float' nullable='true'>Minimum budget</param>",
            "       <param name='max_budget' type='float' nullable='true'>Maximum budget</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, category: str, min_budget: float, max_budget: float):
        try:
            if helpers.is_null(user_id) or helpers.is_null(category) or min_budget is None or max_budget is None:
                return "error: missing required params for SetAspirationalBudget"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload
            fin = payload.get("financials", {})

            fin.setdefault("category_stats", {})
            fin["category_stats"].setdefault(category, {"avg_spend": 0.0, "count": 0, "max_spend": 0.0})

            fin["category_stats"][category]["wishlist_budget_min"] = min_budget
            fin["category_stats"][category]["wishlist_budget_max"] = max_budget

            payload["financials"] = fin
            helpers.upsert_user(user_id, user.vector, payload)
            return "success: aspirational budget set"
        except Exception as e:
            return f"error: {e}"


class UpdateSeasonality(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='UpdateSeasonality'>",
            "   <when to use>",
            "       PurchaseMade",
            "   </when to use>",
            "   <purpose>Adds month to payload.seasonality.active_months and checks Holiday Shopper flag</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='month' type='int' nullable='true'>Month number (1-12)</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, month: int):
        try:
            if helpers.is_null(user_id) or month is None:
                return "error: missing required params for UpdateSeasonality"

            user = helpers.get_user_point(user_id, with_vectors=True)
            payload = user.payload

            payload.setdefault("seasonality", {})
            active_months = set(payload["seasonality"].get("active_months", []))
            active_months.add(month)

            payload["seasonality"]["active_months"] = list(active_months)
            payload["seasonality"]["is_holiday_shopper"] = any(m in [11, 12, 1] for m in active_months)

            helpers.upsert_user(user_id, user.vector, payload)
            return "success: seasonality updated"
        except Exception as e:
            return f"error: {e}"


class SetActiveSearchIntent(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='SetActiveSearchIntent'>",
            "   <when to use>",
            "       SearchPerformed",
            "   </when to use>",
            "   <purpose>Upserts to user_intents (type: active_search) and deletes previous active searches for this user</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='raw_query' type='str' nullable='true'>Original search query</param>",
            "       <param name='expanded_keywords' type='str' nullable='true'>Expanded keywords</param>",
            "       <param name='filters' type='dict' nullable='true'>Applied filters</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, raw_query: str, expanded_keywords: str, filters: dict):
        try:
            if helpers.is_null(user_id) or helpers.is_null(raw_query):
                return "error: missing required params for SetActiveSearchIntent"

            expanded_keywords = expanded_keywords or ""
            filters = filters or {}

            full_text = f"{raw_query} {expanded_keywords}".strip()
            vector = helpers.get_text_embedding(full_text)
            if vector is None:
                return "error: query text was null"

            config.qdrant.delete(
                collection_name="user_intents",
                points_selector=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="type", match=MatchValue(value="active_search"))
                    ]
                )
            )

            intent_id = str(uuid4())
            config.qdrant.upsert(
                collection_name="user_intents",
                points=[PointStruct(
                    id=intent_id,
                    vector={"intent_vector": vector},
                    payload={
                        "user_id": user_id,
                        "type": "active_search",
                        "status": "active",
                        "query": raw_query,
                        "expanded_query": expanded_keywords,
                        "filters": filters,
                        "timestamp": datetime.now().isoformat()
                    }
                )]
            )
            return "success: active search intent set"
        except Exception as e:
            return f"error: {e}"


class AddPassiveWishlistIntent(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='AddPassiveWishlistIntent'>",
            "   <when to use>",
            "       WishlistAdded",
            "   </when to use>",
            "   <purpose>Upserts to user_intents (type: passive_wishlist) with urgency, budget info, AND visual embeddings</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='product_desc' type='str' nullable='true'>Product description</param>",
            "       <param name='image_url' type='str' nullable='true'>URL of the product image</param>",
            "       <param name='urgency_days' type='int' nullable='true'>Urgency window in days</param>",
            "       <param name='budget_min' type='float' nullable='true'>Minimum budget willing to spend</param>",
            "       <param name='budget_max' type='float' nullable='true'>Maximum budget willing to spend</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, product_desc: str, image_url: str, urgency_days: int, budget_min: float, budget_max: float):
        try:
            if helpers.is_null(user_id) or helpers.is_null(product_desc) or urgency_days is None or budget_min is None or budget_max is None:
                return "error: missing required params for AddPassiveWishlistIntent"

            text_vector = helpers.get_text_embedding(product_desc)
            if text_vector is None:
                return "error: product_desc was null"

            visual_vector = helpers.get_image_embedding(image_url)

            urgency_score = 1.0 / max(urgency_days, 1) if urgency_days is not None else 0.1

            # ✅ FIX: Keep uuid4() here since this is a NEW intent, not tied to user_id
            from uuid import uuid4
            intent_id = str(uuid4())

            vectors = {"intent_vector": text_vector}
            if visual_vector is not None:
                vectors["visual_vector"] = visual_vector

            config.qdrant.upsert(
                collection_name="user_intents",
                points=[PointStruct(
                    id=intent_id,
                    vector=vectors,
                    payload={
                        "user_id": user_id,
                        "type": "passive_wishlist",
                        "status": "active",
                        "product_desc": product_desc,
                        "has_image": bool(image_url),
                        "image_url": image_url,
                        "urgency_score": urgency_score,
                        "budget_min": budget_min,
                        "budget_max": budget_max,
                        "timestamp": datetime.now().isoformat()
                    }
                )]
            )
            return f"success: wishlist intent added ({intent_id})"
        except Exception as e:
            return f"error: {e}"


class FulfillIntent(Tool):

    def build_prompt(self):
        prompt_parts = [
            "<tool name='FulfillIntent'>",
            "   <when to use>",
            "       PurchaseMade",
            "   </when to use>",
            "   <purpose>Marks matching user_intents as fulfilled to stop recommending purchased items</purpose>",
            self._nullable_note(),
            "   <params>",
            "       <param name='user_id' type='str' nullable='true'>The unique identifier of the user</param>",
            "       <param name='product_id' type='str' nullable='true'>Purchased product ID</param>",
            "       <param name='category' type='str' nullable='true'>Product category</param>",
            "   </params>",
            "</tool>"
        ]
        return "\n".join(prompt_parts)

    def execute(self, user_id: str, product_id: str, category: str):
        try:
            if helpers.is_null(user_id) or helpers.is_null(product_id):
                return "error: missing required params for FulfillIntent"

            config.qdrant.set_payload(
                collection_name="user_intents",
                payload={"status": "fulfilled", "fulfilled_by": product_id},
                points=Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id)),
                        FieldCondition(key="status", match=MatchValue(value="active")),
                        FieldCondition(key="type", match=MatchValue(value="active_search"))
                    ]
                )
            )
            return "success: intent fulfilled"
        except Exception as e:
            return f"error: {e}"