# D:\FYP\FORGE-1\agents\retrieval\search.py
import json
from typing import List, Dict, Any
import numpy as np

from agents.catalogue import CATALOG_FILE, EMBEDDINGS_FILE


class VectorSearcher:
    def __init__(self):
        self.embeddings: Dict[str, List[float]] = {}
        self.catalog: List[Dict[str, Any]] = []
        self._load_data()

    def _load_data(self):
        if EMBEDDINGS_FILE.is_file():
            with open(EMBEDDINGS_FILE, "r", encoding="utf-8") as f:
                self.embeddings = json.load(f)
        if CATALOG_FILE.is_file():
            with open(CATALOG_FILE, "r", encoding="utf-8") as f:
                self.catalog = json.load(f)

    def search_by_vector(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Cosine similarity search against component vectors."""
        if not self.embeddings:
            return []
        q_vec = np.array(query_vector)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        scored = []
        for cid, vec in self.embeddings.items():
            c_vec = np.array(vec)
            c_norm = np.linalg.norm(c_vec)
            if c_norm > 0:
                score = float(np.dot(q_vec, c_vec) / (q_norm * c_norm))
                scored.append({"component_id": cid, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
