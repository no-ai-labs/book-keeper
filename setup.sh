#!/bin/bash

# Book Keeper Setup Script
echo "================================================"
echo "Book Keeper - PDF Contradiction Checker Setup"
echo "================================================"
echo ""

# Check if conda is installed
if ! command -v conda &> /dev/null
then
    echo "❌ Conda is not installed. Please install Anaconda or Miniconda first."
    echo "Visit: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create conda environment
echo "📦 Creating conda environment 'book-keeper'..."
conda env create -f environment.yml

echo ""
echo "✅ Conda environment created successfully!"
echo ""

# Provide activation instructions
echo "📋 Next steps:"
echo ""
echo "1. Activate the environment:"
echo "   conda activate book-keeper"
echo ""
echo "2. Copy .env_example to .env and add your OpenAI API key:"
echo "   cp .env_example .env"
echo "   # Then edit .env and add your OPENAI_API_KEY"
echo ""
echo "3. Start Qdrant vector database (requires Docker):"
echo "   Option 1 (Docker Compose - recommended):"
echo "   docker-compose up -d"
echo ""
echo "   Option 2 (Docker run):"
echo "   docker run -p 6345:6333 -p 6346:6334 -v $(pwd)/data/qdrant:/qdrant/storage:z qdrant/qdrant"
echo ""
echo "4. Run the PDF checker:"
echo "   python rag_pdf_checker.py"
echo ""
echo "================================================"
echo "Optional: For UI interface, after activation run:"
echo "   python ui_gradio.py  # or python ui_streamlit.py"
echo "================================================" 