docker compose run --rm fastapi alembic revision --autogenerate -m "initial migration"

docker compose run --rm fastapi alembic upgrade head

# To access postgres
docker exec -it chat-application-postgres psql -U chatuser -d chatdb           

# To access redis
docker exec -it chat-application-redis redis-cli