.PHONY: setup up down logs test lint migrate backup

setup:
	test -f .env || cp .env.example .env

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	pytest

lint:
	ruff check .

migrate:
	alembic upgrade head

backup:
	mkdir -p backups
	docker compose exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -Fc' > "backups/uga_stove_$$(date +%Y%m%d_%H%M%S).dump"
