# Visa Community Platform - Backend

FastAPI-based backend with MongoDB, Qdrant vector search, and local LLM integration.

## 📂 Project Structure

```
backend/
├── api/                    # FastAPI routes and endpoints
│   ├── main.py            # Main FastAPI application
│   └── __init__.py
│
├── services/              # Business logic and AI services
│   ├── enhanced_chat_synthesizer.py   # RedBus2US Q&A with Qwen LLM
│   ├── chat_synthesizer.py            # Conversation synthesis
│   ├── smart_chat_synthesizer.py      # Smart chat responses
│   ├── simple_vector_processor.py     # Qdrant vector operations
│   ├── email_service.py               # Email verification
│   └── __init__.py
│
├── models/                # Database models and connections
│   ├── mongodb_connection.py          # MongoDB Atlas connection
│   ├── mongodb_auth.py                # Authentication DB
│   ├── mongodb_chat.py                # Chat DB
│   ├── community_chat.py              # WebSocket chat
│   ├── user_auth.py                   # User authentication
│   └── __init__.py
│
├── utils/                 # Utility functions
│   ├── data_cleanup.py                # Data cleaning utilities
│   ├── mongodb_certificate_validator.py
│   └── __init__.py
│
├── scripts/               # Data processing and ETL scripts
│   ├── telegram_csv_downloader.py     # Download Telegram data
│   ├── csv_data_processor.py          # Process CSV files
│   ├── conversation_analyzer.py       # Topic analysis
│   ├── knowledge_extractor.py         # Extract Q&A knowledge
│   ├── redbus2us_scraper.py           # Scrape RedBus2US
│   ├── scrape_redbus2us_h1b.py        # H1B article scraper
│   ├── load_redbus_to_qdrant.py       # Load to Qdrant
│   ├── run_knowledge_extraction.py    # Knowledge pipeline
│   ├── run_vector_pipeline.py         # Vector processing
│   └── __init__.py
│
├── pyproject.toml         # UV package configuration
├── requirements.txt       # Pip dependencies
├── uv.lock               # UV lock file
└── README.md             # This file
```

---

## 🚀 Quick Start

### Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Run the server
uv run python api/main.py
```

### Using Pip

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python api/main.py
```

### Using Docker

```bash
# Build and run
docker compose --profile web up -d
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# MongoDB Atlas
MONGODB_URI=mongodb+srv://...
MONGODB_DATABASE=visa_community
MONGODB_TLS_ENABLED=true
MONGODB_TLS_CERT_FILE=certificates/X509-cert-xxx.pem
MONGODB_AUTH_MECHANISM=MONGODB-X509

# Qdrant Vector DB
QDRANT_HOST=localhost  # or 'qdrant' in Docker
QDRANT_PORT=6333

# Local LLM (Ollama)
OLLAMA_HOST=http://localhost:11434  # or http://host.docker.internal:11434 in Docker
LLM_MODEL=qwen

# Email Service
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

---

## 📡 API Endpoints

### Health & Stats
- `GET /health` - Health check
- `GET /stats` - Database statistics

### Search & AI
- `POST /search` - Vector search conversations
- `POST /chat` - Chat with conversation synthesis
- `POST /api/ai/ask` - AI assistant with RedBus2US knowledge

### Authentication
- `POST /auth/request-code` - Request verification code
- `POST /auth/verify-code` - Verify code and login
- `GET /auth/verify-session` - Verify session token
- `POST /auth/logout` - Logout
- `POST /auth/update-profile` - Update user profile

### Community Chat
- `WebSocket /ws/chat/{email}/{display_name}` - WebSocket chat connection

---

## 🗄️ Database Schema

### MongoDB Collections
- **users** - User profiles and authentication
- **messages** - Community chat messages
- **sessions** - Active user sessions
- **verification_codes** - Email verification codes (TTL index)

### Qdrant Collections
- **visa_conversations** - 767K+ indexed conversations
- **redbus2us_articles** - 127 H1B articles from RedBus2US

---

## 🤖 AI Services

### Enhanced Chat Synthesizer
- Uses Qdrant to search RedBus2US articles
- Generates answers with Qwen LLM (local)
- Provides source attribution with links
- ~5-7 second response time

### Vector Processor
- Sentence-transformers embeddings (all-MiniLM-L6-v2)
- Semantic search with Qdrant
- Category and visa type filtering

---

## 📊 Data Pipeline Scripts

### Telegram Data Download
```bash
uv run python scripts/telegram_csv_downloader.py --all
```

### Process Conversations
```bash
uv run python scripts/csv_data_processor.py
```

### Extract Knowledge
```bash
uv run python scripts/run_knowledge_extraction.py
```

### Scrape RedBus2US
```bash
uv run python scripts/scrape_redbus2us_h1b.py
```

### Load to Qdrant
```bash
uv run python scripts/load_redbus_to_qdrant.py
```

---

## 🔒 Security

- X.509 certificate authentication for MongoDB Atlas
- Session-based authentication with secure tokens
- Email verification for user signup
- CORS configuration for frontend
- Environment variable-based secrets

---

## 🐳 Docker Deployment

The backend runs in Docker with:
- FastAPI on port 8000
- MongoDB Atlas (cloud)
- Qdrant (local container)
- Ollama (host machine via host.docker.internal)

---

## 📝 Development

### Adding New Endpoints

1. Create route in `api/main.py`
2. Add business logic in `services/`
3. Update models if needed in `models/`
4. Test with `curl` or Postman

### Running Tests

```bash
# Run with UV
uv run pytest

# Or with pip
pytest
```

---

## 🤝 Dependencies

**Core:**
- FastAPI - Web framework
- Pydantic - Data validation
- Uvicorn - ASGI server

**AI/ML:**
- sentence-transformers - Embeddings
- qdrant-client - Vector search
- httpx - Async HTTP (for Ollama)

**Database:**
- pymongo - MongoDB driver
- motor - Async MongoDB (WebSockets)

**Utilities:**
- python-dotenv - Environment variables
- beautifulsoup4 - Web scraping
- telethon - Telegram client

---

## 📈 Performance

- **Vector Search**: ~100ms for 767K conversations
- **LLM Response**: ~5-7s (Qwen 4B model)
- **WebSocket Chat**: Real-time, <50ms latency
- **Embeddings**: all-MiniLM-L6-v2 (384 dimensions)

---

## 🔗 Related

- [Frontend README](../frontend/README.md)
- [Main Project README](../README.md)
- [Progress Tracker](../PROGRESS.md)

