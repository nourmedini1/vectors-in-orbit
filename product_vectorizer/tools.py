import os
import sys
from dotenv import load_dotenv

load_dotenv()

import requests
import torch
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from PIL import Image

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
from id_helpers import get_point_id

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, VectorParams, Distance, Filter, FieldCondition, MatchValue,
    ScalarQuantization, ScalarQuantizationConfig, ScalarType,
    HnswConfigDiff
)
from transformers import CLIPProcessor, CLIPModel
from sentence_transformers import SentenceTransformer

# ==========================================
# 1. CONFIGURATION & HELPERS
# ==========================================

class Config:
    def __init__(self) -> None:
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        
        # Dimensions matching Search Engine config
        self.text_embed_dim = int(os.getenv("TEXT_EMBED_DIM", 1024))
        self.visual_embed_dim = int(os.getenv("VISUAL_EMBED_DIM", 512))

        self.mistral_api_key = os.getenv("MISTRAL_API_KEY", "1NvLgTmXU4DmLi2HRC0VJKQzGNcRWTC1")
        self.clip_model_id = os.getenv("CLIP_MODEL_ID", "laion/CLIP-ViT-B-32-laion2B-s34B-b79K")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.qdrant = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        try:
            self.text_model = SentenceTransformer("BAAI/bge-m3", device=self.device)
        except Exception as e:
            print(f"Warning: Text Model load failed: {e}")
            self.text_model = None

        try:
            self.clip_model = CLIPModel.from_pretrained(self.clip_model_id).to(self.device)
            self.clip_processor = CLIPProcessor.from_pretrained(self.clip_model_id)
        except Exception as e:
            print(f"Warning: CLIP Model load failed: {e}")
            self.clip_model = None

class Helpers:
    def __init__(self, config: Config) -> None:
        self.config = config

    def is_null(self, value: Any) -> bool:
        return value is None or (isinstance(value, str) and not value.strip())

    def get_text_embedding(self, text: str) -> List[float]:
        if self.is_null(text) or not self.config.text_model:
            return [0.0] * self.config.text_embed_dim
        try:
            embedding = self.config.text_model.encode(text)
            return embedding.tolist()
        except Exception:
            return [0.0] * self.config.text_embed_dim

    def get_image_embedding(self, image_url: str) -> List[float]:
        if self.is_null(image_url) or not self.config.clip_model:
            return [0.0] * self.config.visual_embed_dim
        try:
            resp = requests.get(image_url, stream=True, timeout=5)
            resp.raise_for_status()
            img = Image.open(resp.raw)
            inputs = self.config.clip_processor(images=img, return_tensors="pt").to(self.config.device)
            with torch.no_grad():
                outputs = self.config.clip_model.get_image_features(**inputs)
            outputs = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
            return outputs.squeeze().tolist()
        except Exception:
            return [0.0] * self.config.visual_embed_dim

    def get_product_point(self, product_id: str) -> PointStruct:
        point_id = get_point_id(product_id)
        try:
            res = self.config.qdrant.retrieve(
                collection_name="products",
                ids=[point_id],
                with_vectors=True,
                with_payload=True
            )
            if res: return res[0]
        except: pass
        
        # Return Default Schema if not found
        return PointStruct(
            id=point_id,
            vector={
                "text_vector": [0.0] * self.config.text_embed_dim,
                "visual_vector": [0.0] * self.config.visual_embed_dim,
                "typical_user_vector": [0.0] * self.config.text_embed_dim
            },
            payload={
                "product_id": product_id,
                "metadata": {}, 
                "stats": {"purchase_count": 0, "view_count": 0, "add_to_cart_count": 0, "return_count": 0, "hesitation_count": 0},
                "scores": {"desirability_score": 0.5, "affordability_score": 0.5},
                "warnings": {"quality_flag": False},
                "review_data": {"extracted_tags": [], "sentiment_score": 0.0}
            }
        )

    def get_user_long_term_taste(self, user_id: str) -> Optional[List[float]]:
        user_uuid = get_point_id(user_id)
        try:
            res = self.config.qdrant.retrieve(
                collection_name="users",
                ids=[user_uuid],
                with_vectors=["long_term_taste"]
            )
            if res: return res[0].vector.get("long_term_taste")
        except: pass
        return None

config = Config()
helpers = Helpers(config)

def ensure_product_collections():
    # SCALABILITY OPTIMIZATIONS
    # 1. Quantization: Int8 for RAM efficiency
    quantization_config = ScalarQuantization(
        scalar=ScalarQuantizationConfig(
            type=ScalarType.INT8,
            always_ram=True,
            quantile=0.99,
        )
    )
    # 2. HNSW: Tuned for read-heavy workload
    hnsw_config = HnswConfigDiff(m=16, ef_construct=100, full_scan_threshold=1000)

    if not config.qdrant.collection_exists("products"):
        print("Creating products collection...")
        config.qdrant.create_collection(
            collection_name="products",
            vectors_config={
                # on_disk=True allows massive catalogs > RAM size
                "text_vector": VectorParams(size=config.text_embed_dim, distance=Distance.COSINE, on_disk=True),
                "visual_vector": VectorParams(size=config.visual_embed_dim, distance=Distance.COSINE, on_disk=True),
                "typical_user_vector": VectorParams(size=config.text_embed_dim, distance=Distance.COSINE, on_disk=True),
            },
            quantization_config=quantization_config,
            hnsw_config=hnsw_config
        )
    else:
        print("products collection already exists.")

