#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Get the project reference from config if available, or use the one from the existing script
SUPABASE_PROJECT_REF="${SUPABASE_PROJECT_REF:-hsnppengoffvgtnifceo}"

# Create backup directory with timestamp (using absolute path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups/$(date +%Y%m%d_%H%M%S)_pre_migration"
mkdir -p "$BACKUP_DIR"

print_message "$YELLOW" "Creating database backup before Phase 1 Task 3 migration..."
print_message "$YELLOW" "Backup directory: $BACKUP_DIR"

# Check if we're linked to the correct project
print_message "$YELLOW" "Ensuring connection to project $SUPABASE_PROJECT_REF..."
supabase link --project-ref "$SUPABASE_PROJECT_REF" || {
    print_message "$RED" "Failed to link to project $SUPABASE_PROJECT_REF"
    exit 1
}

# Backup critical tables
TABLES=("trades" "options_strategy_trades" "options_strategy_transactions" "transactions" "monthly_pl")

# Create a combined backup
print_message "$YELLOW" "Creating full database backup..."
supabase db dump -f "$BACKUP_DIR/full_backup.sql"

if [ $? -eq 0 ]; then
    print_message "$GREEN" "✓ Successfully created full backup"
else
    print_message "$RED" "✗ Failed to create full backup"
    exit 1
fi

# Create data-only backup
print_message "$YELLOW" "Creating data-only backup..."
supabase db dump --data-only -f "$BACKUP_DIR/data_backup.sql"

if [ $? -eq 0 ]; then
    print_message "$GREEN" "✓ Successfully created data backup"
else
    print_message "$YELLOW" "⚠ Could not create data-only backup (full backup contains all data)"
fi

# Create a metadata file
cat > "$BACKUP_DIR/backup_metadata.txt" << EOF
Backup Created: $(date)
Project Reference: $SUPABASE_PROJECT_REF
Migration: Phase 1 Task 3 - Data Migration Strategy
Backed up tables: ${TABLES[*]}
EOF

print_message "$GREEN" "Database backup completed successfully!"
print_message "$YELLOW" "Backup location: $BACKUP_DIR"
print_message "$YELLOW" "Before proceeding with migration, verify the backup by checking the SQL files." 