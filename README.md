---
title: QNA RAG Database
sdk: docker
app_port: 3000
pinned: false
license: mit
---

# QNA-RAG-Database System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org/)

A production-ready Question-Answering system using Retrieval-Augmented Generation (RAG) with document processing, vector storage, and intelligent query enhancement.

## 🚀 Quick Start

### Option 1: Docker (Recommended)
```bash
git clone <your-repo-url>
cd QNA-RAG-Database
cp .env.example .env
docker-compose up
```
Access the app at `http://localhost:3000`

### Option 2: Local Development
```bash
# Install dependencies
npm install
pip install -r backend/requirements.txt

# Start services
npm run dev          # Frontend (port 3000)
cd backend && uvicorn app.main:app --reload --port 8000  # Backend
```

## ✨ Features

- **📄 Document Processing**: PDF, DOCX, TXT support with OCR capabilities
- **🧩 Semantic Chunking**: Intelligent text segmentation preserving context
- **🔍 Vector Embeddings**: Jina embeddings v2 (512 dimensions) with caching
- **💾 Vector Storage**: ChromaDB for efficient similarity search
- **🤖 RAG Pipeline**: Query enhancement, retrieval, reranking, and response generation
- **📱 Modern UI**: Responsive Next.js frontend with real-time chat interface

## 📋 How to Use

1. **Upload Documents**: Drag & drop PDF, DOCX, or TXT files
2. **Wait for Processing**: Documents are chunked and vectorized automatically
3. **Ask Questions**: Use the chat interface to query your documents
4. **Get Answers**: Receive intelligent responses with source citations

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js UI    │───▶│   FastAPI       │───▶│   ChromaDB      │
│   (Frontend)    │    │   (Backend)     │    │   (Vector DB)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Celery        │
                       │   (Background)  │
                       └─────────────────┘
```

## 📁 Project Structure

```
QNA-RAG-Database/
├── app/                    # Next.js pages
├── components/             # React components
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── models/        # Data models
│   │   └── services/      # Business logic
│   └── requirements.txt
├── tests/                 # Test files
├── docker-compose.yml     # Multi-service setup
└── README.md
```

## 🛠️ Tech Stack

**Frontend:**
- Next.js 15 + React 19
- TypeScript
- Tailwind CSS + shadcn/ui
- Real-time chat interface

**Backend:**
- FastAPI (Python)
- ChromaDB (Vector database)
- Celery (Background tasks)
- Redis (Task queue)

**AI/ML:**
- Jina Embeddings v2
- Sentence Transformers
- OCR with Tesseract
- Cross-encoder reranking

## 🔧 Configuration

Copy `.env.example` to `.env` and configure:

```env
BACKEND_URL=http://localhost:8000
CHROMA_DB_PATH=./chroma_db
COHERE_API_KEY=your_key_here  # Optional
```

## 🧪 Testing

```bash
# Backend tests
cd backend && python -m pytest tests/

# Frontend tests
npm test
```

## 📚 API Documentation

Once running, visit:
- Frontend: `http://localhost:3000`
- API Docs: `http://localhost:8000/docs`
- API Redoc: `http://localhost:8000/redoc`

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.
