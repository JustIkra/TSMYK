# Docker shortcuts
# ENV in .env controls hot-reload: dev=on, prod=off
.PHONY: base-build build up down logs restart shell prod-up

# Build base image (run once, or when system deps change)
base-build:
	docker build -f Dockerfile.base -t tsmuk-base:latest .

# Standard commands (uses override.yml automatically = volume mounts)
build:
	docker compose build --parallel

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f app worker

restart:
	docker compose restart app worker

shell:
	docker compose exec app bash

# Production mode (no volume mounts, no override)
prod-up:
	docker compose -f docker-compose.yml up -d
