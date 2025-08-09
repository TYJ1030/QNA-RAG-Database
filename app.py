import gradio as gr
import os
import tempfile
import asyncio
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your existing services
from backend.app.services.document_processor import DocumentProcessor
from backend.app.services.vector_service import VectorService
from backend.app.services.rag_service import RAGService

# Global instances
doc_processor = None
vector_service = None
rag_service = None

def initialize_services():
    """Initialize services on first use"""
    global doc_processor, vector_service, rag_service
    if doc_processor is None:
        doc_processor = DocumentProcessor()
        vector_service = VectorService()
        rag_service = RAGService()
    return doc_processor, vector_service, rag_service

async def upload_document(file):
    """Handle document upload"""
    try:
        processor, _, _ = initialize_services()
        
        if file is None:
            return "Please select a file to upload.", ""
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp_file:
            tmp_file.write(file.read())
            tmp_path = tmp_file.name
        
        # Process the file
        from fastapi import UploadFile
        import aiofiles
        
        # Create UploadFile-like object
        class SimpleUploadFile:
            def __init__(self, filename, file_path):
                self.filename = filename
                self.file_path = file_path
            
            async def read(self):
                async with aiofiles.open(self.file_path, 'rb') as f:
                    return await f.read()
        
        upload_file = SimpleUploadFile(file.name, tmp_path)
        doc_id = await processor.handle_upload(upload_file)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return f"✅ Document uploaded successfully! ID: {doc_id}", get_documents_list()
        
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return f"❌ Upload failed: {str(e)}", ""

def get_documents_list():
    """Get list of uploaded documents"""
    try:
        processor, _, _ = initialize_services()
        docs = processor.list_documents()
        
        if not docs:
            return "No documents uploaded yet."
        
        doc_list = "📚 **Uploaded Documents:**\n\n"
        for doc in docs:
            doc_list += f"• **{doc['filename']}** ({doc['size']} bytes)\n"
            doc_list += f"  ID: `{doc['id']}`\n"
            doc_list += f"  Uploaded: {doc['created_at']}\n\n"
        
        return doc_list
        
    except Exception as e:
        return f"Error loading documents: {str(e)}"

async def query_documents(question, chat_history):
    """Handle Q&A queries"""
    try:
        if not question.strip():
            return chat_history, ""
        
        processor, vector_service, rag_service = initialize_services()
        
        # Check if documents exist
        docs = processor.list_documents()
        if not docs:
            response = "Please upload some documents first before asking questions."
            chat_history.append([question, response])
            return chat_history, ""
        
        # Process query using RAG
        enhanced_query = await rag_service.enhance_query(question)
        
        # Search for relevant chunks
        candidates = await rag_service.retrieve_candidates(
            query=enhanced_query,
            collection_name="documents",
            k=5,
            vector_service=vector_service
        )
        
        if not candidates:
            response = "I couldn't find relevant information in your documents to answer this question."
        else:
            # Build context and generate response
            context = await rag_service.build_context(candidates, max_tokens=2000)
            response = await rag_service.generate_response(question, context)
            
            # Add source information
            if candidates:
                response += "\n\n**Sources:**\n"
                for i, candidate in enumerate(candidates[:2]):
                    metadata = candidate.get("metadata", {})
                    doc_id = metadata.get("doc_id", "unknown")[:8]
                    score = candidate.get("score", 0)
                    confidence = max(0, min(100, (1 / (1 + score)) * 100))
                    response += f"• Document {doc_id}... (Confidence: {confidence:.1f}%)\n"
        
        chat_history.append([question, response])
        return chat_history, ""
        
    except Exception as e:
        logger.error(f"Query error: {e}")
        error_response = f"Sorry, I encountered an error: {str(e)}"
        chat_history.append([question, error_response])
        return chat_history, ""

# Create Gradio interface
def create_interface():
    with gr.Blocks(title="QNA RAG System", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🚀 QNA RAG System")
        gr.Markdown("Upload documents and ask questions about their content using AI-powered search and generation.")
        
        with gr.Tab("📄 Upload Documents"):
            with gr.Row():
                with gr.Column():
                    file_upload = gr.File(
                        label="Upload Document",
                        file_types=[".pdf", ".docx", ".txt"],
                        type="binary"
                    )
                    upload_btn = gr.Button("Upload Document", variant="primary")
                
                with gr.Column():
                    upload_status = gr.Textbox(
                        label="Upload Status",
                        interactive=False,
                        lines=2
                    )
            
            documents_list = gr.Markdown(
                value="No documents uploaded yet.",
                label="Uploaded Documents"
            )
            
            # Upload event
            upload_btn.click(
                fn=upload_document,
                inputs=[file_upload],
                outputs=[upload_status, documents_list]
            )
        
        with gr.Tab("💬 Ask Questions"):
            chatbot = gr.Chatbot(
                label="Chat with your documents",
                height=400
            )
            
            with gr.Row():
                question_input = gr.Textbox(
                    label="Ask a question about your documents",
                    placeholder="What is this document about?",
                    lines=2,
                    scale=4
                )
                ask_btn = gr.Button("Ask", variant="primary", scale=1)
            
            # Chat events
            ask_btn.click(
                fn=query_documents,
                inputs=[question_input, chatbot],
                outputs=[chatbot, question_input]
            )
            
            question_input.submit(
                fn=query_documents,
                inputs=[question_input, chatbot],
                outputs=[chatbot, question_input]
            )
        
        with gr.Tab("📊 System Info"):
            gr.Markdown("""
            ## System Features
            - **Document Processing**: PDF, DOCX, TXT support
            - **Vector Search**: Semantic similarity matching
            - **AI Generation**: OpenRouter API integration
            - **Source Citations**: Track answer sources
            
            ## How to Use
            1. **Upload Documents**: Go to Upload tab and select files
            2. **Ask Questions**: Use the Chat tab to query your documents
            3. **Get Answers**: Receive AI-generated responses with sources
            """)
    
    return demo

# Run the app
if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True
    )