"""
Main FastAPI application entry point.
Includes API routers, CORS, and Celery integration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import documents
from celery_worker import test_celery
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code (initialize resources, DB connections, etc.)
    yield
    # Shutdown code (cleanup resources)


app = FastAPI(title="Document Processing API", lifespan=lifespan)

# CORS middleware (adjust origins as needed)
# Get allowed origins from environment
import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include document API router
app.include_router(documents.router)


@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "API is running"}

@app.post("/sync/clear-documents")
def clear_documents_on_frontend_restart():
    """Clear all backend documents when frontend restarts/refreshes"""
    import redis
    import logging
    
    logger = logging.getLogger(__name__)
    r = redis.Redis.from_url(
        "rediss://default:AYLCAAIjcDFkNGZhYmNkMWI1NjM0MWZmYjdjM2I4ZWE0ODQ4NWI4ZHAxMA@enormous-lab-33474.upstash.io:6379?ssl_cert_reqs=required",
        decode_responses=True
    )
    
    # Get all document IDs
    doc_ids = list(r.smembers('doc_ids'))
    
    # Remove all document-related data
    for doc_id in doc_ids:
        r.delete(f"doc_meta:{doc_id}")
        r.delete(f"doc_progress:{doc_id}")
        r.delete(f"doc_chunks:{doc_id}")
    
    # Clear the document IDs set
    r.delete('doc_ids')
    
    logger.info(f"Frontend sync: cleared {len(doc_ids)} documents from backend")
    return {"message": "Backend documents cleared", "cleared_count": len(doc_ids)}

@app.get("/admin/debug")
def debug_redis_state():
    """Show what documents are currently in Redis"""
    import redis
    import logging
    
    logger = logging.getLogger(__name__)
    r = redis.Redis.from_url(
        "rediss://default:AYLCAAIjcDFkNGZhYmNkMWI1NjM0MWZmYjdjM2I4ZWE0ODQ4NWI4ZHAxMA@enormous-lab-33474.upstash.io:6379?ssl_cert_reqs=required",
        decode_responses=True
    )
    
    doc_ids = list(r.smembers('doc_ids'))
    documents = []
    
    for doc_id in doc_ids:
        doc_meta = r.hgetall(f"doc_meta:{doc_id}")
        chunks_count = r.llen(f"doc_chunks:{doc_id}")
        documents.append({
            "id": doc_id,
            "filename": doc_meta.get('filename', 'Unknown'),
            "created_at": doc_meta.get('created_at', 'Unknown'),
            "chunks_count": chunks_count
        })
    
    return {
        "total_documents": len(doc_ids),
        "documents": documents
    }

@app.get("/admin/reset")
def reset_all_documents():
    """DANGER: Remove ALL documents from Redis - use for testing only"""
    import redis
    import logging
    
    logger = logging.getLogger(__name__)
    r = redis.Redis.from_url(
        "rediss://default:AYLCAAIjcDFkNGZhYmNkMWI1NjM0MWZmYjdjM2I4ZWE0ODQ4NWI4ZHAxMA@enormous-lab-33474.upstash.io:6379?ssl_cert_reqs=required",
        decode_responses=True
    )
    
    # Get all document IDs
    doc_ids = list(r.smembers('doc_ids'))
    
    # Remove all document-related data
    for doc_id in doc_ids:
        r.delete(f"doc_meta:{doc_id}")
        r.delete(f"doc_progress:{doc_id}")
        r.delete(f"doc_chunks:{doc_id}")
    
    # Clear the document IDs set
    r.delete('doc_ids')
    
    logger.info(f"Reset complete: removed {len(doc_ids)} documents")
    return {"message": f"Reset complete: removed {len(doc_ids)} documents", "remaining_docs": 0}

from fastapi import HTTPException
import asyncio

@app.post("/rag/query")
async def rag_query(request: dict):
    import redis
    import ast
    import numpy as np
    import logging
    from app.services.rag_service import RAGService
    
    logger = logging.getLogger(__name__)
    
    try:
        query = request["query"]
        
        # Special reset command
        if query.lower() == "reset redis now":
            r = redis.Redis.from_url(
                "rediss://default:AYLCAAIjcDFkNGZhYmNkMWI1NjM0MWZmYjdjM2I4ZWE0ODQ4NWI4ZHAxMA@enormous-lab-33474.upstash.io:6379?ssl_cert_reqs=required",
                decode_responses=True
            )
            doc_ids = list(r.smembers('doc_ids'))
            for doc_id in doc_ids:
                r.delete(f"doc_meta:{doc_id}")
                r.delete(f"doc_progress:{doc_id}")
                r.delete(f"doc_chunks:{doc_id}")
            r.delete('doc_ids')
            logger.info(f"Redis reset: removed {len(doc_ids)} documents")
            return {"answer": f"Redis reset complete: removed {len(doc_ids)} documents", "sources": []}
        
        rag = RAGService()
        
        # Get chunks from Redis
        r = redis.Redis.from_url(
            "rediss://default:AYLCAAIjcDFkNGZhYmNkMWI1NjM0MWZmYjdjM2I4ZWE0ODQ4NWI4ZHAxMA@enormous-lab-33474.upstash.io:6379?ssl_cert_reqs=required",
            decode_responses=True
        )
        
        # Use all available documents
        doc_ids = list(r.smembers('doc_ids'))
        logger.info(f"Found {len(doc_ids)} total documents in Redis")
        
        # Use all documents that have valid metadata and chunks
        current_docs = []
        for doc_id in doc_ids:
            doc_meta = r.hgetall(f"doc_meta:{doc_id}")
            chunks_exist = r.exists(f"doc_chunks:{doc_id}")
            if doc_meta and chunks_exist:
                current_docs.append(doc_id)
        
        logger.info(f"Using {len(current_docs)} documents for RAG query")
        
        if not current_docs:
            return {"answer": "No documents found. Please upload documents first.", "sources": []}
        
        # Collect chunks from all current documents (with limits)
        all_chunks = []
        chunk_sources = []
        MAX_CHUNKS_PER_DOC = 100  # Limit chunks per document
        MAX_TOTAL_CHUNKS = 500    # Limit total chunks
        
        for doc_id in current_docs:
            if len(all_chunks) >= MAX_TOTAL_CHUNKS:
                logger.info(f"Reached maximum total chunks limit ({MAX_TOTAL_CHUNKS})")
                break
                
            chunks_raw = r.lrange(f"doc_chunks:{doc_id}", 0, MAX_CHUNKS_PER_DOC-1)  # Limit per doc
            doc_meta = r.hgetall(f"doc_meta:{doc_id}")
            doc_filename = doc_meta.get('filename', 'Unknown') if doc_meta else 'Unknown'
            logger.info(f"Processing document: {doc_filename} (ID: {doc_id}) with {len(chunks_raw)} chunks (limited)")
            
            for chunk_str in chunks_raw:
                if len(all_chunks) >= MAX_TOTAL_CHUNKS:
                    break
                try:
                    chunk = ast.literal_eval(chunk_str)
                    text = chunk.get('text', '')
                    if text.strip():
                        all_chunks.append(text)
                        chunk_sources.append({
                            'filename': doc_filename,
                            'doc_id': doc_id
                        })
                except:
                    continue
        
        if not all_chunks:
            return {"answer": "No relevant documents found. Please upload documents first.", "sources": []}
        
        # Use semantic similarity for fair ranking (with timeout)
        async def process_with_timeout():
            from sentence_transformers import SentenceTransformer
            
            model = SentenceTransformer('all-MiniLM-L6-v2')
            query_embedding = model.encode([query])[0]
            
            # Calculate semantic similarity for each chunk (batch processing)
            chunk_scores = []
            batch_size = 50  # Process in batches
            
            for i in range(0, len(all_chunks), batch_size):
                batch_chunks = all_chunks[i:i+batch_size]
                batch_embeddings = model.encode(batch_chunks)
                
                for j, chunk_embedding in enumerate(batch_embeddings):
                    chunk_idx = i + j
                    if chunk_idx < len(all_chunks) and all_chunks[chunk_idx].strip():
                        similarity = np.dot(query_embedding, chunk_embedding) / (
                            np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                        )
                        chunk_scores.append((all_chunks[chunk_idx], similarity, chunk_sources[chunk_idx]))
            
            return chunk_scores
        
        try:
            # Set 30 second timeout for embedding processing
            chunk_scores = await asyncio.wait_for(process_with_timeout(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error("Embedding processing timed out after 30 seconds")
            raise HTTPException(status_code=408, detail="Query processing timed out. Please try with fewer documents.")
        except Exception as e:
            logger.error(f"Error in embedding processing: {str(e)}")
            raise HTTPException(status_code=500, detail="Error processing query")
        
        # Sort by semantic similarity (highest first)
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Take top 10 most semantically similar chunks
        top_chunks = chunk_scores[:10]
        relevant_chunks = [chunk for chunk, score, source in top_chunks]
        
        # Log the top matches for debugging
        logger.info(f"Top semantic matches for '{query}':")
        for i, (chunk, score, source) in enumerate(top_chunks[:3]):
            logger.info(f"  {i+1}. Score: {score:.3f}, Source: {source['filename']}, Text: {chunk[:100]}...")
        
        # Build context
        context = "\n\n".join(relevant_chunks[:8])
        
        # Log query processing for monitoring
        logger.info(f"RAG Query: '{query}' - Found {len(relevant_chunks)} relevant chunks from {len(current_docs)} documents")
        
        # Generate response
        template = """You are a document-based AI assistant. You must ONLY use information from the provided context to answer questions. If the answer is not in the context, you must say "I cannot answer this question based on the provided documents."

Do NOT provide any information from your general knowledge. Do NOT make assumptions. Do NOT offer to provide information outside the context.

Context: {context}

Question: {query}

Answer (use ONLY the context above):"""
        
        answer = await rag.generate_response(
            query, 
            context, 
            template,
            model="deepseek/deepseek-chat"
        )
        
        # Format sources
        unique_sources = {}
        for chunk in relevant_chunks[:8]:
            if chunk in all_chunks:
                chunk_idx = all_chunks.index(chunk)
                source_info = chunk_sources[chunk_idx] if chunk_idx < len(chunk_sources) else {'filename': 'Unknown'}
                filename = source_info['filename']
                
                if filename not in unique_sources:
                    unique_sources[filename] = {
                        "document": filename,
                        "page": 1,
                        "text": chunk[:200] + "..."
                    }
        
        sources = list(unique_sources.values())
        
        return {"answer": answer, "sources": sources}
        
    except Exception as e:
        logger.error(f"RAG query error: {str(e)}")
        return {"answer": f"Error: {str(e)}", "sources": []}

@app.get("/test-celery")
def run_test_celery():
    task = test_celery.delay()
    return JSONResponse({"task_id": task.id})