# ==========================================
# 2. TOOLS
# ==========================================

class Tool(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs): pass
    def build_prompt(self) -> str: pass


class UpsertProductProfile(Tool):
    def build_prompt(self):
        return """
<tool name='UpsertProductProfile'>
    <when to use>ProductAdded OR ProductUpdated events.</when to use>
    <purpose>Initializes or updates vectors and metadata. Handles partial updates gracefully.</purpose>
    <note>Pass 'None' for fields that haven't changed.</note>
    <params>
        <param name='product_id' type='str'>Unique product ID</param>
        <param name='name' type='str' nullable='true'>Product Name</param>
        <param name='description' type='str' nullable='true'>Description</param>
        <param name='image_url' type='str' nullable='true'>Image URL</param>
        <param name='category' type='str' nullable='true'>Category</param>
        <param name='brand' type='str' nullable='true'>Brand Name (Infer if missing)</param>
        <param name='gender' type='str' nullable='true'>Target Gender (Men, Women, Unisex, Kids)</param>
        <param name='condition' type='str' nullable='true'>Condition (New, Used, Refurbished)</param>
        <param name='price' type='float' nullable='true'>Price</param>
        <param name='stock_quantity' type='int' nullable='true'>Stock Count</param>
        <param name='region' type='str' nullable='true'>Region Code (e.g., TN)</param>
        <param name='tags' type='list' nullable='true'>List of tags</param>
        <param name='is_discounted' type='bool' nullable='true'>Is item on sale?</param>
    </params>
</tool>
"""

    def execute(self, product_id: str, name: Optional[str] = None, description: Optional[str] = None, 
                image_url: Optional[str] = None, category: Optional[str] = None, 
                brand: Optional[str] = None, gender: Optional[str] = None,
                condition: Optional[str] = None, price: Optional[float] = None,
                stock_quantity: Optional[int] = None, region: Optional[str] = None,
                tags: Optional[List[str]] = None, is_discounted: Optional[bool] = None):
        try:
            # 1. Fetch Existing
            existing = helpers.get_product_point(product_id)
            payload = existing.payload
            vectors = existing.vector
            
            # Ensure Payload Structure
            meta = payload.setdefault("metadata", {})
            payload.setdefault("stats", {"purchase_count": 0, "view_count": 0, "add_to_cart_count": 0, "return_count": 0, "hesitation_count": 0})
            payload.setdefault("scores", {"desirability_score": 0.5})
            payload.setdefault("warnings", {"quality_flag": False})

            # 2. Update Text Vector? (If semantic content changed)
            new_name = name or meta.get("name", "")
            new_desc = description or meta.get("description", "")
            new_tags = tags or meta.get("tags", [])
            new_brand = brand or meta.get("brand", "")
            
            if name or description or tags or brand:
                text_content = f"{new_name} {new_brand} {new_desc} {' '.join(new_tags)}"
                vectors["text_vector"] = helpers.get_text_embedding(text_content)

            # 3. Update Visual Vector?
            if image_url:
                v_vec = helpers.get_image_embedding(image_url)
                if any(x != 0 for x in v_vec): # Only update if successful
                    vectors["visual_vector"] = v_vec

            # 4. Merge Metadata (Upsert Logic)
            payload["product_id"] = product_id
            if name: meta["name"] = name
            if description: meta["description"] = description
            if category: meta["category"] = category
            if brand: meta["brand"] = brand
            if gender: meta["gender"] = gender
            if condition: meta["condition"] = condition
            if price is not None: meta["price"] = price
            if stock_quantity is not None: meta["stock_quantity"] = stock_quantity
            if region: meta["region"] = region
            if tags is not None: meta["tags"] = tags
            if is_discounted is not None: meta["is_discounted"] = is_discounted
            
            if image_url: meta["image_url"] = image_url
            meta["updated_at"] = datetime.now().isoformat()
            if "created_at" not in meta:
                meta["created_at"] = datetime.now().isoformat()

            payload["metadata"] = meta

            # 5. Upsert
            point_id = get_point_id(product_id)
            config.qdrant.upsert(
                collection_name="products",
                points=[PointStruct(id=point_id, vector=vectors, payload=payload)]
            )
            return f"success: product {product_id} profile updated"
        except Exception as e:
            return f"error: {e}"


