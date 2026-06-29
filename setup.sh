#!/bin/bash
# VENHO AI Studio — one-time setup
# Usage: bash setup.sh

echo "Installing dependencies for VENHO AI Studio..."
pip3 install openai anthropic python-dotenv
echo ""
echo "Done. Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Fill in OPENAI_API_KEY and ANTHROPIC_API_KEY in .env"
echo "  3. Drop images into assets/raw/<category>/"
echo "  4. python3 app/main.py --folder assets/raw/room --category Room"
