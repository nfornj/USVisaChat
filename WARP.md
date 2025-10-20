# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Overview

The **Visa Community Platform** is a full-stack real-time application that combines community chat with AI-powered search through 1.5M+ visa conversations. It's built for the visa community to share experiences and get intelligent answers about visa processes.

## Common Development Commands

### Quick Start Commands

```bash
# Start the full platform (development with local Ollama)
docker compose --profile web up qdrant visa-web -d

# Start production deployment (with Groq API)
docker compose --profile production up qdrant visa-prod -d

# Health check
curl http://localhost:8000/health

# View logs
docker compose logs visa-web -f

# Stop services
docker compose --profile web down

# Rebuild after code changes
docker compose build --no-cache visa-web
docker compose --profile web up qdrant visa-web -d
```

### Local Development Setup

```bash
# Backend development (without Docker)
docker compose up qdrant mongodb -d
cd backend
uv sync
uv run python api/main.py

# Frontend development
cd frontend
npm install
npm run dev
```

### Python Dependency Management

This project uses **UV** for dependency management:

```bash
# Install new packages
uv add package_name

# Remove packages
uv remove package_name

# Sync all dependencies
uv sync

# Run with UV environment
uv run python script.py
```

### Data Processing Commands

```bash
# Discover available Telegram chats
docker compose --profile telegram run telegram-discover

# Download specific chats
CHAT_IDS="chat1,chat2" docker compose --profile specific run telegram-specific

# Process downloaded CSV data
docker compose --profile data-ingestion run csv-processor

# Run vector processing pipeline
uv run python backend/scripts/run_vector_pipeline.py

# Scrape RedBus2US articles
uv run python pipeline/article_processing/comprehensive_redbus_scraper.py

# Organize articles
uv run python pipeline/article_processing/organize_articles.py

# Summarize articles
uv run python pipeline/article_processing/article_summarizer.py
```

### Testing & Development

```bash
# Frontend linting
cd frontend && npm run lint

# Frontend build
cd frontend && npm run build

# Backend testing (run single components)
uv run python backend/services/llm_service.py
uv run python backend/services/simple_vector_processor.py

# Pipeline testing (run individual scripts)
uv run python pipeline/article_processing/comprehensive_redbus_scraper.py
uv run python pipeline/article_processing/organize_articles.py
uv run python pipeline/article_processing/article_summarizer.py
```

## Architecture Overview

### High-Level Architecture

```
User → React Frontend (Material-UI + TypeScript)
         ↓
     FastAPI Backend (Python + UV)
       ├── WebSocket → Community Chat (MongoDB Atlas)
       ├── Auth System → User Management (MongoDB Atlas)  
       ├── LLM Service → AI Responses (Groq API / Ollama)
       └── Vector Search → AI Search (Qdrant 1.5M+ vectors)
```

### Key Components

**Backend Services (`backend/services/`)**:
- `llm_service.py` - Flexible LLM service (Ollama/Groq with Llama 3.1 8B)
- `simple_vector_processor.py` - Vector search through 1.5M+ conversations
- `chat_synthesizer.py` - AI response synthesis from search results
- `enhanced_chat_synthesizer.py` - RedBus2US knowledge-based answers
- `email_service.py` - Email verification system

**API Layer (`backend/api/`)**:
- `main.py` - FastAPI server with REST endpoints and WebSocket support

**Data Models (`backend/models/`)**:
- `community_chat.py` - WebSocket-based group messaging
- `user_auth.py` - Email-based authentication system
- `mongodb_connection.py` - MongoDB Atlas connection management

**Pipeline Processing (`pipeline/`)**:
- `article_processing/comprehensive_redbus_scraper.py` - RedBus2US article scraping
- `article_processing/organize_articles.py` - Article organization by date/category
- `article_processing/article_summarizer.py` - AI-powered article summarization
- `data_processing/telegram_csv_downloader.py` - Telegram data collection
- `data_processing/csv_data_processor.py` - Data preprocessing and cleanup