class EvolveTypicalUser(Tool):
    def build_prompt(self):
        return """
<tool name='EvolveTypicalUser'>
    <when to use>PurchaseMadeEvent</when to use>
    <purpose>Updates the 'typical_user_vector' by averaging it with the buyer's taste profile.</purpose>
    <params>
        <param name='product_id' type='str'>Product ID</param>
        <param name='user_id' type='str'>Buyer User ID</param>
    </params>
</tool>
"""
    def execute(self, product_id: str, user_id: str):
        try:
            buyer_vec = helpers.get_user_long_term_taste(user_id)
            if not buyer_vec:
                return "error: buyer profile not found, cannot evolve"

            product = helpers.get_product_point(product_id)
            current_typ_vec = product.vector.get("typical_user_vector", [0.0]*config.text_embed_dim)
            
            stats = product.payload.setdefault("stats", {})
            N = stats.get("purchase_count", 0)
            
            # Check if initialized (if all zeros, N=0)
            if all(v == 0.0 for v in current_typ_vec): N = 0

            # Cumulative Moving Average
            new_vec = []
            for c, b in zip(current_typ_vec, buyer_vec):
                val = ((c * N) + b) / (N + 1)
                new_vec.append(val)

            stats["purchase_count"] = N + 1
            product.payload["stats"] = stats
            product.vector["typical_user_vector"] = new_vec
            
            point_id = get_point_id(product_id)
            config.qdrant.upsert(
                collection_name="products",
                points=[PointStruct(id=point_id, vector=product.vector, payload=product.payload)]
            )
            return f"success: typical user evolved (N={N+1})"
        except Exception as e:
            return f"error: {e}"


class TrackInteraction(Tool):
    def build_prompt(self): return "<tool name='TrackInteraction'><when to use>AddToCart, RemoveFromCart, PurchaseMade</when><purpose>Update stats & desirability</purpose><params><param name='product_id' type='str'/><param name='interaction_type' type='str'>(view, add_to_cart, purchase, return, hesitation)</param><param name='desirability_delta' type='float'>(-1.0 to 1.0)</param></params></tool>"

    def execute(self, product_id: str, interaction_type: str, desirability_delta: float):
        try:
            pt = helpers.get_product_point(product_id)
            stats, scores = pt.payload.setdefault("stats", {}), pt.payload.setdefault("scores", {})
            
            key_map = {"add": "add_to_cart_count", "buy": "purchase_count", "remove": "hesitation_count"}
            key = key_map.get(interaction_type, f"{interaction_type}_count")
            stats[key] = stats.get(key, 0) + 1
            scores["desirability_score"] = max(0.0, min(1.0, scores.get("desirability_score", 0.5) + desirability_delta))
            
            helpers.upsert_product(product_id, pt.vector, pt.payload)
            return "success: interaction tracked"
        except Exception as e: return f"error: {e}"



class LogReviewInsights(Tool):
    def build_prompt(self): return "<tool name='LogReviewInsights'><when to use>ReviewSubmittedEvent</when><purpose>Extract keywords, adjust score</purpose><params><param name='product_id' type='str'/><param name='sentiment_score' type='float'>(-1.0 to 1.0)</param><param name='extracted_tags' type='list'/><param name='is_quality_issue' type='bool'/></params></tool>"

    def execute(self, product_id: str, sentiment_score: float, extracted_tags: List[str], is_quality_issue: bool):
        try:
            pt = helpers.get_product_point(product_id)
            rd = pt.payload.setdefault("review_data", {}); rd["extracted_tags"] = list(set(rd.get("extracted_tags", [])) | set(extracted_tags or [])); rd["sentiment_score"] = sentiment_score
            if is_quality_issue: pt.payload.setdefault("warnings", {})["quality_flag"] = True
            
            sc = pt.payload.setdefault("scores", {}); sc["desirability_score"] = max(0.0, min(1.0, sc.get("desirability_score", 0.5) + sentiment_score * 0.1))
            helpers.upsert_product(product_id, pt.vector, pt.payload)
            return "success: review insights logged"
        except Exception as e: return f"error: {e}"

class ProcessReturnImpact(Tool):
    def build_prompt(self): return "<tool name='ProcessReturnImpact'><when to use>ReturnRefundEvent</when><purpose>Penalize score, negative learning</purpose><params><param name='product_id' type='str'/><param name='user_id' type='str'/><param name='is_taste_mismatch' type='bool'/></params></tool>"

    def execute(self, product_id: str, user_id: str, is_taste_mismatch: bool):
        try:
            pt = helpers.get_product_point(product_id)
            st, sc = pt.payload.setdefault("stats", {}), pt.payload.setdefault("scores", {})
            st["return_count"] = st.get("return_count", 0) + 1; sc["desirability_score"] = max(0.0, sc.get("desirability_score", 0.5) - 0.15)
            
            if is_taste_mismatch and (bv := helpers.get_user_long_term_taste(user_id)):
                pt.vector["typical_user_vector"] = [(c - (b * 0.05)) for c, b in zip(pt.vector.get("typical_user_vector", [0.0]*config.text_embed_dim), bv)]
                
            helpers.upsert_product(product_id, pt.vector, pt.payload)
            return "success: return processed"
        except Exception as e: return f"error: {e}"
