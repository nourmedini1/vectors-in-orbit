import uuid
from typing import List, Dict, Any, Optional
from qdrant_client.models import Filter, FieldCondition, MatchValue
from id_helpers import get_point_id
from .config import Config
from .helpers import SearchHelpers
from .retrieval import RetrievalLayer
from .reranking import RerankingLayer
from .lexical import BM25Ranker
from .hybrid import HybridSearchEngine
from .search_logging import SearchLogger, StateExtractor, SearchAction

class RecommendationPipeline:
    def __init__(self):
        self.config, self.helpers = Config(), SearchHelpers(Config())
        self.client = self.helpers.qdrant
        self.retrieval_layer, self.reranking_layer = RetrievalLayer(helpers=self.helpers), RerankingLayer()
        self.bm25_ranker = BM25Ranker()
        self._build_lexical_index()
        self.hybrid_engine = HybridSearchEngine(retrieval_layer=self.retrieval_layer, bm25_ranker=self.bm25_ranker)
        
        # Initialize logging components
        self.logger = SearchLogger()
        self.state_extractor = StateExtractor()

    def _build_lexical_index(self):
        try:
            all_records, next_offset = [], None
            while True:
                batch, next_offset = self.client.scroll("products", limit=100, with_payload=True, with_vectors=False, offset=next_offset)
                all_records.extend(batch)
                if next_offset is None: break
            self.bm25_ranker.index_products([{**r.payload, 'id': r.id} for r in all_records])
        except: pass

    def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        user_uuid, context = get_point_id(user_id), {"profile": {}, "wishlist": []}
        try:
            res = self.client.retrieve("users", [user_uuid], with_vectors=True, with_payload=True)
            context["profile"] = {"vector": res[0].vector, "payload": res[0].payload} if res else {"vector": {}, "payload": {"financials": {"global_ltv": 0}}}
        except: context["profile"] = {"vector": {}, "payload": {"financials": {"global_ltv": 0}}}
        try:
            intents, _ = self.client.scroll("user_intents", scroll_filter=Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id)), FieldCondition(key="status", match=MatchValue(value="active")), FieldCondition(key="type", match=MatchValue(value="passive_wishlist"))]), limit=10, with_payload=True, with_vectors=True)
            context["wishlist"] = [{"vectors": i.vector, "payload": i.payload} for i in intents]
        except: pass
        return context

    def execute(self, user_id: str, query_text: str, explicit_filters: Optional[Dict[str, Any]] = None, limit: int = 20, session_id: Optional[str] = None, session_history: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Main execution pipeline with integrated logging.
        
        Args:
            user_id: User identifier
            query_text: Search query
            explicit_filters: Optional filters
            limit: Number of results
            session_id: Optional session ID for tracking
            session_history: Optional session history data
        
        Returns:
            List of ranked products
        """
        context = self._get_user_context(user_id)
        candidates = self.hybrid_engine.search(query=query_text, user_payload=context["profile"].get("payload", {}), explicit_filters=explicit_filters, limit=limit * 2)
        if not candidates: return []
        
        final_results = self.reranking_layer.rerank(candidates=candidates, query_text=query_text, user_profile=context["profile"], user_wishlist=context["wishlist"], top_n=limit * 2)
        
        # LOGGING: Capture state, action, and ranking for RL training
        try:
            session_data = {
                "session_id": session_id or str(uuid.uuid4()),
                "history": session_history or {}
            }
            
            state = self.state_extractor.extract_state(
                user_id=user_id,
                query_text=query_text,
                user_profile=context["profile"],
                candidates=candidates,
                session_data=session_data
            )
            
            action = self.reranking_layer.get_current_weights()
            
            ranking = [r["product_id"] for r in final_results]
            ranking_metadata = [
                {
                    "product_id": r["product_id"],
                    "price": r.get("price"),
                    "category": r.get("payload", {}).get("metadata", {}).get("category")
                }
                for r in final_results
            ]
            
            log_id = self.logger.log_search(
                state=state,
                action=action,
                ranking=ranking,
                ranking_metadata=ranking_metadata
            )
            
        except Exception as e:
            import traceback
            print(f"[Pipeline] ⚠️ Logging failed (non-critical): {e}")
            traceback.print_exc()
        
        return final_results[:limit]