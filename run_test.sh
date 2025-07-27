#!/bin/bash

echo "================================================"
echo "Book Keeper - Test Mode"
echo "================================================"
echo ""
echo "This will only check the first 5 chapter pairs"
echo "to test the system without hitting rate limits."
echo ""

# Check if conda environment is activated
if [[ "$CONDA_DEFAULT_ENV" != "book-keeper" ]]; then
    echo "⚠️  Please activate the book-keeper environment first:"
    echo "   conda activate book-keeper"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "   Please copy .env_example to .env and add your API key"
    exit 1
fi

# Check if Qdrant is running
echo "🔍 Checking Qdrant connection..."
if ! curl -s http://localhost:6345/health > /dev/null; then
    echo "❌ Qdrant is not running!"
    echo "   Please start it with: docker-compose up -d"
    exit 1
fi
echo "✅ Qdrant is running"
echo ""

# Check for model argument
MODEL_ARG=""
if [ "$1" = "--openai" ] || [ "$1" = "--gpt" ]; then
    MODEL_ARG="--openai"
    echo "🤖 Using GPT-4o model"
else
    echo "🤖 Using Claude Sonnet 4 model (default)"
    echo "   (use './run_test.sh --openai' or '--gpt' for GPT-4o)"
fi
echo ""

# Run in test mode
echo "🚀 Starting PDF checker in TEST MODE..."
echo ""
python rag_pdf_checker.py --test $MODEL_ARG 