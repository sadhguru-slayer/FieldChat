# ⚡ FieldChat Backend

High-performance asynchronous real-time backend for **FieldChat**, built with **FastAPI**, **PostgreSQL**, **Redis Streams**, **Redis Pub/Sub**, and **SQLAlchemy 2.0 Async**.

The backend is designed around persistent WebSocket connections, asynchronous message processing, transactional event publishing, targeted presence, and horizontally scalable real-time communication.

## ✨ Highlights

* 🚀 **Async FastAPI + WebSockets** for low-latency real-time communication
* 📨 **Transactional Outbox** for reliable publishing of persistent message events
* 📡 **Redis Streams** for durable asynchronous message-event delivery
* ⚡ **Redis Pub/Sub** for lightweight ephemeral events such as typing and presence
* 🔄 **Multi-instance WebSocket fan-out** using Redis consumer groups
* 🟢 **Targeted presence system** for efficient online/offline state updates
* 🗄️ **PostgreSQL + SQLAlchemy 2.0 Async** for persistent application state
* 📦 **Batch outbox processing** using Redis pipelines
* 🛡️ **JWT authentication** with access and refresh tokens
* 🔐 **Argon2 password hashing** using `pwdlib`
* 🔔 **VAPID Web Push** for background/offline notifications
* 🐳 **Dockerized production deployment**

> A detailed system architecture diagram will be added separately.

---

## 🛠️ Tech Stack

| Component          | Technology              |
| :----------------- | :---------------------- |
| Backend            | FastAPI                 |
| ASGI Server        | Uvicorn                 |
| Database           | PostgreSQL 16           |
| ORM                | SQLAlchemy 2.0 Async    |
| Migrations         | Alembic                 |
| Event Streaming    | Redis Streams           |
| Ephemeral Events   | Redis Pub/Sub           |
| Cache / State      | Redis                   |
| Authentication     | JWT                     |
| Password Hashing   | Argon2 / pwdlib         |
| Push Notifications | pywebpush / VAPID       |
| Deployment         | Docker / Docker Compose |

---

## 📡 Real-Time Architecture

FieldChat uses different event transports depending on whether an event needs durability.

### Persistent Events

Persistent message changes use a **Transactional Outbox → Redis Streams** pipeline.

Examples:

* Message creation
* Message editing
* Message deletion
* Message forwarding
* Other persistent message state changes

The database change and its corresponding outbox event are committed together. A background worker then publishes pending events to Redis Streams.

This prevents a successfully committed database change from losing its real-time event because Redis was temporarily unavailable.

### Ephemeral Events

Events that do not require persistence or replay use **Redis Pub/Sub**.

Examples:

* Typing indicators
* Presence updates
* Lightweight delivery/read events
* Other temporary real-time state

This keeps high-frequency ephemeral events lightweight without adding unnecessary database and outbox overhead.

---

## 🔄 Transactional Outbox

Persistent events follow the transactional outbox pattern.

When a persistent message operation occurs:

1. The message state is modified in PostgreSQL.
2. An outbox event is created in the same database transaction.
3. Both changes are committed atomically.
4. A background outbox worker reads pending events.
5. Events are published to Redis Streams.
6. FastAPI instances consume the stream through Redis consumer groups.
7. Local WebSocket connections receive the event.

The outbox worker processes events in batches using:

* `LIMIT`
* `FOR UPDATE SKIP LOCKED`
* Redis pipelines
* Batch commits

The system provides **at-least-once event delivery**, so consumers are designed with duplicate event processing in mind.

---

## 📡 Redis Streams

The primary message event stream is:

```text
stream:message-events
```

Each FastAPI instance uses its own consumer group.

This allows every application instance to receive message events while only delivering them to the WebSocket connections maintained by that instance.

Redis Streams also provide buffering and the ability to recover events that were not successfully processed.

A separate notification stream is available for decoupling notification processing from real-time message delivery:

```text
stream:notification-events
```

---

## 🟢 Presence

Presence is implemented using Redis state and targeted subscriptions rather than global broadcasts.

Redis is used for:

* Online user tracking
* Last-seen timestamps
* Presence watchers
* Per-user WebSocket connection tracking
* Conversation membership caching

