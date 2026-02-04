SHELL := /bin/bash

COMPOSE ?= docker compose
SERVICE ?= server
NAME ?= user

.PHONY: help build up down restart logs ps clean client client-docker test test-docker

help:
	@echo "Targets:"
	@echo "  build         Build Docker images"
	@echo "  up            Start the server"
	@echo "  down          Stop containers"
	@echo "  restart       Restart containers"
	@echo "  logs          Follow server logs"
	@echo "  ps            Show running containers"
	@echo "  clean         Remove containers and volumes"
	@echo "  client        Run a local client: make client NAME=Pedro"
	@echo "  client-docker Run a dockerised client: make client-docker NAME=Pedro"
	@echo "  test          Run pytest locally"
	@echo "  test-docker   Run pytest in a one-off container on the compose network"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f $(SERVICE)

ps:
	$(COMPOSE) ps

clean:
	$(COMPOSE) down -v --remove-orphans

client:
	python3 client.py $(NAME)

client-docker:
	$(COMPOSE) run --rm client python client.py $(NAME)

test:
	pytest -q

test-docker:
	$(COMPOSE) run --rm -e ADDRESS=server -e PORT=8000 client pytest -q
