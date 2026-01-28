from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import uvicorn
import os, sys
import asyncio
import uuid
from datetime import datetime

# Path setup to find search_engine module
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path: sys.path.insert(0, repo_root)

from search_engine.pipeline import RecommendationPipeline
from search_engine.feed import FeedPipeline
from kafka_broker import broker

# Global instances
search_pipeline = None
feed_pipeline = None

# Session storage (in-memory for now, use Redis for production)
session_histories: Dict[str, Dict[str, Any]] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global search_pipeline, feed_pipeline
    print("--- 🟢 INITIALIZING ENGINES ---")
    
    print("[1/2] Loading Search Pipeline (Intent + Hybrid + Reranking)...")
    search_pipeline = RecommendationPipeline()
    
    print("[2/2] Loading Feed Pipeline (Discovery + Personalization)...")
    feed_pipeline = FeedPipeline()
    
    print("[Broker] Starting Kafka Producer...")
    await broker.start()
    
    print("--- ✅ SYSTEM READY ---")
    yield
    # Cleanup
    search_pipeline = None
    feed_pipeline = None
    await broker.stop()

app = FastAPI(lifespan=lifespan, title="Nexus Neural Search")

# CORS
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# --- MODELS ---
class SearchRequest(BaseModel):
    user_id: str
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20

# --- ENDPOINTS ---

@app.get("/health")
async def health_check():
    if search_pipeline and feed_pipeline:
        return {"status": "healthy", "modules": ["search", "feed"]}
    return {"status": "initializing"}

@app.post("/search")
async def search(request: SearchRequest, http_request: Request, response: Response, background_tasks: BackgroundTasks):
    """
    Intent-Aware Hybrid Search with Session Tracking.
    Used when user TYPES a query.
    """
    if not search_pipeline: 
        raise HTTPException(status_code=503, detail="Search engine not ready")

    # Get or create session_id
    session_id = http_request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(key="session_id", value=session_id, max_age=86400)  # 24 hours
    
    # Get session history
    if session_id not in session_histories:
        session_histories[session_id] = {
            "search_count": 0,
            "click_count": 0,
            "duration_seconds": 0.0
        }
    
    session_history = session_histories[session_id]
    session_history["search_count"] += 1

    # Send Search Event to Kafka (Background Task)
    event_payload = {
        "user_id": request.user_id,
        "session_id": session_id,
        "query": request.query_text,
        "filters": request.filters,
        "timestamp": datetime.now().isoformat()
    }
    background_tasks.add_task(broker.send_event, "SearchPerformedEvent", event_payload)
    
    # Execute search with session context
    results = search_pipeline.execute(
        user_id=request.user_id,
        query_text=request.query_text,
        explicit_filters=request.filters,
        limit=request.limit,
        session_id=session_id,
        session_history=session_history
    )
    
    return {"results": results, "session_id": session_id}

@app.get("/feed/{user_id}")
async def get_feed(user_id: str):
    """
    Structured For-You Page.
    Used when user lands on Home Screen.
    Returns sections: [Inspired by Wishlist, Taste Match, Trending, Deals]
    """
    if not feed_pipeline: 
        raise HTTPException(status_code=503, detail="Feed engine not ready")
    
    structured_feed = feed_pipeline.generate(user_id)
    return {"feed": structured_feed}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)