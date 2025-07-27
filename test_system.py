#!/usr/bin/env python3
"""
Test script for the Book Keeper PDF Contradiction Detector
This script tests the system without needing actual PDF files
"""

import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    missing_deps = []
    
    # Check required packages
    try:
        import pdfplumber
        print("✅ pdfplumber")
    except ImportError:
        missing_deps.append("pdfplumber")
        print("❌ pdfplumber")
    
    try:
        import qdrant_client
        print("✅ qdrant_client")
    except ImportError:
        missing_deps.append("qdrant_client")
        print("❌ qdrant_client")
    
    try:
        import openai
        print("✅ openai")
    except ImportError:
        missing_deps.append("openai")
        print("❌ openai")
    
    try:
        import tqdm
        print("✅ tqdm")
    except ImportError:
        missing_deps.append("tqdm")
        print("❌ tqdm")
    
    try:
        import colorama
        print("✅ colorama")
    except ImportError:
        missing_deps.append("colorama")
        print("❌ colorama")
    
    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv")
    except ImportError:
        missing_deps.append("python-dotenv")
        print("❌ python-dotenv")
    
    if missing_deps:
        print(f"\n❌ Missing dependencies: {', '.join(missing_deps)}")
        print("Please activate the conda environment: conda activate book-keeper")
        return False
    
    print("\n✅ All dependencies installed!")
    return True


def check_environment():
    """Check environment variables"""
    print("\n🔍 Checking environment variables...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found")
        print("Please copy .env_example to .env and add your OpenAI API key")
        return False
    else:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key.startswith("sk-") and len(api_key) > 20:
            print("✅ OPENAI_API_KEY found and appears valid")
        else:
            print("⚠️  OPENAI_API_KEY found but may be invalid")
    
    return True


def check_pdf_files():
    """Check if PDF files exist in the pdf folder"""
    print("\n🔍 Checking PDF files...")
    
    pdf_folder = Path("pdf")
    if not pdf_folder.exists():
        print("❌ 'pdf' folder not found")
        return False
    
    pdf_files = list(pdf_folder.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in 'pdf' folder")
        return False
    
    print(f"✅ Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files[:5]:  # Show first 5
        print(f"   - {pdf.name}")
    
    if len(pdf_files) > 5:
        print(f"   ... and {len(pdf_files) - 5} more")
    
    return True


def test_qdrant_connection():
    """Test Qdrant connection"""
    print("\n🔍 Testing Qdrant connection...")
    
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            host=os.getenv("QDRANT_HOST", "localhost"),
            port=int(os.getenv("QDRANT_PORT", 6345))
        )
        # Try to get collections
        collections = client.get_collections()
        print("✅ Qdrant connection successful!")
        return True
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        print("Please ensure Qdrant is running:")
        print("docker-compose up -d")
        return False


def test_openai_connection():
    """Test OpenAI API connection"""
    print("\n🔍 Testing OpenAI API connection...")
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # Try a simple completion
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'test ok'"}],
            max_tokens=10
        )
        print("✅ OpenAI API connection successful!")
        return True
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        return False


def test_anthropic_connection():
    """Test Anthropic API connection"""
    print("\n🔍 Testing Anthropic (Claude) API connection...")
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY not found (optional)")
        return True  # Not a failure if not configured
    
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Try a simple completion
        response = client.messages.create(
            model="claude-3-haiku-20240307",  # Use cheaper model for testing
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'test ok'"}]
        )
        print("✅ Anthropic API connection successful!")
        return True
    except Exception as e:
        print(f"❌ Anthropic API connection failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("Book Keeper System Test")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run tests
    if not check_dependencies():
        all_tests_passed = False
    
    if not check_environment():
        all_tests_passed = False
    
    if not check_pdf_files():
        all_tests_passed = False
    
    # Only test connections if environment is set up
    if os.getenv("OPENAI_API_KEY"):
        if not test_openai_connection():
            all_tests_passed = False
    
    if not test_anthropic_connection():
        all_tests_passed = False
        
    if not test_qdrant_connection():
        print("⚠️  Qdrant not running, but system can still work for testing")
    
    # Summary
    print("\n" + "=" * 60)
    if all_tests_passed:
        print("✅ All tests passed! System is ready to use.")
        print("\nRun the main script with: python rag_pdf_checker.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    print("=" * 60)


if __name__ == "__main__":
    main() 