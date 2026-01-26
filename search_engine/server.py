from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
import uvicorn
import os, sys

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path: sys.path.insert(0, repo_root)

from search_engine.pipeline import RecommendationPipeline

pipeline_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline_instance
    print("Initializing Search Engine Pipeline...")
    pipeline_instance = RecommendationPipeline()
    print("Search Engine Pipeline Initialized.")
    yield
    pipeline_instance = None

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SearchRequest(BaseModel):
    user_id: str
    query_text: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 20

@app.post("/search")
async def search(request: SearchRequest):
    if not pipeline_instance: raise HTTPException(status_code=503, detail="Search engine not initialized")
    return {"results": pipeline_instance.execute(request.user_id, request.query_text, request.filters, request.limit)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)