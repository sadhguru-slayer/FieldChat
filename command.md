docker compose run --rm fastapi alembic revision --autogenerate -m "message model updated"

docker compose run --rm fastapi alembic upgrade head

# To access postgres
docker exec -it chat-application-postgres psql -U chatuser -d chatdb           

# To access redis
docker exec -it chat-application-redis redis-cli

# --- PRODUCTION COMMANDS ---

# Build and start services in detached mode
docker compose -f docker-compose.prod.yaml up -d --build

# Run database migrations
docker compose -f docker-compose.prod.yaml --profile migration run --rm alembic

# Stop all services
docker compose -f docker-compose.prod.yaml down

# View logs
docker compose -f docker-compose.prod.yaml logs -f

# Access postgres database
docker exec -it chat-application-postgres psql -U chatuser -d chatdb

# Access redis cli
docker exec -it chat-application-redis redis-cli

