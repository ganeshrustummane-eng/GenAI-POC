#!/bin/bash
# install_and_test.sh - One-command setup and test

echo "================================================"
echo "Migration Validator - .env Setup & Test"
echo "================================================"
echo ""

echo "Step 1: Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Step 2: Testing database connections..."
python test_env_connections.py

echo ""
echo "Step 3: Running quick start demo..."
python quick_start.py

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Create YAML configs in config/bronze/"
echo "   Reference: CONFIG_EXAMPLES.md"
echo ""
echo "2. Run batch validation:"
echo "   python -m src.validation.validation_executor"
echo ""
echo "3. Check results:"
echo "   output/bronze/validation_<run_id>/"
echo ""
