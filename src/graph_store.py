import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS
import hashlib


class ProvenanceInfo:
    def __init__(self, source: str, snippet: str, start: int, end: int):
        self.source = source
        self.snippet = snippet
        self.start = start
        self.end = end
    
    def to_dict(self):
        return {
            "source": self.source,
            "snippet": self.snippet,
            "start": self.start,
            "end": self.end
        }


class GraphStore:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.graph_path = self.data_dir / "graph.ttl"
        self.provenance_path = self.data_dir / "provenance.json"
        self.aliases_path = self.data_dir / "aliases.json"
        
        self.graph = Graph()
        self.PKG = Namespace("http://pkg.local/")
        self.graph.bind("pkg", self.PKG)
        
        self.provenance_store = {}
        self.alias_table = {}
        
        self._load()
    
    def _load(self):
        if self.graph_path.exists():
            self.graph.parse(self.graph_path, format="turtle")
        
        if self.provenance_path.exists():
            with open(self.provenance_path, 'r') as f:
                self.provenance_store = json.load(f)
        
        if self.aliases_path.exists():
            with open(self.aliases_path, 'r') as f:
                self.alias_table = json.load(f)
    
    def save(self):
        self.graph.serialize(destination=str(self.graph_path), format="turtle")
        
        with open(self.provenance_path, 'w') as f:
            json.dump(self.provenance_store, f, indent=2)
        
        with open(self.aliases_path, 'w') as f:
            json.dump(self.alias_table, f, indent=2)
    
    def _normalize_entity(self, text: str) -> str:
        return text.lower().strip()
    
    def _entity_id(self, text: str) -> str:
        normalized = self._normalize_entity(text)
        if normalized in self.alias_table:
            return self.alias_table[normalized]
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def add_alias(self, text: str, canonical_id: str):
        normalized = self._normalize_entity(text)
        self.alias_table[normalized] = canonical_id
    
    def get_canonical_id(self, text: str) -> str:
        normalized = self._normalize_entity(text)
        return self.alias_table.get(normalized, self._entity_id(text))
    
    def add_triple(self, subject: str, predicate: str, obj: str, 
                   confidence: float, provenance: ProvenanceInfo):
        subject_id = self.get_canonical_id(subject)
        object_id = self.get_canonical_id(obj)
        
        subject_uri = URIRef(self.PKG[subject_id])
        predicate_uri = URIRef(self.PKG[predicate])
        object_uri = URIRef(self.PKG[object_id])
        
        self.graph.add((subject_uri, predicate_uri, object_uri))
        self.graph.add((subject_uri, RDFS.label, Literal(subject)))
        self.graph.add((object_uri, RDFS.label, Literal(obj)))
        
        triple_key = f"{subject_id}:{predicate}:{object_id}"
        self.provenance_store[triple_key] = {
            "subject": subject,
            "predicate": predicate,
            "object": obj,
            "confidence": confidence,
            "provenance": provenance.to_dict()
        }
    
    def get_entity_info(self, entity_id: str) -> Optional[Dict]:
        entity_uri = URIRef(self.PKG[entity_id])
        
        if (entity_uri, None, None) not in self.graph and (None, None, entity_uri) not in self.graph:
            return None
        
        label = None
        for s, p, o in self.graph.triples((entity_uri, RDFS.label, None)):
            label = str(o)
            break
        
        relations = []
        for s, p, o in self.graph.triples((entity_uri, None, None)):
            if p != RDFS.label:
                obj_label = self._get_label(o)
                relations.append({
                    "predicate": str(p).replace(str(self.PKG), ""),
                    "object": obj_label,
                    "object_id": str(o).replace(str(self.PKG), "")
                })
        
        for s, p, o in self.graph.triples((None, None, entity_uri)):
            if p != RDFS.label:
                subj_label = self._get_label(s)
                relations.append({
                    "predicate": str(p).replace(str(self.PKG), "") + "_inverse",
                    "object": subj_label,
                    "object_id": str(s).replace(str(self.PKG), "")
                })
        
        aliases = [k for k, v in self.alias_table.items() if v == entity_id]
        
        sources = set()
        for triple_key, prov_data in self.provenance_store.items():
            if entity_id in triple_key:
                sources.add(prov_data["provenance"]["source"])
        
        return {
            "entity_id": entity_id,
            "label": label or entity_id,
            "aliases": aliases,
            "relations": relations,
            "sources": list(sources)
        }
    
    def _get_label(self, uri) -> str:
        for s, p, o in self.graph.triples((uri, RDFS.label, None)):
            return str(o)
        return str(uri).replace(str(self.PKG), "")
    
    def get_all_triples(self) -> List[Dict]:
        results = []
        for triple_key, prov_data in self.provenance_store.items():
            results.append(prov_data)
        return results
    
    def search_triples(self, query_terms: List[str]) -> List[Dict]:
        results = []
        query_lower = [t.lower() for t in query_terms]
        
        for triple_key, prov_data in self.provenance_store.items():
            text = f"{prov_data['subject']} {prov_data['predicate']} {prov_data['object']} {prov_data['provenance']['snippet']}"
            text_lower = text.lower()
            
            if any(term in text_lower for term in query_lower):
                results.append(prov_data)
        
        return results
    
    def get_triple_count(self) -> int:
        return len(self.provenance_store)
