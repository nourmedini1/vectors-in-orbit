import spacy, torch
from transformers import pipeline

class IntentEngine:
    def __init__(self, use_zero_shot=True):
        try: self.nlp = spacy.load("en_core_web_sm")
        except:
            from spacy.cli import download; download("en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
        self.brand_patterns = ["samsung", "apple", "nike", "dell", "hp", "sony", "lenovo", "asus", "wacom", "msi", "redragon", "logitech"]
        self.use_zero_shot, self.device = use_zero_shot, 0 if torch.cuda.is_available() else -1
        if self.use_zero_shot:
            try: self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=self.device)
            except (RuntimeError, torch.cuda.OutOfMemoryError):
                torch.cuda.empty_cache(); self.device = -1
                self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
            self.labels = ["specific product search", "broad category exploration"]

    def extract_entities(self, query: str) -> dict:
        doc, entities = self.nlp(query.lower()), {"brand": None, "has_alphanumeric": False}
        for token in [t.text for t in doc]:
             if token in self.brand_patterns: entities["brand"] = token
        if any(c.isdigit() for c in query): entities["has_alphanumeric"] = True
        return entities

    def predict_intent(self, query: str) -> dict:
        entities, intent_type, confidence = self.extract_entities(query), "broad_explore", 0.0
        if self.use_zero_shot:
            try:
                result = self.classifier(query, self.labels)
                if result['labels'][0] == "specific product search": intent_type = "specific_product"
                confidence = result['scores'][0]
            except: pass
        if entities.get("brand") and entities.get("has_alphanumeric"):
            intent_type, confidence = "specific_product", 0.95
        return {"intent_type": intent_type, "confidence": confidence}