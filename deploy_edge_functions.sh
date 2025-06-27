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

# Check if Supabase CLI is installed
if ! command -v supabase &> /dev/null; then
    print_message "$RED" "Supabase CLI is not installed. Installing now..."
    brew install supabase/tap/supabase
fi

# Check if we're in the frontend directory
if [[ ! -d "supabase/functions" ]]; then
    print_message "$RED" "Error: Must be run from the frontend directory containing supabase/functions"
    exit 1
fi

# Deploy each function
print_message "$YELLOW" "Deploying edge functions..."

# Get only directories from supabase/functions, excluding _shared
functions=()
while IFS= read -r dir; do
    # Skip _shared directory and any files
    if [[ -d "$dir" && $(basename "$dir") != "_shared" ]]; then
        functions+=($(basename "$dir"))
    fi
done < <(find supabase/functions -maxdepth 1 -mindepth 1)

print_message "$YELLOW" "Found functions to deploy: ${functions[*]}"

for func in "${functions[@]}"; do
    print_message "$YELLOW" "Deploying $func function..."
    supabase functions deploy "$func" --project-ref "$SUPABASE_PROJECT_REF"
    
    if [ $? -eq 0 ]; then
        print_message "$GREEN" "✓ Successfully deployed $func"
    else
        print_message "$RED" "✗ Failed to deploy $func"
        exit 1
    fi
done

print_message "$GREEN" "All functions deployed successfully!" 