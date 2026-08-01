.PHONY: help install lint format test build run clean

IMAGE_NAME ?= pdeu-discord-bot
IMAGE_TAG ?= latest

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Sync the uv environment
	uv sync --locked

lint: ## Run ruff and mypy
	uv run ruff check .
	uv run mypy .

format: ## Format code with ruff
	uv run ruff format .

test: ## Run tests
	uv run pytest

build: ## Build the container image using Podman
	podman build \
		--file Containerfile \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		.

run: ## Run the container using Podman. Usage: PDEU_DISCORD_TOKEN=... make run
	podman run --rm -d \
		--name $(IMAGE_NAME) \
		--env PDEU_DISCORD_TOKEN \
		--env PDEU_WATCH_CHANNEL_ID \
		$(IMAGE_NAME):$(IMAGE_TAG)

run-debug: ## TODO comment
	podman run --rm -d \
		--name $(IMAGE_NAME) \
		--env PDEU_DISCORD_TOKEN \
		--env PDEU_WATCH_CHANNEL_ID \
		--env PDEU_LOG_LEVEL=DEBUG \
		$(IMAGE_NAME):$(IMAGE_TAG)

img-clean: ## Remove the :latest container image from local registry
	podman rmi $(IMAGE_NAME):$(IMAGE_TAG)