**Vector Processing (`backend/scripts/`)**:
- `run_vector_pipeline.py` - Vector embedding pipeline
- `load_redbus_to_qdrant.py` - Vector database loading
- `generate_article_vectors.py` - Article vectorization

### Frontend Architecture

**React App (`frontend/src/`)**:
- `App.tsx` - Main application with Material-UI theming
- `CommunityChat.tsx` - Real-time chat interface with WebSocket
- `AIAssistant.tsx` - ChatGPT-style AI search interface
- `components/` - Reusable UI components

**Tech Stack**:
- React 18 + TypeScript
- Material-UI (MUI) for components
- Tailwind CSS for styling
- Vite for build tooling
- Axios for HTTP requests

### Data Flow

1. **Vector Search**: User query → Sentence transformers → Qdrant search → Top results
2. **AI Synthesis**: Search results → LLM Service (Groq/Ollama) → Synthesized answer
3. **Community Chat**: WebSocket connection → Real-time messaging → MongoDB storage
4. **Authentication**: Email → 6-digit code → Session token → User access

### Docker Compose Profiles

- **`web`** - Full web application (development)
- **`production`** - Production deployment with Groq API
- **`telegram`** - Telegram data collection
- **`data-ingestion`** - Data processing pipeline
- **`vectors`** - Vector database and processing

### Environment Configuration

The application uses two LLM configurations:

**Development (Local Ollama)**:
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1:8b
OLLAMA_HOST=http://localhost:11434
```

**Production (Groq API)**:
```bash
LLM_PROVIDER=groq
LLM_MODEL=llama3.1:8b
GROQ_API_KEY=your-api-key
```

## Important Development Notes

### Database Architecture

- **Qdrant**: Vector database with 1.5M+ conversations (384-dim embeddings)
  - Collections: `visa_conversations`, `redbus2us_articles`
- **MongoDB Atlas**: User authentication, chat history, session management
  - Uses email-based verification (no passwords)

### LLM Service Design

The `LLMService` class provides flexible LLM integration:
- Automatic fallback from Groq to Ollama
- Consistent interface across providers
- Uses Llama 3.1 8B model for both local and cloud deployment

### Key Design Patterns

1. **Service Layer Pattern**: Business logic separated into services
2. **Repository Pattern**: Database access abstracted through models
3. **Factory Pattern**: LLM service switches providers based on config
4. **WebSocket Manager**: Centralized chat connection management

### Performance Characteristics

- **Vector Search**: 50-200ms average response time
- **LLM Responses**: 1-2s (Groq) / 5-7s (Ollama)
- **WebSocket Latency**: <10ms for real-time chat
- **Concurrent Users**: Tested up to 100+

### File Organization Rules

This project follows strict documentation rules (see `.cursorrules`):
- **Only 3 documentation files allowed**: README.md, PROGRESS.md, PROJECT_PROFILE.md
- **Never create** additional .md files without explicit user request
- **Use UV** for all Python dependency management
- **Update PROGRESS.md** for all development changes

### Common Gotchas

1. **UV vs pip**: Always use `uv` for dependency management, never `pip`
2. **Docker profiles**: Use correct profile for your use case (web/production/telegram)
3. **LLM fallback**: Service automatically falls back to Ollama if Groq API key missing
4. **MongoDB certificates**: Production requires TLS certificates for MongoDB Atlas
5. **Port conflicts**: Default ports are 8000 (app), 6333 (Qdrant), 27017 (MongoDB)

### Development Workflow

1. **Local Development**: Use `docker compose --profile web` with local Ollama
2. **Production Testing**: Use `docker compose --profile production` with Groq API
3. **Data Updates**: Use telegram/data-ingestion profiles for data collection
4. **Code Changes**: Always update PROGRESS.md and rebuild containers

## Key Files to Know

- `backend/api/main.py` - Main FastAPI application
- `backend/services/llm_service.py` - LLM abstraction layer
- `docker-compose.yml` - Service orchestration with multiple profiles
- `frontend/src/App.tsx` - Main React application
- `backend/pyproject.toml` - Python dependencies (managed by UV)
- `.cursorrules` - Strict development and documentation rules