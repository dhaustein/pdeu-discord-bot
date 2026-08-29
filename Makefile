.PHONY: help install lint format test run run-debug img-clean

IMAGE_NAME ?= pdeu-discord-bot
IMAGE_TAG ?= latest

BUILD_STAMP := .build-stamp
SOURCES := $(shell find cogs config -name '*.py') $(wildcard *.py) Containerfile .containerignore pyproject.toml uv.lock

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Sync the uv environment (--frozen: release-please bumps pyproject.toml
	# version without regenerating uv.lock, so version-only drift must not fail CI)
	uv sync --frozen

lint: ## Run ruff and mypy
	uv run ruff check .
	uv run mypy .

format: ## Format code with ruff
	uv run ruff format .

test: ## Run tests (pytest-randomly shuffles order)
	uv run pytest

build: $(BUILD_STAMP) ## Build the container image using Podman (rebuilds when sources change)

$(BUILD_STAMP): $(SOURCES)
	podman build \
		--file Containerfile \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		.
	@touch $(BUILD_STAMP)

run: build ## Run the container using Podman. Usage: PDEU_DISCORD_TOKEN=... make run
	podman run --rm -d \
		--name $(IMAGE_NAME) \
		--env PDEU_DISCORD_TOKEN \
		--env PDEU_WATCH_CHANNEL_ID \
		--volume $(IMAGE_NAME)-data:/app/data:Z \
		$(IMAGE_NAME):$(IMAGE_TAG)

run-debug: build ## Run the container using Podman, with DEBUG level logging on
	podman run --rm -d \
		--name $(IMAGE_NAME) \
		--env PDEU_DISCORD_TOKEN \
		--env PDEU_WATCH_CHANNEL_ID \
		--env PDEU_LOG_LEVEL=DEBUG \
		--volume $(IMAGE_NAME)-data:/app/data:Z \
		$(IMAGE_NAME):$(IMAGE_TAG)

img-clean: ## Remove the :latest container image from local registry
	podman rmi $(IMAGE_NAME):$(IMAGE_TAG)
	rm -f $(BUILD_STAMP)
