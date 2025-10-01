import re
import uuid
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from src.graph_store import GraphStore, ProvenanceInfo


class IngestionJob:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "queued"
        self.triples_count = 0
        self.files_processed = 0
        self.error = None


class TextChunker:
    def __init__(self, chunk_size: int = 300, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_text(self, text: str, source: str) -> List[Dict]:
        sentences = self._split_sentences(text)
        chunks = []
        
        current_chunk = []
        current_length = 0
        chunk_start = 0
        
        for sentence in sentences:
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length > self.chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "source": source,
                    "start": chunk_start,
                    "end": chunk_start + len(chunk_text)
                })
                
                overlap_words = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s.split()) <= self.overlap:
                        overlap_words.insert(0, s)
                        overlap_length += len(s.split())
                    else:
                        break
                
                current_chunk = overlap_words
                current_length = overlap_length
                if not overlap_words:
                    chunk_start = chunk_start + len(chunk_text)
            
            current_chunk.append(sentence)
            current_length += sentence_length
        
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "source": source,
                "start": chunk_start,
                "end": chunk_start + len(chunk_text)
            })
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        text = re.sub(r'\s+', ' ', text)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]


class EntityExtractor:
    def __init__(self):
        self.patterns = [
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+(?:a|an)\s+([a-z]+(?:\s+[a-z]+)*)', 'isA'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+works?\s+(?:on|with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'worksOn'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+uses?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'uses'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:creates?|created|building|built)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'creates'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:relates?|related)\s+to\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'relatedTo'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:has|have)\s+([a-z]+(?:\s+[a-z]+)*)', 'has'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:developed|develops)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'develops'),
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:wrote|writes|written)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', 'writes'),
        ]
    
    def extract_triples(self, chunk: Dict) -> List[Tuple[str, str, str, float, ProvenanceInfo]]:
        text = chunk["text"]
        triples = []
        
        for pattern, relation in self.patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                subject = match.group(1).strip()
                obj = match.group(2).strip()
                
                if subject and obj and subject != obj:
                    snippet = text[max(0, match.start()-50):min(len(text), match.end()+50)]
                    provenance = ProvenanceInfo(
                        source=chunk["source"],
                        snippet=snippet,
                        start=chunk["start"] + match.start(),
                        end=chunk["start"] + match.end()
                    )
                    
                    triples.append((subject, relation, obj, 0.8, provenance))
        
        triples.extend(self._extract_entities(chunk))
        
        return triples
    
    def _extract_entities(self, chunk: Dict) -> List[Tuple[str, str, str, float, ProvenanceInfo]]:
        text = chunk["text"]
        triples = []
        
        entity_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b'
        matches = list(re.finditer(entity_pattern, text))
        
        for i, match in enumerate(matches):
            entity = match.group(1).strip()
            
            if len(entity.split()) >= 2:
                snippet = text[max(0, match.start()-30):min(len(text), match.end()+30)]
                provenance = ProvenanceInfo(
                    source=chunk["source"],
                    snippet=snippet,
                    start=chunk["start"] + match.start(),
                    end=chunk["start"] + match.end()
                )
                
                for j in range(i+1, min(i+3, len(matches))):
                    other_entity = matches[j].group(1).strip()
                    if len(other_entity.split()) >= 2 and entity != other_entity:
                        distance = matches[j].start() - match.end()
                        if distance < 100:
                            triples.append((entity, "mentionedWith", other_entity, 0.5, provenance))
                            break
        
        return triples


class Ingester:
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store
        self.chunker = TextChunker()
        self.extractor = EntityExtractor()
        self.jobs = {}
    
    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        self.jobs[job_id] = IngestionJob(job_id)
        return job_id
    
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        return self.jobs.get(job_id)
    
    def ingest_file(self, file_path: Path, content: str, job_id: str) -> int:
        job = self.jobs.get(job_id)
        if not job:
            return 0
        
        job.status = "processing"
        
        try:
            chunks = self.chunker.chunk_text(content, str(file_path))
            
            triples_added = 0
            for chunk in chunks:
                triples = self.extractor.extract_triples(chunk)
                for subject, predicate, obj, confidence, provenance in triples:
                    self.graph_store.add_triple(subject, predicate, obj, confidence, provenance)
                    triples_added += 1
            
            job.triples_count += triples_added
            job.files_processed += 1
            
            return triples_added
        except Exception as e:
            job.error = str(e)
            job.status = "failed"
            return 0
    
    def finalize_job(self, job_id: str):
        job = self.jobs.get(job_id)
        if job:
            job.status = "done"
            self.graph_store.save()
