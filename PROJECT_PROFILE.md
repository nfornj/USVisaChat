# Visa Community Platform - Project Profile

**Last Updated:** December 19, 2024  
**Version:** 2.0.0  
**Status:** Production Ready

---

## 🎯 Project Overview

**Visa Community Platform** is a full-stack real-time application that combines community chat with AI-powered search through 1.5M+ visa conversations. Built for the visa community to share experiences and get intelligent answers about visa processes.

### Key Features

- **Real-time Community Chat** - WebSocket-based group messaging
- **AI Assistant** - Search through 1.5M+ visa conversations with intelligent answers
- **Vector Search** - Semantic search using Qdrant vector database
- **Authentication** - Email-based verification system
- **Image Sharing** - Upload and share images in chat
- **Responsive UI** - Modern React interface with dark mode

---

## 🏗️ Technical Architecture

### Frontend Stack

- **Framework**: React 18 + TypeScript
- **UI Library**: Material-UI (MUI)
- **Styling**: Tailwind CSS
- **Build Tool**: Vite
- **State Management**: React Hooks + Context
- **HTTP Client**: Axios
- **Real-time**: WebSocket API

### Backend Stack

- **Framework**: FastAPI (Python)
- **Server**: Uvicorn (ASGI)
- **Database**: MongoDB Atlas (Cloud)
- **Vector DB**: Qdrant (1.5M+ vectors)
- **LLM**: Groq API (Llama 3.1 8B) / Ollama (Local)
- **Authentication**: Email verification + Session tokens
- **Email**: SMTP (Gmail/SendGrid)
- **Image Processing**: Pillow (PIL)

### Infrastructure

- **Containerization**: Docker + Docker Compose
- **Package Manager**: UV (Python)
- **Deployment**: Production-ready profiles
- **Monitoring**: Health checks + Logging
- **Security**: TLS certificates + Environment variables

---

## 📊 Data & Performance

### Vector Database

- **Total Vectors**: 1,534,667 visa conversations
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2
- **Dimensions**: 384
- **Search Speed**: 50-200ms
- **Collections**:
  - `visa_conversations` (1.5M+ vectors)
  - `redbus2us_articles` (60+ H1B articles)

### Performance Metrics

- **Vector Search**: 50-200ms average
- **WebSocket Latency**: <10ms
- **LLM Response**: 1-2s (Groq) / 5-7s (Ollama)
- **Concurrent Users**: 100+ tested
- **Database**: MongoDB Atlas (Cloud-native)

---

## 🔧 LLM Configuration

### Current Setup

- **Primary Model**: Llama 3.1 8B
- **Local Development**: Ollama (Llama 3.1 8B)
- **Production**: Groq API (Llama 3.1 8B)
- **Fallback**: Automatic fallback from Groq to Ollama

### Environment Variables

```bash
# LLM Configuration
LLM_PROVIDER=groq  # or ollama
LLM_MODEL=llama3.1:8b
GROQ_API_KEY=your-groq-api-key
OLLAMA_HOST=http://localhost:11434
```

---

## 🚀 Deployment Profiles

### Development Profile

```bash
docker compose --profile development up qdrant visa-web -d
```

- **LLM**: Ollama (Local)
- **Components**: Qdrant + Frontend
- **Use Case**: Local development

### Production Profile

```bash
docker compose --profile production up qdrant visa-prod -d
```

- **LLM**: Groq API
- **Components**: Qdrant + Frontend + All services
- **Use Case**: Production deployment

---

## 📁 Project Structure

```
Visa/
├── backend/
│   ├── api/
│   │   └── main.py                    # FastAPI server
│   ├── services/
│   │   ├── llm_service.py            # LLM service (Ollama/Groq)
│   │   ├── enhanced_chat_synthesizer.py  # AI response synthesis
│   │   ├── simple_vector_processor.py    # Vector search
│   │   └── email_service.py          # Email notifications
│   ├── models/
│   │   ├── mongodb_connection.py     # Database connection
│   │   ├── community_chat.py         # WebSocket chat
│   │   └── user_auth.py              # Authentication
│   └── scripts/                      # Data processing scripts
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # Main application
│   │   ├── CommunityChat.tsx         # Chat interface
│   │   ├── AIAssistant.tsx           # AI search interface
│   │   └── components/                # UI components
│   └── package.json
├── docker-compose.yml                # Service orchestration
├── Dockerfile.fullstack              # Multi-stage build
└── PROJECT_PROFILE.md                # This file
```

---

## 🔐 Security & Authentication

### Authentication System

- **Method**: Email-based verification
- **Process**: Email → 6-digit code → Session token
- **Sessions**: 30-day expiry with TTL
- **Security**: No passwords, trust-based community access

### Data Security

- **MongoDB**: TLS encryption + Certificate authentication
- **Environment**: All secrets in .env file
- **API**: CORS enabled for browser access
- **Images**: Compressed and validated uploads

---

## 📈 API Endpoints

### REST API

- `GET /health` - Health check
- `GET /stats` - Vector statistics
- `POST /search` - Vector search
- `POST /chat` - AI chat synthesis
- `POST /api/ai/ask` - RedBus2US AI assistant
- `POST /auth/request-code` - Email verification
- `POST /auth/verify-code` - Code verification
- `POST /chat/upload-image` - Image upload

### WebSocket

- `ws://host/ws/chat/{email}/{name}` - Real-time chat

---

## 🛠️ Development Workflow

