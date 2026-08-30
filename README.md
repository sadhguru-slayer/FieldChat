# ⚡ Fieldchat Backend Engine

High-performance, asynchronous real-time backend engine for **Fieldchat**, powered by **FastAPI**, **PostgreSQL**, **Redis Pub/Sub**, and **SQLAlchemy 2.0 Async Engine**.

---

## ✨ Core Highlights

- **🚀 Async FastAPI & Uvicorn**: Fully asynchronous request handling built for low-latency REST APIs and persistent WebSockets.
- **📡 Scalable Redis Pub/Sub Broadcasts**: Multi-node horizontal scaling support with event broadcasting for direct messages, groups, typing events, and message status updates.
- **🟢 Targeted Presence Engine ($O(1)$)**: Efficient online status and `last_seen` timestamp management using subscription channels instead of expensive $O(N)$ global broadcasts.
- **🛡️ Security & Authentication**: Modern password hashing using **Argon2** (`pwdlib`) and dual JWT (access/refresh) token management.
- **🗄️ Database Connection Pooling & Resilience**: Optimized SQLAlchemy engine with connection recycling (`pool_recycle=300`), health pre-pings, and automatic zombie connection cleanup on startup.
- **🔔 VAPID WebPush Service**: Integrated push notification fallback (`pywebpush`) for delivering alerts to offline or backgrounded mobile devices.

---

## 🛠️ Tech Stack

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Database**: [PostgreSQL 16](https://www.postgresql.org/) + [SQLAlchemy 2.0 (Async)](https://www.sqlalchemy.org/)
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/)
- **In-Memory Cache & Pub/Sub**: [Redis](https://redis.io/)
- **Authentication**: JWT (`python-jose`/`PyJWT`) + Argon2 (`pwdlib`)
- **Push Notifications**: [pywebpush](https://github.com/web-push-libs/pywebpush) (VAPID)
- **Containerization**: [Docker](https://www.docker.com/) & Docker Compose

---

## 🚀 Quick Start

### Option A: Local Development Setup

#### 1. Prerequisites
- **Python 3.10+**
- **PostgreSQL 16** running locally or via Docker
- **Redis Server** running locally or via Docker

#### 2. Virtual Environment Setup
```bash
# Navigate to backend directory
cd fieldchat-backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### 3. Environment Configuration
Create a `.env` file in `fieldchat-backend/`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/fieldchat
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your_super_secret_jwt_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
VAPID_PRIVATE_KEY=your_vapid_private_key
VAPID_PUBLIC_KEY=your_vapid_public_key
VAPID_CLAIMS_SUB=mailto:admin@example.com
```

#### 4. Run Database Migrations
```bash
alembic upgrade head
```

#### 5. Start Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

### Option B: Docker Compose (Production / Instant Run)

To run PostgreSQL, Redis, and FastAPI in containerized environments:

```bash
# Start all services in detached mode
docker-compose up -d --build
```

---

## 📡 API & WebSocket Reference Overview

### 🔐 Authentication (`/api/auth`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Authenticate & receive token pair |
| `POST` | `/api/auth/token/refresh` | Refresh access token |
| `GET` | `/api/auth/me` | Fetch authenticated user profile |

### 💬 Conversations & Messages (`/api/conversations`, `/api/messages`)
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/conversations/` | List all user conversations & unread status |
| `POST` | `/api/conversations/create-dm` | Initialize Direct Message |
| `POST` | `/api/conversations/create-group` | Create group chat |
| `GET` | `/api/messages/get-messages` | Cursor-paginated message history |
| `POST` | `/api/messages/create-message` | Send message (REST fallback) |
| `PATCH` | `/api/messages/edit-message` | Edit existing message |
| `DELETE` | `/api/messages/delete-for-everyone` | Unsend message for all members |
| `POST` | `/api/messages/react-to-message` | Toggle emoji reaction |

### 🔌 Real-Time WebSocket (`/ws`)
- **URL**: `ws://localhost:8000/ws?token=<ACCESS_TOKEN>`
- **Events Handled**:
  - `join_conversation`, `leave_conversation`
  - `message.create`, `message.edit`, `message.delete_for_everyone`, `message.delete_for_me`
  - `message.delivered`, `message.read`
  - `message.react`, `message.remove_react`
  - `typing.start`, `typing.stop`
  - `presence.subscribe`, `presence.unsubscribe`

---

## 📁 Project Structure

```text
fieldchat-backend/
├── app/
│   ├── admin/          # FastAdmin panel configuration
│   ├── core/           # Core security, JWT & configuration
│   ├── models/         # SQLAlchemy database models
│   ├── redis/          # Redis connection & pub/sub event handlers
│   ├── router/         # FastAPI endpoint route handlers
│   ├── schema/         # Pydantic request/response schemas
│   ├── services/       # Notification & presence services
│   ├── ws/             # WebSocket ConnectionManager & socket loops
│   ├── database.py     # Database engine setup & pooling
│   └── main.py         # FastAPI application instantiation
├── alembic/            # Database migration scripts
├── docker-compose.yaml # Docker Compose development setup
├── Dockerfile          # Production container configuration
└── requirements.txt    # Python dependencies
```
