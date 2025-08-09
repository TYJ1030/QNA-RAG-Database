---
title: QNA RAG System
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
---

# QNA RAG System

A production-ready Question-Answering system using Retrieval-Augmented Generation (RAG) with document processing, vector storage, and intelligent query enhancement.

## Features

- **Document Processing**: Upload PDF, DOCX, TXT files
- **Semantic Search**: Find relevant content using vector embeddings
- **AI Responses**: Generate intelligent answers using OpenRouter API
- **Source Citations**: Track which documents were used for answers
- **Real-time Chat**: Interactive Q&A interface

## How to Use

1. **Upload Documents**: Go to the "Upload Documents" tab and select your files
2. **Ask Questions**: Switch to "Ask Questions" tab and type your queries
3. **Get Answers**: Receive AI-generated responses with source citations

## Environment Variables

Set these in your Hugging Face Space settings:

- `OPENROUTER_API_KEY`: Your OpenRouter API key
- `JINA_API_KEY`: Your Jina embeddings API key (optional)
- `COHERE_API_KEY`: Your Cohere API key (optional)

## Architecture

```
Document Upload → Text Extraction → Semantic Chunking → Vector Embeddings → ChromaDB Storage
                                                                                    ↓
User Query → Query Enhancement → Vector Search → Context Building → AI Response
```

## Technology Stack

- **Frontend**: Gradio web interface
- **Backend**: FastAPI with async processing
- **Embeddings**: SentenceTransformers (all-MiniLM-L6-v2)
- **Vector DB**: ChromaDB for similarity search
- **AI Generation**: OpenRouter API (multiple models)
- **Document Processing**: PyPDF, python-docx for text extraction