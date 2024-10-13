# Makefile for Blue Deer Trading Discord Bot

# Variables
PYTHON := python
UVICORN := uvicorn
APP := app.main:app
PORT := 8000
TEST_CMD := pytest
REQUIREMENTS := app/requirements.txt

# Phony targets
.PHONY: run run_local test init_db clean update_trade_metrics install_deps migrate

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
	@echo "  db-upgrade  - Upgrade the database"
	@echo "  prod-db-upgrade - Upgrade the production database"
	@echo "  db-upgrade-plan - Show the migration plan without executing"
	@echo "  db-check    - Check if the database is up to date"
	@echo "  update_trade_metrics - Update trade metrics in the database"
	@echo "  install_deps - Install required dependencies"
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

# Define the path to the script (use quotes to handle spaces in path)
MIGRATION_SCRIPT := "$(CURDIR)/alembic/run_specific_migration.py"

# Run a specific migration, handling errors
db-upgrade-specific:
	@read -p "Enter the revision ID: " rev_id; \
	python "$(MIGRATION_SCRIPT)" "$$rev_id"

# Run a specific migration in production
prod-db-upgrade-specific:
	@read -p "Enter the revision ID: " rev_id; \
	echo "Are you sure you want to run migration $$rev_id on the production database? (y/n)"; \
	read answer; \
	if [ "$$answer" = "y" ]; then \
		echo "Running migration $$rev_id..."; \
		alembic upgrade $$rev_id; \
	else \
		echo "Migration cancelled."; \
	fi

# List all revisions with dates
db-revisions:
	@alembic history --verbose

# Stamp the database with the current head revision
db-stamp-head:
	alembic stamp head

# New target to run the update trade metrics script
update_trade_metrics: install_deps
	@echo "Updating trade metrics..."
	cd backend && $(PYTHON) ../scripts/update_trade_metrics.py

# Install dependencies
install_deps:
	@echo "Installing dependencies..."
	cd backend && pip install -r $(REQUIREMENTS)

# Run the migration script
migrate:
	python manage_migrations.py

# Development database upgrade
dev-db-upgrade:
	@echo "Upgrading development database..."
	alembic -x environment=development upgrade head

# Production database upgrade (with confirmation)
prod-db-upgrade:
	@echo "Are you sure you want to upgrade the production database? (y/n)"
	@read answer; \
	if [ "$$answer" = "y" ]; then \
		echo "Upgrading production database..."; \
		alembic -x environment=production upgrade head; \
	else \
		echo "Production database upgrade cancelled."; \
	fi

# Development database check
dev-db-check:
	@if alembic -x environment=development current | grep -q "(head)"; then \
		echo "Development database is up to date."; \
		exit 0; \
	else \
		echo "Development database needs to be upgraded."; \
		exit 1; \
	fi

# Production database check
prod-db-check:
	@if alembic -x environment=production current | grep -q "(head)"; then \
		echo "Production database is up to date."; \
		exit 0; \
	else \
		echo "Production database needs to be upgraded."; \
		exit 1; \
	fi

# Development migration
dev-migrate:
	python scripts/manage_migrations.py development

# Production migration
prod-migrate:
	@echo "Are you sure you want to run migrations on the production database? (y/n)"
	@read answer; \
	if [ "$$answer" = "y" ]; then \
		python scripts/manage_migrations.py production; \
	else \
		echo "Production migration cancelled."; \
	fi