This allows presence updates to be sent only to users who are interested in them.

---

## 🔐 Authentication & Security

* JWT access tokens
* JWT refresh tokens
* Argon2 password hashing
* Authenticated WebSocket connections
* Conversation membership validation
* Message ownership and permission checks
* Role-based permissions for administrative message deletion

---

## 🔔 Notifications

FieldChat supports VAPID-based Web Push notifications for users who are offline or not actively viewing a conversation.

Notification processing is designed to remain independent from the real-time message delivery path so external push providers do not unnecessarily block message delivery.

---

## 📡 API Reference

### Authentication

| Method | Endpoint                  | Description                     |
| :----- | :------------------------ | :------------------------------ |
| `POST` | `/api/auth/register`      | Register a new user             |
| `POST` | `/api/auth/login`         | Authenticate and receive tokens |
| `POST` | `/api/auth/token/refresh` | Refresh access token            |
| `GET`  | `/api/auth/me`            | Get authenticated user          |

### Conversations & Messages

| Method   | Endpoint                            | Description                                |
| :------- | :---------------------------------- | :----------------------------------------- |
| `GET`    | `/api/conversations/`               | List conversations and unread status       |
| `POST`   | `/api/conversations/create-dm`      | Create or initialize a direct conversation |
| `POST`   | `/api/conversations/create-group`   | Create a group conversation                |
| `GET`    | `/api/messages/get-messages`        | Cursor-paginated message history           |
| `POST`   | `/api/messages/create-message`      | Send message via REST fallback             |
| `PATCH`  | `/api/messages/edit-message`        | Edit a message                             |
| `DELETE` | `/api/messages/delete-for-everyone` | Delete a message for everyone              |
| `POST`   | `/api/messages/react-to-message`    | Add or update a reaction                   |

---

## 🔌 WebSocket

WebSocket endpoint:

```text
ws://localhost:8000/ws?token=<ACCESS_TOKEN>
```

### Connection Events

* `join_conversation`
* `leave_conversation`

### Message Events

* `message.create`
* `message.edit`
* `message.delete_for_everyone`
* `message.delete_for_me`
* `message.delivered`
* `message.read`
* `message.react`
* `message.remove_react`

### Real-Time Events

* `typing.start`
* `typing.stop`
* `presence.subscribe`
* `presence.unsubscribe`

REST endpoints are also available as a fallback for core message operations.

---

## 📁 Project Structure

```text
fieldchat-backend/
├── app/
│   ├── admin/                 # Admin panel
│   ├── core/                  # Security, JWT & configuration
│   ├── models/                # SQLAlchemy models
│   ├── redis/                 # Streams, Pub/Sub & event handlers
│   ├── router/                # API route handlers
│   ├── schema/                # Pydantic schemas
│   ├── services/              # Business logic & background services
│   │   ├── outbox_service.py
│   │   └── notification_service.py
│   ├── ws/                    # WebSocket connection management
│   ├── database.py            # Async database engine
│   └── main.py                # FastAPI application
├── alembic/                   # Database migrations
├── Dockerfile                 # Production container
├── docker-compose.yaml        # Container orchestration
└── requirements.txt           # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.10+
* PostgreSQL 16
* Redis

### Local Setup

```bash
git clone <repository-url>
cd fieldchat-backend

python -m venv venv
```

Activate the environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file:

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

### Database Migration

```bash
alembic upgrade head
```

### Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🐳 Docker

Run the complete backend stack with:

```bash
docker-compose up -d --build
```

This starts the application together with its PostgreSQL and Redis dependencies.

---

## 📌 Engineering Focus

FieldChat is primarily built as a backend engineering project focused on:

* Asynchronous Python
* Real-time WebSocket systems
* Distributed event delivery
* Transactional consistency
* Redis Streams and consumer groups
* Redis Pub/Sub
* PostgreSQL data modeling
* Async database access
* Background workers
* Horizontal scaling
* Connection and state management
* Reliable message delivery

A detailed architecture document and system design diagram will cover the internal event flow, scaling model, failure handling, and infrastructure decisions.
