from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import tempfile

from src.graph_store import GraphStore
from src.embeddings import EmbeddingStore
from src.ingest import Ingester


router = APIRouter()

graph_store = GraphStore()
embedding_store = EmbeddingStore()
ingester = Ingester(graph_store)


class QueryRequest(BaseModel):
    q: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer: str
    results: List[dict]


class IngestTextRequest(BaseModel):
    text: str
    title: Optional[str] = "pasted_text"


@router.post("/ingest")
async def ingest_files(files: List[UploadFile] = File(...)):
    job_id = ingester.create_job()
    
    total_triples = 0
    for file in files:
        content = await file.read()
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            continue
        
        triples_count = ingester.ingest_file(Path(file.filename), text_content, job_id)
        total_triples += triples_count
    
    all_triples = graph_store.get_all_triples()
    documents = []
    for triple in all_triples:
        doc = {
            "text": f"{triple['subject']} {triple['predicate']} {triple['object']}. {triple['provenance']['snippet']}",
            "triple_key": f"{triple['subject']}:{triple['predicate']}:{triple['object']}",
            "provenance": triple['provenance']
        }
        documents.append(doc)
    
    if documents:
        embedding_store.add_documents(documents)
        embedding_store.save()
    
    ingester.finalize_job(job_id)
    
    return {
        "job_id": job_id,
        "status": "done",
        "triples": total_triples
    }


@router.post("/ingest-text")
async def ingest_text(request: IngestTextRequest):
    job_id = ingester.create_job()
    
    triples_count = ingester.ingest_file(Path(request.title), request.text, job_id)
    
    all_triples = graph_store.get_all_triples()
    documents = []
    for triple in all_triples:
        doc = {
            "text": f"{triple['subject']} {triple['predicate']} {triple['object']}. {triple['provenance']['snippet']}",
            "triple_key": f"{triple['subject']}:{triple['predicate']}:{triple['object']}",
            "provenance": triple['provenance']
        }
        documents.append(doc)
    
    if documents:
        embedding_store.add_documents(documents)
        embedding_store.save()
    
    ingester.finalize_job(job_id)
    
    return {
        "job_id": job_id,
        "status": "done",
        "triples": triples_count
    }


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = ingester.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "triples": job.triples_count,
        "files_processed": job.files_processed,
        "error": job.error
    }


@router.post("/query")
async def query_graph(request: QueryRequest):
    results = embedding_store.query(request.q, top_k=request.top_k)
    
    if not results:
        keyword_results = graph_store.search_triples(request.q.split())
        results = [({"text": f"{t['subject']} {t['predicate']} {t['object']}", 
                     "provenance": t['provenance']}, 0.5) 
                   for t in keyword_results[:request.top_k]]
    
    formatted_results = []
    for doc, score in results:
        formatted_results.append({
            "text": doc.get("text", ""),
            "source": doc.get("provenance", {}).get("source", "unknown"),
            "snippet": doc.get("provenance", {}).get("snippet", ""),
            "score": round(score, 3)
        })
    
    answer = ""
    if formatted_results:
        top_snippets = [r["snippet"] for r in formatted_results[:3]]
        answer = f"Based on your knowledge graph: {' '.join(top_snippets[:2])}"
    else:
        answer = "No relevant information found in the knowledge graph."
    
    return QueryResponse(answer=answer, results=formatted_results)


@router.get("/entity/{entity_id}")
async def get_entity(entity_id: str):
    entity_info = graph_store.get_entity_info(entity_id)
    if not entity_info:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    return entity_info


@router.get("/stats")
async def get_stats():
    return {
        "total_triples": graph_store.get_triple_count(),
        "total_entities": len(set([t.split(":")[0] for t in graph_store.provenance_store.keys()] + 
                                   [t.split(":")[2] for t in graph_store.provenance_store.keys()])),
        "embedding_method": "OpenAI" if embedding_store.use_openai else "TF-IDF"
    }
