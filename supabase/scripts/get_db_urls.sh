#!/bin/bash

# Helper script to guide you through getting database connection URLs

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_message "$BLUE" "=== How to Get Your Database Connection URLs ==="
echo ""

print_message "$YELLOW" "📝 Step 1: Get Production Database URL"
print_message "$GREEN" "1. Go to https://supabase.com/dashboard"
print_message "$GREEN" "2. Select your PRODUCTION project (hsnppengoffvgtnifceo)"
print_message "$GREEN" "3. Go to Settings → Database"
print_message "$GREEN" "4. Under 'Connection string', copy the 'URI' format"
print_message "$GREEN" "5. It looks like: postgresql://postgres:[password]@[host]:[port]/postgres"
echo ""

print_message "$YELLOW" "📝 Step 2: Get Preview Database URL"
print_message "$GREEN" "1. Go back to https://supabase.com/dashboard"
print_message "$GREEN" "2. Select your PREVIEW project (wrdcvjcglejufqhumitd)"
print_message "$GREEN" "3. Go to Settings → Database"
print_message "$GREEN" "4. Under 'Connection string', copy the 'URI' format"
echo ""

print_message "$YELLOW" "📝 Step 3: Set Environment Variables"
print_message "$GREEN" "Run these commands with your actual URLs:"
echo ""
print_message "$BLUE" "export PROD_DB_URL='postgresql://postgres:[YOUR_PROD_PASSWORD]@[PROD_HOST]:[PORT]/postgres'"
print_message "$BLUE" "export PREVIEW_DB_URL='postgresql://postgres:[YOUR_PREVIEW_PASSWORD]@[PREVIEW_HOST]:[PORT]/postgres'"
echo ""

print_message "$YELLOW" "📝 Step 4: Run the Data Copy Script"
print_message "$GREEN" "cd temp_prod_data && python3 manual_extract.py"
echo ""

print_message "$YELLOW" "💡 Tips:"
print_message "$GREEN" "• Make sure to replace [YOUR_PROD_PASSWORD] and [YOUR_PREVIEW_PASSWORD] with actual passwords"
print_message "$GREEN" "• The connection strings are on the same page as your database settings"
print_message "$GREEN" "• You can test the connection by pinging the host first"
echo ""

print_message "$YELLOW" "🔍 Example of what the URLs should look like:"
print_message "$BLUE" "postgresql://postgres:your_password@db.abcdefghijk.supabase.co:5432/postgres"
echo ""

print_message "$YELLOW" "Once you have both URLs set, run:"
print_message "$GREEN" "./scripts/copy_prod_test_data_v2.sh"
echo "" 