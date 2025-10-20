#!/bin/bash
"""
Quick Summary Quality Test Runner
"""

echo "🔍 Article Summary Quality Tester"
echo "=================================="
echo ""
echo "This script will test your local LLM's article summarization quality"
echo "and determine if it's suitable for vector database creation."
echo ""

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Check if UV is available
if command -v uv &> /dev/null; then
    echo "🚀 Running summary quality tests with UV..."
    uv run python pipeline/utils/test_summary_quality.py
else
    echo "🚀 Running summary quality tests with Python..."
    python3 pipeline/utils/test_summary_quality.py
fi

echo ""
echo "✅ Test completed! Check the output above for results."
echo ""
echo "📊 Key things to look for:"
echo "   • Overall Quality Score (should be > 0.7)"
echo "   • Vector DB Suitable percentage (should be > 80%)"  
echo "   • Compression ratio (0.1-0.8 is good)"
echo "   • Key info preservation (> 0.7 is good)"
echo ""
echo "💡 If results are poor, consider:"
echo "   • Adjusting LLM temperature (lower for more factual)"
echo "   • Improving summarization prompts"
echo "   • Using a different/better local model"