# Customizable Prompts System

All Groq and Perplexity search prompts are now centralized in an easy-to-edit YAML file.

## 📍 Location

**Prompts File**: `backend/config/prompts.yaml` ← **Edit this file!**
**Loader Code**: `backend/config/prompts.py`

## 🎯 Available Prompts

### 1. **Perplexity News Search Query**
- **YAML Key**: `perplexity_news_query`
- **Used By**: News fetching service
- **Purpose**: Searches Perplexity API for H1B and immigration news
- **Placeholders**: `{year}`, `{next_year}` auto-replaced with current year
- **Default**: Comprehensive query covering H1B, green cards, USCIS updates, visa bulletins, etc.

### 2. **Groq System Prompt**
- **YAML Key**: `groq_system_prompt`
- **Used By**: General Groq LLM queries
- **Purpose**: Base system prompt for Groq LLM interactions
- **Placeholders**: `{year}`, `{next_year}` auto-replaced with current year
- **Default**: Helpful AI assistant specialized in immigration

### 3. **AI Search System Prompt**
- **YAML Key**: `ai_search_system_prompt`
- **Used By**: Chat-based visa assistant (Enhanced Chat Synthesizer)
- **Purpose**: Instructs the LLM on how to answer visa-related questions
- **Placeholders**: `{year}`, `{next_year}` auto-replaced with current year
- **Default**: Expert immigration assistant focused on accuracy and current year policies

### 4. **News Summary Prompt**
- **YAML Key**: `news_summary_prompt`
- **Used By**: News article processing (Groq LLM)
- **Purpose**: Generates concise bullet-point summaries of news articles
- **Default**: 3-5 bullet points focusing on key facts and actionable information

### 5. **Title Generation Prompt**
- **YAML Key**: `title_generation_prompt`
- **Used By**: News article processing (Groq LLM)
- **Purpose**: Creates short, punchy titles for news articles
- **Default**: Clear titles (max 10 words) with visa type and key action

## 🔧 How to Customize

### Simple: Edit the YAML File

1. **Edit the prompts file**:
   ```bash
   vim backend/config/prompts.yaml
   # or
   nano backend/config/prompts.yaml
   ```

2. **Modify any prompt** - they're clearly labeled:
   ```yaml
   perplexity_news_query: |
     Your custom Perplexity search query here.
     Use {year} for current year.
   
   groq_system_prompt: |
     Your custom Groq system prompt here.
   
   ai_search_system_prompt: |
     Your custom AI assistant prompt here.
   ```

3. **Redeploy**:
   ```bash
   fly deploy --remote-only -a usvisachat
   ```

### Tips:
- Use `{year}` placeholder for current year (auto-replaced with 2025)
- Use `{next_year}` for next year (auto-replaced with 2026)
- Multi-line strings use the `|` symbol in YAML
- All prompts have clear comments and examples

## 📊 Current Default Prompts

### Perplexity News Query (as of 2025)
```
What are the latest H1B visa and immigration news updates for 2025-2026? 
Focus on: H1B visa policy changes 2025, H1B cap registration and lottery results 2025, 
H1B stamping appointment availability, H1B premium processing updates, 
visa bulletin priority dates for 2025, green card processing times, 
I-140 and I-485 filing updates, USCIS fee changes 2025, 
H-4 EAD work authorization news, EB-2 and EB-3 backlogs 2025, 
consulate visa interview experiences, new immigration regulations 2025. 
Include only recent news from the past 14 days with official sources like USCIS.gov, 
State Department, immigration law firms, and major news outlets.
```

### AI Search System Prompt
```
You are an expert US immigration and visa assistant with deep knowledge of H1B, F1, Green Card, and other visa processes.

IMPORTANT CONTEXT:
- Current year: 2025
- Focus on 2025 policies, timelines, and requirements
- USCIS policies change frequently - prioritize recent information

YOUR APPROACH:
1. **Primary Sources**: Use RedBus2US articles as authoritative references for official processes
2. **Community Context**: Supplement with real user experiences for practical insights
3. **Specificity**: Provide exact timelines, fees, and document requirements when available
4. **Updates**: Highlight any 2025 policy changes or recent updates
5. **Accuracy**: Be factual and cite sources. If uncertain, acknowledge limitations
6. **Clarity**: Use bullet points, numbered lists, and clear sections for readability
7. **Actionable**: Provide next steps and practical advice
8. **Current**: Focus on information relevant to 2025-2026

AVOID:
- Outdated information from before 2023
- Speculation about future policy changes
- Generic advice that doesn't address the specific question
- Legal advice (you're an information assistant, not a lawyer)

Remember: Your guidance helps people navigate complex visa processes. Be accurate, current, and helpful.
```

## 🧪 Testing Custom Prompts

1. **Test Perplexity Query**: Fetch news manually
   ```bash
   curl https://usvisachat.fly.dev/news/refresh
   ```

2. **Test AI Search**: Ask a visa question in the app

3. **View Logs**: Check Fly.io logs to see which prompts are being used
   ```bash
   fly logs -a usvisachat
   ```

## 💡 Best Practices

### For Perplexity Queries:
- ✅ Be specific about time ranges (e.g., "past 14 days")
- ✅ Include specific visa types (H1B, F1, Green Card)
- ✅ Mention authoritative sources (USCIS.gov, State Department)
- ✅ Include the current year
- ❌ Avoid overly broad queries
- ❌ Don't specify too many sources (limits results)

### For AI Search Prompts:
- ✅ Emphasize accuracy and source citation
- ✅ Specify the output format (bullets, sections, etc.)
- ✅ Include current year context
- ✅ Mention limitations (not legal advice)
- ❌ Avoid being too restrictive
- ❌ Don't make prompts too long (affects token usage)

### For Summary Prompts:
- ✅ Specify desired length (word/character count)
- ✅ Request bullet points for clarity
- ✅ Focus on actionable information
- ❌ Avoid asking for too much detail
- ❌ Don't request subjective opinions

### For Title Prompts:
- ✅ Specify character/word limits
- ✅ Request inclusion of key elements (visa type, year)
- ✅ Emphasize clarity over creativity
- ❌ Avoid clickbait-style requests
- ❌ Don't ask for overly long titles

## 🔄 Resetting to Defaults

To reset a prompt to its default value, remove the environment variable:

```bash
# Remove custom prompt (Fly.io)
fly secrets unset PERPLEXITY_NEWS_QUERY -a usvisachat

# Remove from .env file
# Just delete or comment out the line
```

## 📈 Monitoring Prompt Performance

1. **Check logs** for prompt usage:
   ```bash
   fly logs -a usvisachat | grep "prompt"
   ```

2. **Monitor news quality** in the AI News section

3. **Test AI responses** with various questions

4. **Review article titles** for clarity and accuracy

## 🆘 Troubleshooting

**Prompt not being used?**
- Verify environment variable is set correctly
- Check for typos in variable name
- Restart the application after setting
- View logs to confirm prompt loading

**Poor results with custom prompt?**
- Try the default prompt first
- Gradually modify from the default
- Check prompt length (very long prompts can cause issues)
- Ensure proper formatting (no extra quotes or escapes)

## 📚 Related Files

- **Prompt definitions**: `backend/config/prompts.py`
- **News service**: `backend/services/news/news_service.py`
- **News utils**: `backend/services/news/news_utils.py`
- **Chat synthesizer**: `backend/services/enhanced_chat_synthesizer.py`
- **Environment examples**: `.env.example`

---

**Last Updated**: 2025-01-27
**Version**: 2.0.0
