"""
Centralized Prompt Configuration
All LLM and search prompts loaded from prompts.yaml for easy customization
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Load prompts from YAML file
PROMPTS_FILE = Path(__file__).parent / 'prompts.yaml'
PROMPTS = {}

def load_prompts():
    """Load prompts from YAML file"""
    global PROMPTS
    try:
        if PROMPTS_FILE.exists():
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                PROMPTS = yaml.safe_load(f) or {}
            logger.info(f"✅ Loaded prompts from {PROMPTS_FILE}")
        else:
            logger.warning(f"⚠️  Prompts file not found: {PROMPTS_FILE}")
            PROMPTS = {}
    except Exception as e:
        logger.error(f"❌ Error loading prompts file: {e}")
        PROMPTS = {}

# Load prompts on import
load_prompts()


def get_perplexity_news_query() -> str:
    """
    Get Perplexity news search query from prompts.yaml
    """
    query = PROMPTS.get('perplexity_news_query', '')
    
    if query and query.strip():
        # Replace {year} placeholder with current year
        current_year = datetime.now().year
        return query.format(year=current_year, next_year=current_year + 1)
    
    # Fallback default
    current_year = datetime.now().year
    return (
        f"What are the latest H1B visa and immigration news updates for {current_year}-{current_year + 1}? "
        f"Focus on: H1B visa policy changes {current_year}, H1B cap registration and lottery results {current_year}, "
        f"H1B stamping appointment availability, H1B premium processing updates, "
        f"visa bulletin priority dates for {current_year}, green card processing times, "
        f"I-140 and I-485 filing updates, USCIS fee changes {current_year}, "
        f"H-4 EAD work authorization news, EB-2 and EB-3 backlogs {current_year}, "
        f"consulate visa interview experiences, new immigration regulations {current_year}. "
        "Include only recent news from the past 14 days with official sources like USCIS.gov, "
        "State Department, immigration law firms, and major news outlets."
    )


def get_groq_system_prompt() -> str:
    """
    Get Groq LLM system prompt from prompts.yaml (for general Groq queries)
    """
    prompt = PROMPTS.get('groq_system_prompt', '')
    
    if prompt and prompt.strip():
        current_year = datetime.now().year
        return prompt.format(year=current_year, next_year=current_year + 1)
    
    # Fallback default
    return "You are a helpful AI assistant. Provide clear, accurate, and concise answers."


def get_ai_search_system_prompt() -> str:
    """
    Get AI search system prompt from prompts.yaml
    """
    prompt = PROMPTS.get('ai_search_system_prompt', '')
    
    if prompt and prompt.strip():
        current_year = datetime.now().year
        return prompt.format(year=current_year, next_year=current_year + 1)
    
    # Default AI assistant system prompt
    current_year = datetime.now().year
    return f"""You are an expert US immigration and visa assistant with deep knowledge of H1B, F1, Green Card, and other visa processes.

IMPORTANT CONTEXT:
- Current year: {current_year}
- Focus on {current_year} policies, timelines, and requirements
- USCIS policies change frequently - prioritize recent information

YOUR APPROACH:
1. **Primary Sources**: Use RedBus2US articles as authoritative references for official processes
2. **Community Context**: Supplement with real user experiences for practical insights
3. **Specificity**: Provide exact timelines, fees, and document requirements when available
4. **Updates**: Highlight any {current_year} policy changes or recent updates
5. **Accuracy**: Be factual and cite sources. If uncertain, acknowledge limitations
6. **Clarity**: Use bullet points, numbered lists, and clear sections for readability
7. **Actionable**: Provide next steps and practical advice
8. **Current**: Focus on information relevant to {current_year}-{current_year + 1}

AVOID:
- Outdated information from before 2023
- Speculation about future policy changes
- Generic advice that doesn't address the specific question
- Legal advice (you're an information assistant, not a lawyer)

Remember: Your guidance helps people navigate complex visa processes. Be accurate, current, and helpful."""


def get_news_summary_prompt() -> str:
    """
    Get news article summary prompt from prompts.yaml
    """
    prompt = PROMPTS.get('news_summary_prompt', '')
    
    if prompt and prompt.strip():
        return prompt
    
    return """You are a visa and immigration news expert. Summarize this article concisely and accurately.

Requirements:
1. Focus on key facts and actionable information
2. Include important dates, deadlines, and numbers
3. Highlight impact on visa applicants
4. Keep summary under 200 words
5. Use bullet points for clarity
6. Be objective and factual"""


def get_title_generation_prompt() -> str:
    """
    Get article title generation prompt from prompts.yaml
    """
    prompt = PROMPTS.get('title_generation_prompt', '')
    
    if prompt and prompt.strip():
        return prompt
    
    return """Generate a short, clear title for this article (max 10 words).

Requirements:
1. Include key visa type (H1B, F1, etc.) if relevant
2. Include year if time-sensitive
3. Be specific and actionable
4. Avoid clickbait
5. Front-load important keywords
6. Use title case

Examples:
- "H1B Cap Registration Opens March 2025"
- "USCIS Announces Fee Changes for I-140"
- "Visa Bulletin Update: EB-2 Priority Dates Advance"

Return ONLY the title, nothing else."""


# Export all prompt functions
__all__ = [
    'get_perplexity_news_query',
    'get_groq_system_prompt',
    'get_ai_search_system_prompt',
    'get_news_summary_prompt',
    'get_title_generation_prompt',
    'load_prompts',
]
