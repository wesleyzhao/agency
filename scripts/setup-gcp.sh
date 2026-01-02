#!/bin/bash
# AgentCtl GCP Setup Script
# This script guides you through the minimal GCP setup required.

set -e

echo "========================================"
echo "  AgentCtl GCP Setup"
echo "========================================"
echo ""

# Check if credentials already exist
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "✓ Found credentials at: $GOOGLE_APPLICATION_CREDENTIALS"
    echo ""
    read -p "Use existing credentials? [Y/n] " use_existing
    if [ "$use_existing" != "n" ] && [ "$use_existing" != "N" ]; then
        echo "Using existing credentials."
        exec agentctl init "$@"
    fi
fi

echo "This script will guide you through GCP setup."
echo "You'll need to perform 3 steps in the GCP Console."
echo ""

# Step 1: Project
echo "----------------------------------------"
echo "STEP 1: Create or Select a GCP Project"
echo "----------------------------------------"
echo ""
echo "Open this URL in your browser:"
echo "  https://console.cloud.google.com/projectcreate"
echo ""
echo "Create a new project or note an existing project ID."
echo ""
read -p "Enter your GCP Project ID: " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Project ID is required"
    exit 1
fi

# Step 2: Billing
echo ""
echo "----------------------------------------"
echo "STEP 2: Enable Billing"
echo "----------------------------------------"
echo ""
echo "Open this URL to enable billing:"
echo "  https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
echo ""
read -p "Press Enter once billing is enabled..."

# Step 3: Service Account
echo ""
echo "----------------------------------------"
echo "STEP 3: Create Service Account"
echo "----------------------------------------"
echo ""
echo "Open this URL:"
echo "  https://console.cloud.google.com/iam-admin/serviceaccounts/create?project=$PROJECT_ID"
echo ""
echo "1. Service account name: agentctl-admin"
echo "2. Click 'Create and Continue'"
echo "3. Add these roles:"
echo "   - Compute Admin"
echo "   - Secret Manager Admin"
echo "   - Storage Admin"
echo "   - Service Usage Admin"
echo "4. Click 'Done'"
echo ""
echo "Then create a key:"
echo "  https://console.cloud.google.com/iam-admin/serviceaccounts?project=$PROJECT_ID"
echo ""
echo "1. Click on 'agentctl-admin' service account"
echo "2. Go to 'Keys' tab"
echo "3. Click 'Add Key' -> 'Create new key' -> 'JSON'"
echo "4. Save the file"
echo ""
read -p "Enter the path to your downloaded JSON key file: " KEY_FILE

# Expand ~ if used
KEY_FILE="${KEY_FILE/#\~/$HOME}"

if [ ! -f "$KEY_FILE" ]; then
    echo "Error: File not found: $KEY_FILE"
    exit 1
fi

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$KEY_FILE"

echo ""
echo "----------------------------------------"
echo "STEP 4: Initialize AgentCtl"
echo "----------------------------------------"
echo ""
echo "Running: agentctl init --project $PROJECT_ID"
echo ""

# Run init
agentctl init --project "$PROJECT_ID"

echo ""
echo "========================================"
echo "  Setup Complete!"
echo "========================================"
echo ""
echo "Add this to your shell profile (~/.bashrc or ~/.zshrc):"
echo ""
echo "  export GOOGLE_APPLICATION_CREDENTIALS=\"$KEY_FILE\""
echo ""
echo "Then you can run:"
echo "  agentctl run 'Your task here'"
echo ""
