#!/bin/bash
docker-compose down -v
docker-compose up -d
sleep 5 # give postgres time to initialize
docker-compose exec api alembic upgrade head
docker-compose exec api python -u -m ingestion.seed