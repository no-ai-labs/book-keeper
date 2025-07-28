# Book Keeper - PDF Quality Analyzer 📚🔍

**Book Keeper v2.0** - A comprehensive AI-powered quality assurance tool that analyzes PDF documents for contradictions, content flow, redundancy, code quality, and theoretical accuracy.

## ✨ Features

### Core Analysis Modules

1. **📚 Contradiction Detection**: Identifies logical contradictions between chapters
2. **📊 Flow Analysis**: Checks content progression and prerequisite violations  
3. **🔁 Redundancy Detection**: Finds duplicate or unnecessarily repeated content
4. **🐛 Code Validation**: Validates code snippets for syntax and best practices
5. **📖 Theory Verification**: Verifies against software engineering standards (SOLID, Design Patterns, etc.)

### Technical Features

- 📄 **Automatic PDF Chapter Extraction**: Supports various chapter delimiter patterns
- 🧠 **Vector Embeddings**: Semantic text analysis using OpenAI Embeddings API
- 🗄️ **Vector Database**: Efficient similarity search powered by Qdrant
- 🤖 **Dual LLM Support**: Choose between Claude 3.5 Sonnet (default) or GPT-4o
- 📊 **Comprehensive Reports**: JSON and Markdown formats with quality scores
- 🌍 **Multilingual Support**: Works with PDFs in multiple languages

## 📋 System Requirements

- Python 3.10+
- Conda (Anaconda or Miniconda)
- Docker (for running Qdrant)
- API Keys:
  - ANTHROPIC_API_KEY (for Claude 3.5 Sonnet - default)
  - OPENAI_API_KEY (for GPT-4o - optional)

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/no-ai-labs/book-keeper.git
cd book-keeper
```

### 2. Set up the environment
```bash
# Install Conda (if not already installed)
./install_conda.sh  # macOS only

# Create and activate the environment
./setup.sh
conda activate book-keeper
```

### 3. Configure environment variables
```bash
cp .env_example .env
# Edit .env and add your API keys:
# - ANTHROPIC_API_KEY (for Claude - default)
# - OPENAI_API_KEY (for GPT-4o - optional)
```

### 4. Start Qdrant
```bash
docker-compose up -d
```

### 5. Place PDF files
Put your PDF files in the `pdf/` directory.

## 📖 Usage

### Comprehensive Analysis (Default)
Runs all quality checks:

```bash
python rag_pdf_checker.py
```

### Specific Checks
Run only selected analyzers:

```bash
# Single check
python rag_pdf_checker.py --check contradiction

# Multiple checks
python rag_pdf_checker.py --check contradiction,flow,code

# Available checks: contradiction, flow, redundancy, code, theory
```

### Test Mode
Limited analysis for testing (first 3 chapters only):

```bash
# Test with default model (Claude)
python rag_pdf_checker.py --test

# Test with GPT-4o
python rag_pdf_checker.py --test --openai
```

### Model Selection
```bash
# Use Claude 3.5 Sonnet (default)
python rag_pdf_checker.py

# Use GPT-4o
python rag_pdf_checker.py --openai
# or
python rag_pdf_checker.py --gpt
```

### Custom PDF Directory
```bash
python rag_pdf_checker.py --pdf-dir /path/to/pdfs
```

## 📊 Output

The tool generates two report files:

### 1. `quality_report_v2.json`
Detailed JSON report with all findings and scores.

### 2. `quality_report_v2.md`
Beautiful Markdown report with:
- 🎯 Overall quality score (0-100%)
- 📈 Individual module scores
- 📋 Detailed findings by category
- 🔍 Key insights summary

### Quality Scoring

- **90-100%**: Excellent ✅
- **80-89%**: Good ⚠️
- **70-79%**: Fair ⚠️
- **60-69%**: Needs Improvement ❌
- **Below 60%**: Poor ❌

## 🗂️ Project Structure

```
book-keeper/
├── rag_pdf_checker.py      # Main v2.0 application
├── analyzers/              # Analysis modules
│   ├── base.py            # Base analyzer class
│   ├── contradiction.py   # Contradiction detector
│   ├── flow.py           # Content flow analyzer
│   ├── redundancy.py     # Redundancy detector
│   ├── code.py           # Code validator
│   └── theory.py         # Theory verifier
├── pdf/                   # PDF files directory
├── environment.yml        # Conda environment
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Qdrant setup
└── quality_report_v2.*    # Generated reports
```

## 🔧 Advanced Settings

### Environment Variables (.env)
```bash
# API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6345
QDRANT_API_KEY=optional_key
```

### Docker Compose Configuration
The `docker-compose.yml` configures Qdrant with:
- REST API on port 6345
- gRPC on port 6346
- Persistent storage in `./data/qdrant`
- Health checks
- Auto-restart

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Claude 4 Opus and Claude 3.5 Sonnet
- Powered by OpenAI Embeddings
- Vector search by Qdrant 