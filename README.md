# 🌐 Visa Community Platform

Real-time community chat + AI-powered search through 1.5M+ visa conversations.

**Quick Start:** `docker compose --profile web up qdrant visa-web -d` → http://localhost:8000

---

## ⚡ Quick Start

### 1. Start the Platform

```bash
docker compose --profile web up qdrant visa-web -d
```

### 2. Access the UI

```
http://localhost:8000
```

### 3. Create Your Profile

- Enter your name
- Enter your email
- Start chatting!

---

## 🎯 Features

### 💬 Community Chat

- Real-time group messaging (like Telegram)
- See who's online
- Message history
- Instant access

### 🤖 AI Assistant

- Search 1.5M+ visa conversations
- Get synthesized answers
- See source citations
- ChatGPT-style interface

---

## 📚 Usage

### Community Chat

1. Click "Community Chat" tab
2. Type message and press Enter
3. See responses in real-time
4. View online users in sidebar

### AI Assistant

1. Click "AI Assistant" tab
2. Ask a question (e.g., "H1B document requirements")
3. Get synthesized answer with sources
4. View conversation history in sidebar

---

## 🎨 Example Questions

**Documents:**

- "What documents do I need for H1B stamping?"
- "F1 visa requirements"

**Timeline:**

- "How long does visa processing take?"
- "Mumbai consulate wait times"

**Experience:**

- "Interview experience at Delhi consulate"
- "Dropbox eligibility"

---

## 🔧 Docker Commands

```bash
# Start
docker compose --profile web up qdrant visa-web -d

# View logs
docker compose logs visa-web -f

# Stop
docker compose --profile web down

# Rebuild (after code changes)
docker compose build --no-cache visa-web
docker compose --profile web up qdrant visa-web -d

# Check health
curl http://localhost:8000/health
```

---

## 💻 Local Development

### Backend

```bash
docker compose up qdrant -d
uv sync
python visa_mcp_server.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Access: http://localhost:3000

---

## 🗄️ MongoDB Configuration (Required)

The platform uses **MongoDB Atlas** for cloud-native storage of chat history and user data.

### 1. Create MongoDB Atlas Cluster

1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free cluster (M0 tier is sufficient for development)
3. Create a database user with read/write access
4. Whitelist your IP address (or use 0.0.0.0/0 for dev)

### 2. Get Connection String

1. Click "Connect" on your cluster
2. Choose "Connect your application"
3. Copy the connection string
4. It will look like: `mongodb+srv://username:password@cluster.mongodb.net/`

### 3. Configure Environment Variables

Create a `.env` file:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=visa_community

# Optional: For certificate-based auth
MONGODB_TLS_ENABLED=true
MONGODB_TLS_CERT_FILE=/path/to/certificate.pem
MONGODB_TLS_CA_FILE=/path/to/ca-certificate.pem
```

### 4. Create Indexes (First Time Only)

After starting the server, indexes will be created automatically. Or run:

```bash
uv run python -c "from mongodb_connection import mongodb_client; mongodb_client.create_indexes()"
```

**Note:** The application will fail to start without MongoDB connection. Ensure your cluster is accessible.

---

## 📧 Email Configuration (Optional)

By default, the platform uses **mock mode** (verification codes are logged to console). To enable **real email sending via Gmail**:

### 1. Get Gmail App Password

1. Enable **2-Factor Authentication** on your Google account
2. Visit: https://myaccount.google.com/apppasswords
3. Create an "App Password" for "Mail"
4. Copy the 16-character password

### 2. Configure Environment Variables

Create a `.env` file (or edit existing one):

```bash
# Email Configuration
EMAIL_MODE=smtp

# SMTP Configuration (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=xxxx-xxxx-xxxx-xxxx  # Your App Password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Visa Community Platform
```

### 3. Restart the Service

```bash
docker compose --profile web restart visa-web
```

**Note:** Works with Gmail, Outlook, or any SMTP server. Just change the `SMTP_HOST` and `SMTP_PORT` accordingly.

---

## 📊 System Stats

- **Vectors:** 1,534,667 visa conversations
- **Search Speed:** 50-200ms
- **Embedding Model:** sentence-transformers (384 dim)
- **Vector Database:** Qdrant
- **Chat & Auth Storage:** MongoDB Atlas (Cloud)

---

## 🏗️ Architecture

```
User → React Frontend
         ↓
     FastAPI Backend
       ├── WebSocket → Community Chat (MongoDB Atlas)
       ├── Auth System → User Management (MongoDB Atlas)
       └── REST API → AI Search (Qdrant 1.5M+ vectors)
```

---

## 📁 Project Structure

```
/
├── visa_mcp_server.py          # Main server
├── community_chat.py            # WebSocket chat
├── chat_synthesizer.py         # AI synthesis
├── simple_vector_processor.py   # Vector search
├── frontend/                    # React UI
├── docker-compose.yml           # Services
├── Dockerfile.fullstack         # Build config
└── PROGRESS.md                  # Development history
```

---

## 🔒 Security Note

**Current Design:** Email-based authentication with verification codes

- Email verification (6-digit codes)
- Session-based authentication
- No passwords required
- Configurable email service (mock/SMTP/SendGrid/AWS SES)
- Suitable for community use
- For production: Enable real email sending (see Email Configuration section)

---

## 📖 Documentation

- **PROGRESS.md** - Complete development history and technical details
- **API Docs** - http://localhost:8000/docs (when running)

---

## 🚀 Technology Stack

**Backend:** FastAPI, MongoDB Atlas, Qdrant, PyMongo, sentence-transformers, UV  
**Frontend:** React, TypeScript, Vite, Tailwind CSS  
**Infrastructure:** Docker, Docker Compose, Cloud-native (MongoDB Atlas)

---

## 🎯 Use Cases

| Want to...                      | Use This           |
| ------------------------------- | ------------------ |
| Chat with visa applicants       | Community Chat tab |
| Share your experience           | Community Chat tab |
| Search historical conversations | AI Assistant tab   |
| Find specific requirements      | AI Assistant tab   |
| Get detailed visa info          | AI Assistant tab   |

---

## ❓ Troubleshooting

### "Cannot connect to Qdrant"

```bash
docker compose up qdrant -d
docker compose ps
```

### "Port 8000 already in use"

```bash
lsof -ti:8000 | xargs kill -9
```

### "Disconnected from chat"

Refresh the page.

---

## 📈 Performance

- **Vector Search:** Sub-second response
- **WebSocket:** <10ms latency
- **Concurrent Users:** Tested up to 100
- **Database:** 1.5M+ conversations indexed

---

## 🔮 Future Enhancements

- Private messaging
- User profiles with avatars
- File sharing
- Multi-language support
- Voice input
- OAuth integration (Google, Microsoft)

---

**Built with ❤️ for the visa community**

For detailed progress and development history, see [PROGRESS.md](PROGRESS.md)
