import os
import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingStore:
    def __init__(self, data_dir: str = "data", use_openai: Optional[bool] = None):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.vectors_path = self.data_dir / "vectors.npy"
        self.metadata_path = self.data_dir / "vector_metadata.json"
        self.tfidf_path = self.data_dir / "tfidf_vectorizer.pkl"
        
        if use_openai is None:
            use_openai = bool(os.getenv("OPENAI_API_KEY"))
        
        self.use_openai = use_openai
        self.openai_client = None
        
        if self.use_openai:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except Exception as e:
                print(f"Failed to initialize OpenAI client: {e}")
                self.use_openai = False
        
        self.tfidf_vectorizer = None
        self.vectors = None
        self.metadata = []
        
        self._load()
    
    def _load(self):
        if self.vectors_path.exists():
            self.vectors = np.load(self.vectors_path)
        
        if self.metadata_path.exists():
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
        
        if not self.use_openai and self.tfidf_path.exists():
            try:
                with open(self.tfidf_path, 'rb') as f:
                    self.tfidf_vectorizer = pickle.load(f)
            except Exception as e:
                print(f"Failed to load TF-IDF vectorizer: {e}")
                if len(self.metadata) > 0:
                    all_texts = [m["text"] for m in self.metadata]
                    self.tfidf_vectorizer = TfidfVectorizer(max_features=300, stop_words='english')
                    self.tfidf_vectorizer.fit(all_texts)
    
    def save(self):
        if self.vectors is not None:
            np.save(self.vectors_path, self.vectors)
        
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        if not self.use_openai and self.tfidf_vectorizer is not None:
            with open(self.tfidf_path, 'wb') as f:
                pickle.dump(self.tfidf_vectorizer, f)
    
    def _get_openai_embedding(self, text: str) -> Optional[np.ndarray]:
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"OpenAI embedding error: {e}")
            return None
    
    def _get_tfidf_embeddings(self, texts: List[str], refit: bool = False) -> np.ndarray:
        if self.tfidf_vectorizer is None or refit:
            all_texts = [m["text"] for m in self.metadata] + texts
            self.tfidf_vectorizer = TfidfVectorizer(max_features=300, stop_words='english')
            self.tfidf_vectorizer.fit(all_texts)
        
        return self.tfidf_vectorizer.transform(texts).toarray()
    
    def add_documents(self, documents: List[Dict]):
        new_texts = [doc["text"] for doc in documents]
        
        if self.use_openai and self.openai_client:
            new_vectors = []
            for text in new_texts:
                vec = self._get_openai_embedding(text)
                if vec is not None:
                    new_vectors.append(vec)
                else:
                    return False
            new_vectors = np.array(new_vectors)
        else:
            if self.vectors is None:
                new_vectors = self._get_tfidf_embeddings(new_texts)
            else:
                old_texts = [m["text"] for m in self.metadata]
                all_vectors = self._get_tfidf_embeddings(old_texts + new_texts, refit=True)
                self.vectors = all_vectors
                self.metadata.extend(documents)
                return True
        
        if self.vectors is None:
            self.vectors = new_vectors
        else:
            self.vectors = np.vstack([self.vectors, new_vectors])
        
        self.metadata.extend(documents)
        return True
    
    def query(self, query_text: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        if self.vectors is None or len(self.metadata) == 0:
            return []
        
        if self.use_openai and self.openai_client:
            query_vec = self._get_openai_embedding(query_text)
            if query_vec is None:
                return []
            query_vec = query_vec.reshape(1, -1)
        else:
            if self.tfidf_vectorizer is None:
                if len(self.metadata) > 0:
                    all_texts = [m["text"] for m in self.metadata]
                    self.tfidf_vectorizer = TfidfVectorizer(max_features=300, stop_words='english')
                    self.tfidf_vectorizer.fit(all_texts)
                else:
                    return []
            query_vec = self.tfidf_vectorizer.transform([query_text]).toarray()
        
        similarities = cosine_similarity(query_vec, self.vectors)[0]
        
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            if similarities[idx] > 0:
                results.append((self.metadata[idx], float(similarities[idx])))
        
        return results
    
    def clear(self):
        self.vectors = None
        self.metadata = []
        self.tfidf_vectorizer = None
        
        if self.vectors_path.exists():
            self.vectors_path.unlink()
        if self.metadata_path.exists():
            self.metadata_path.unlink()
        if self.tfidf_path.exists():
            self.tfidf_path.unlink()
