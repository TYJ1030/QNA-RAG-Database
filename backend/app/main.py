"""
Main FastAPI application entry point.
Includes API routers, CORS, and Celery integration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import documents, health
from celery_worker import test_celery
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code (initialize resources, DB connections, etc.)
    yield
    # Shutdown code (cleanup resources)


app = FastAPI(title="Document Processing API", lifespan=lifespan)

# CORS middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Serve CSS and JS files directly
@app.get("/styles.css")
async def serve_css():
    return FileResponse("app/static/styles.css", media_type="text/css")

@app.get("/script.js")
async def serve_js():
    return FileResponse("app/static/script.js", media_type="application/javascript")

# Include document API router
app.include_router(documents.router)

# Serve frontend at root
@app.get("/")
async def serve_frontend():
    return FileResponse("app/static/index.html")


# Startup/shutdown events for resource management
# Remove @app.on_event("startup") and @app.on_event("shutdown")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "QNA-RAG-System"}

@app.post("/query")
async def query_documents(request: dict):
    # Temporarily disabled for deployment
    return {
        "answer": "Query functionality temporarily disabled during deployment. Please upload documents first.",
        "sources": [],
        "confidence": 0
    }
    
# Original query function (disabled)
async def _query_documents_disabled(request: dict):
    from app.services.rag_service import RAGService
    from app.services.vector_service import VectorService
    
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    try:
        # Use global instances to avoid re-initialization
        if not hasattr(app.state, 'rag_service'):
            app.state.rag_service = RAGService()
        if not hasattr(app.state, 'vector_service'):
            app.state.vector_service = VectorService()
            
        rag_service = app.state.rag_service
        vector_service = app.state.vector_service
        
        # Step 1: Try both original and enhanced query
        enhanced_query = await rag_service.enhance_query(query)
        
        # First try with original query
        candidates = await rag_service.retrieve_candidates(
            query=query,  # Use original query first
            collection_name="documents",
            k=10,
            vector_service=vector_service
        )
        
        # If no results, try enhanced query
        if not candidates:
            candidates = await rag_service.retrieve_candidates(
                query=enhanced_query,
                collection_name="documents",
                k=10,
                vector_service=vector_service
            )
            
        # If still no results, try simple keyword search
        if not candidates:
            candidates = await rag_service.retrieve_candidates(
                query="programs",  # Simple keyword
                collection_name="documents",
                k=10,
                vector_service=vector_service
            )
            logger.info(f"Keyword search for 'programs' found {len(candidates)} candidates")
        
        # Debug: Check ChromaDB collections
        try:
            client = vector_service._get_chromadb_client()
            collections = client.list_collections()
            logger.info(f"Available ChromaDB collections: {[c.name for c in collections]}")
            
            if collections:
                # Check first collection contents
                first_collection = collections[0]
                count = first_collection.count()
                logger.info(f"Collection '{first_collection.name}' has {count} items")
                
                if count > 0:
                    # Get a sample
                    sample = first_collection.get(limit=1, include=["documents", "metadatas"])
                    if sample['documents']:
                        logger.info(f"Sample document: {sample['documents'][0][:100]}...")
        except Exception as e:
            logger.error(f"ChromaDB debug error: {e}")
        
        # Candidates already retrieved above
        
        # Debug logging
        logger.info(f"Original query: {query}")
        logger.info(f"Enhanced query: {enhanced_query}")
        logger.info(f"Final candidates found: {len(candidates)}")
        if candidates:
            logger.info(f"Sample candidate: {candidates[0].get('text', '')[:100]}...")
        
        if not candidates:
            # Debug: Check if any documents exist
            from app.services.document_processor import DocumentProcessor
            doc_processor = DocumentProcessor()
            all_docs = doc_processor.list_documents()
            
            if not all_docs:
                return {
                    "answer": "No documents have been uploaded yet. Please upload some documents first.",
                    "sources": [],
                    "confidence": 0
                }
            else:
                return {
                    "answer": f"I found {len(all_docs)} document(s) but couldn't find relevant information for your query. The documents might not contain the information you're looking for, or the text extraction may have failed.",
                    "sources": [],
                    "confidence": 0
                }
        
        # Step 3: Build context
        context = await rag_service.build_context(candidates, max_tokens=2000)
        
        # Step 4: Generate response
        rag_prompt = """Based on the following context from uploaded documents, answer the user's question accurately and concisely.

Context: {context}

Question: {query}

Answer:"""
        
        answer = await rag_service.generate_response(
            query=query,
            context=context,
            rag_prompt_template=rag_prompt
        )
        
        # Step 5: Extract source information
        sources = []
        for candidate in candidates[:3]:  # Top 3 sources
            metadata = candidate.get("metadata", {})
            distance = candidate.get("score", 1.0)
            # Convert distance to confidence percentage (0-100%)
            # Lower distance = higher confidence
            confidence = max(0, min(100, (1 / (1 + distance)) * 100))
            sources.append({
                "document": metadata.get("doc_id", "unknown"),
                "score": round(confidence, 1),
                "text_preview": candidate.get("text", "")[:100] + "..."
            })
        
        return {
            "answer": answer or "I couldn't generate a response based on the available information.",
            "sources": sources,
            "confidence": sources[0]["score"] if sources else 0
        }
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        raise HTTPException(status_code=500, detail="Error processing query")

@app.get("/test-celery")
def run_test_celery():
    task = test_celery.delay()
    return JSONResponse({"task_id": task.id})
