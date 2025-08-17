# Contributing to QNA-RAG-Database

## Development Setup

### Prerequisites
- Node.js 18+ and npm/pnpm
- Python 3.8+
- Docker (optional)

### Local Development

1. **Clone and install dependencies:**
```bash
git clone <repository-url>
cd QNA-RAG-Database
npm install
pip install -r backend/requirements.txt
```

2. **Start development servers:**
```bash
# Frontend (Next.js)
npm run dev

# Backend (FastAPI)
cd backend
uvicorn app.main:app --reload --port 8000
```

3. **Run tests:**
```bash
# Backend tests
cd backend && python -m pytest tests/
# Frontend tests
npm test
```

## Project Structure
- `app/` - Next.js frontend
- `backend/` - FastAPI backend
- `components/` - React components
- `tests/` - Test files