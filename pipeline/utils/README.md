# Summary Quality Testing

This directory contains utilities to test and validate the quality of AI-generated article summaries for vector database suitability.

## 🔍 test_summary_quality.py

**Purpose**: Tests your local LLM's article summarization quality and evaluates if summaries are suitable for vector database creation.

### What It Tests

1. **Compression Ratio**: How well the summary condenses information (0.1-0.8 is ideal)
2. **Key Information Preservation**: Whether important dates, fees, documents, processes are retained
3. **Coherence Score**: How well-structured and logical the summary is
4. **Overall Quality**: Combined score determining vector database suitability

### Quality Metrics

- **Excellent (≥80% suitable)**: Ready for vector database
- **Good (≥60% suitable)**: Minor optimization needed
- **Moderate (≥40% suitable)**: Significant improvements needed
- **Poor (<40% suitable)**: Major changes required

### Usage

#### Option 1: Direct Python
```bash
cd /Users/neekrish/Documents/GitHub/MyAI/Visa
uv run python pipeline/utils/test_summary_quality.py
```

#### Option 2: Quick Test Script
```bash
./pipeline/scripts/test_summary_quality.sh
```

### Output

The test will show:
- Overall quality metrics
- Individual article results
- Sample comparison (original vs summary)
- Recommendation for vector database usage
- Detailed JSON report saved to `pipeline/logs/`

### Customization

Edit the script to:
- Test more/fewer articles: Change `num_articles` parameter
- Adjust quality thresholds: Modify `quality_thresholds` dictionary
- Test specific article types: Filter articles by category

### Troubleshooting

**Common Issues:**
1. **No articles found**: Ensure you have data in `data/redbus2us_organized/` or `data/redbus2us_raw/`
2. **LLM connection failed**: Check if Ollama is running (`ollama serve`)
3. **Import errors**: Verify you're running from project root directory

**Performance Tips:**
- Test with 3-5 articles initially
- Use lower temperature settings for more factual summaries
- Ensure adequate CPU/memory for local LLM processing

## Understanding Results

### Good Summary Characteristics
- **Structured format** with clear sections
- **Preserves key facts** (dates, fees, requirements)
- **Logical flow** with transition words
- **Appropriate length** (50-500 words)
- **High compression** without losing essential information

### Vector Database Benefits
High-quality summaries improve:
- Search relevance and accuracy
- Query response speed
- Storage efficiency
- User experience

### Next Steps

1. **Run the test** to baseline your current quality
2. **Analyze results** to identify improvement areas
3. **Optimize prompts** if quality is insufficient
4. **Re-test** after making changes
5. **Proceed with confidence** once quality is good (≥70%)