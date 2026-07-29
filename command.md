docker compose run --rm fastapi alembic revision --autogenerate -m "initial migration"

docker compose run --rm fastapi alembic upgrade head
