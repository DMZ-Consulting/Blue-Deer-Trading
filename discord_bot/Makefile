# Makefile for Blue Deer Trading Discord Bot

# Variables
PYTHON := python3
UVICORN := uvicorn
APP := app.main:app
PORT := 8000
TEST_CMD := pytest

# Phony targets
.PHONY: run run_local test init_db clean

# Default target
all: run

# Run the application using uvicorn
run:
	cd backend && $(UVICORN) $(APP) --host 0.0.0.0 --port $(PORT)

# Run the application locally (same as run for now, can be customized if needed)
run_local:
	@if [ ! -f backend/local.db ]; then \
		$(MAKE) init_db; \
	fi
	cd backend && ./run_local.sh

# Run tests
test:
	cd backend && $(TEST_CMD) tests/test_main.py

# Initialize the database
init_db:
	cd backend && $(PYTHON) -m app.init_db

# Clean up generated files (add more patterns as needed)
clean:
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete

# Help target
help:
	@echo "Available targets:"
	@echo "  run         - Run the application using uvicorn"
	@echo "  run_local   - Run the application locally using run.sh"
	@echo "  test        - Run the tests"
	@echo "  init_db     - Initialize the database"
	@echo "  clean       - Clean up generated files"
	@echo "  help        - Show this help message"

# Database migration command with check
db-upgrade:
	@if $(MAKE) db-check > /dev/null 2>&1; then \
		echo "Database is already up to date. No upgrade needed."; \
	else \
		echo "Upgrading database..."; \
		alembic upgrade head; \
	fi

# Command to run migrations in production with check
prod-db-upgrade:
	@echo "Are you sure you want to run migrations on the production database? (y/n)"
	@read answer; \
	if [ "$$answer" = "y" ]; then \
		echo "Running production database migrations..."; \
		alembic upgrade head; \
	else \
		echo "Migration cancelled."; \
	fi

# Command to show migration plan without executing
db-upgrade-plan:
	alembic upgrade --sql head

# Check if database is up to date
db-check:
	@if alembic current | grep -q "(head)"; then \
		echo "Database is already up to date."; \
		exit 0; \
	else \
		echo "Database needs to be upgraded."; \
		exit 1; \
	fi