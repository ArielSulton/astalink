.PHONY: dev prod down down-prod frontend-install backend-install test-backend logs clean

dev:
	docker compose -f docker-compose.yml up --build

prod:
	docker compose -f docker-compose.prod.yml up --build -d

down:
	docker compose -f docker-compose.yml down

down-prod:
	docker compose -f docker-compose.prod.yml down

frontend-install:
	cd frontend && npm install

backend-install:
	cd backend && uv sync

test-backend:
	cd backend && uv run pytest tests/ -v

logs:
	docker compose logs -f

clean:
	docker compose down -v
	docker system prune -f
