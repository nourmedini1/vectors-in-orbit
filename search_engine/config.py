import os, torch
from pydantic_settings import BaseSettings

class Config(BaseSettings):
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    text_embed_dim: int = 1024
    visual_embed_dim: int = 512
    mistral_api_key: str = "1NvLgTmXU4DmLi2HRC0VJKQzGNcRWTC1"
    clip_model_id: str = "laion/CLIP-ViT-B-32-laion2B-s34B-b79K"
    weight_semantic: float = 0.5
    weight_price: float = 0.15
    weight_collaborative: float = 0.25
    weight_wishlist: float = 0.1
    default_purchasing_power: float = 500.0

    @property
    def device(self) -> str: return "cuda" if torch.cuda.is_available() else "cpu"

    class Config:
        env_file = ".env"
        extra = "ignore"