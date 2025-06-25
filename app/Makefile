.DEFAULT_GOAL := help


RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
BLUE=\033[0;34m
NC=\033[0m # No Color


.PHONY: help lint pretty

help:  ## Display this help screen
	@echo "\033[1mAvailable commands:\033[0m"
	@grep -E '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' | sort

lint: ## Run all linters on source code
	@echo "${YELLOW}\nRunning all linters...${NC}"
	@poetry run ruff check
	@poetry run mypy ../backend/

pretty: ## Run all code formatters on source code
	@echo "${YELLOW}\nPrettifying imports...${NC}"
	@poetry run isort ../backend/
	@echo "${YELLOW}Removing unused imports...${NC}"
	@poetry run autoflake -ir --remove-all-unused-imports ../backend/
	@echo "${YELLOW}Formatting code...${NC}"
	@poetry run black ../backend/

validate: pretty lint ## Run all code quality checks