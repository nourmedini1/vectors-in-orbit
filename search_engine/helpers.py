import requests, torch
from typing import List
from PIL import Image
from io import BytesIO
from qdrant_client import QdrantClient
from transformers import CLIPProcessor, CLIPModel
from sentence_transformers import SentenceTransformer
from .config import Config

class SearchHelpers:
    def __init__(self, config: Config):
        self.config = config
        self.qdrant = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        try: self.text_model = SentenceTransformer("BAAI/bge-m3", device="cpu")
        except: self.text_model = None
        try:
            self.clip_model = CLIPModel.from_pretrained(config.clip_model_id).to("cpu")
            self.clip_processor = CLIPProcessor.from_pretrained(config.clip_model_id)
        except: self.clip_model, self.clip_processor = None, None

    def get_text_embedding(self, text: str) -> List[float]:
        if not text or not self.text_model: return [0.0] * self.config.text_embed_dim
        try: return self.text_model.encode(text).tolist()
        except: return [0.0] * self.config.text_embed_dim

    def get_clip_text_embedding(self, text: str) -> List[float]:
        if not text or not self.clip_model: return [0.0] * self.config.visual_embed_dim
        inputs = self.clip_processor(text=[text], return_tensors="pt", padding=True).to("cpu")
        with torch.no_grad(): outputs = self.clip_model.get_text_features(**inputs)
        return (outputs / outputs.norm(p=2, dim=-1, keepdim=True)).squeeze().tolist()

    def get_clip_image_embedding(self, image_url: str) -> List[float]:
        if not image_url or not self.clip_model: return [0.0] * self.config.visual_embed_dim
        try:
            image = Image.open(BytesIO(requests.get(image_url, timeout=5).content))
            inputs = self.clip_processor(images=image, return_tensors="pt").to("cpu")
            with torch.no_grad(): outputs = self.clip_model.get_image_features(**inputs)
            return (outputs / outputs.norm(p=2, dim=-1, keepdim=True)).squeeze().tolist()
        except: return [0.0] * self.config.visual_embed_dim