### Local Development

```bash
# 1. Install Ollama and pull model
ollama pull llama3.1:8b
ollama serve

# 2. Set up environment
cp env.template .env
# Edit .env with local values

# 3. Start development
docker compose --profile development up qdrant visa-web -d

# 4. Access application
open http://localhost:8000
```

### Production Deployment

```bash
# 1. Set up production environment
cp env.template .env
# Edit .env with production values

# 2. Deploy to production
docker compose --profile production up -d

# 3. Monitor deployment
docker compose ps
docker compose logs -f
```

---

## 📊 Monitoring & Health

### Health Checks

- **Application**: `GET /health` - Returns system status
- **Qdrant**: `GET /health` - Returns vector DB status
- **Docker**: Container health checks every 30s

### Logging

- **Application**: Structured logging with levels
- **Docker**: Container logs with rotation
- **MongoDB**: Connection and query logs
- **LLM**: Request/response logging

---

## 🔄 Data Pipeline

### Data Sources

- **Telegram**: Community chat exports
- **RedBus2US**: H1B articles and guides
- **Processing**: 4-step pipeline (chunking, sessionization, topic modeling, embeddings)

### Data Processing

1. **Download**: Telegram CSV files
2. **Clean**: Data cleanup and validation
3. **Analyze**: Topic modeling and classification
4. **Embed**: Vector embeddings for search
5. **Index**: Store in Qdrant vector database

---

## 🎨 User Interface

### Design System

- **Theme**: Material-UI with custom theme
- **Colors**: Cyan-blue primary, professional palette
- **Typography**: System fonts (Telegram-style)
- **Dark Mode**: Full dark/light mode support
- **Responsive**: Mobile-first design

### Key Components

- **Community Chat**: Real-time messaging with avatars
- **AI Assistant**: ChatGPT-style interface
- **Authentication**: Email verification flow
- **Image Sharing**: Upload and display images
- **User Management**: Profile editing and display names

---

## 🚀 Recent Updates

### December 19, 2024

- ✅ **LLM Service Refactor**: Created flexible LLM service supporting both Ollama and Groq
- ✅ **Llama 3.1 8B Integration**: Upgraded from Qwen to Llama 3.1 8B
- ✅ **Production Configuration**: Added production-ready Docker Compose profiles
- ✅ **Environment Management**: Improved environment variable handling
- ✅ **Resource Limits**: Added CPU and memory limits for production
- ✅ **Health Monitoring**: Enhanced health checks and monitoring
- ✅ **Project Cleanup**: Removed unauthorized documentation files, test files, logs, and temporary data
- ✅ **Code Organization**: Streamlined project structure following cursor rules (3 docs max)
- ✅ **Telegram Integration Fix**: Fixed missing telegram_read.py module and verified Telegram functionality
- ✅ **Telegram Full Test**: Successfully connected to Telegram API and discovered 181 chats including visa-related groups
- ✅ **RedBus2US Data Collection**: Downloaded 295 comprehensive articles from last year across H1B, F1, Immigration, and H4 visa categories

### Previous Updates

- ✅ **MongoDB Atlas Migration**: Moved from SQLite to cloud database
- ✅ **Image Upload System**: Added image sharing with compression
- ✅ **RedBus2US Integration**: Added authoritative H1B knowledge base
- ✅ **Authentication System**: Email-based verification with sessions
- ✅ **Vector Search**: 1.5M+ conversations indexed and searchable

---

## 🔮 Future Roadmap

### Planned Features

- **Private Messaging**: Direct user-to-user chat
- **User Profiles**: Enhanced profile management with avatars
- **File Sharing**: Document upload and sharing
- **Multi-language**: Support for multiple languages
- **Voice Input**: Voice-to-text for AI assistant
- **OAuth Integration**: Google/Microsoft login options

### Technical Improvements

- **Caching**: Redis for improved performance
- **Load Balancing**: Multiple app instances
- **Monitoring**: Advanced metrics and alerting
- **Backup**: Automated backup strategies
- **CI/CD**: Automated deployment pipeline

---

## 📞 Support & Maintenance

### Troubleshooting

- **Health Checks**: `curl http://localhost:8000/health`
- **Logs**: `docker compose logs -f`
- **Restart**: `docker compose restart`
- **Update**: `git pull && docker compose build --no-cache`

### Common Issues

1. **MongoDB Connection**: Check certificates and connection string
2. **LLM Errors**: Verify API keys and model availability
3. **Qdrant Issues**: Check memory and restart service
4. **Frontend Loading**: Verify application is running

---

## 📋 Project Status

### Current Status: ✅ Production Ready

- **Backend**: Fully functional with all features
- **Frontend**: Complete UI with all components
- **Database**: MongoDB Atlas + Qdrant operational
- **LLM**: Groq API + Ollama support
- **Deployment**: Docker Compose profiles ready
- **Security**: TLS + authentication implemented
- **Monitoring**: Health checks and logging active

### Performance: ✅ Optimized

- **Search Speed**: Sub-second vector search
- **Response Time**: Fast LLM responses (1-2s)
- **Scalability**: Tested with 100+ concurrent users
- **Reliability**: Auto-restart and health monitoring

### Security: ✅ Secure

- **Authentication**: Email-based verification
- **Data Encryption**: TLS for all connections
- **Environment**: Secure secret management
- **Access Control**: Session-based authorization

---

**This project profile is automatically updated with every code change to maintain accurate project documentation.**
