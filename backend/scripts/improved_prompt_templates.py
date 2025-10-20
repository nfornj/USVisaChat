"""
Improved Prompt Engineering Templates for Visa-Related Queries
Based on validation results showing low accuracy (0.139/1.0) and content analysis
"""

from typing import Dict, List, Optional
import re
from datetime import datetime


class ImprovedPromptTemplates:
    """Advanced prompt engineering for visa-related queries."""
    
    def __init__(self):
        # Query type detection patterns
        self.query_patterns = {
            'fees': [
                r'\b(fee|cost|price|payment|money|dollar|\$)\b',
                r'\b(premium processing|registration|petition)\b.*\b(fee|cost)\b',
                r'\bhow much\b'
            ],
            'dates': [
                r'\b(when|date|deadline|timeline|schedule)\b',
                r'\b(lottery|registration|filing|deadline)\b',
                r'\b(2025|2026|2027)\b'
            ],
            'documents': [
                r'\b(document|requirement|certificate|transcript|paperwork)\b',
                r'\bwhat.*need\b',
                r'\b(checklist|list)\b'
            ],
            'process': [
                r'\b(how|process|step|procedure|apply)\b',
                r'\b(lottery|petition|approval)\b.*\b(work|process)\b'
            ],
            'policy': [
                r'\b(rule|policy|change|update|new)\b',
                r'\b(trump|biden|uscis|administration)\b',
                r'\b(modernization|reform)\b'
            ],
            'experience': [
                r'\b(experience|interview|stamping|consulate)\b',
                r'\b(questions|preparation|tips)\b'
            ]
        }
    
    def detect_query_type(self, query: str) -> List[str]:
        """Detect the type(s) of query based on patterns."""
        query_lower = query.lower()
        detected_types = []
        
        for query_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_types.append(query_type)
                    break
        
        return detected_types or ['general']
    
    def extract_context_metadata(self, search_results: List) -> Dict:
        """Extract key metadata from search results for better prompting."""
        metadata = {
            'titles': [],
            'dates': [],
            'fees': [],
            'numbers': [],
            'sources': set(),
            'visa_types': set(),
            'categories': set(),
            'total_content_length': 0
        }
        
        for result in search_results:
            payload = result.payload
            
            # Basic metadata
            metadata['titles'].append(payload.get('title', 'Unknown'))
            metadata['sources'].add(payload.get('source', 'Unknown'))
            metadata['total_content_length'] += len(payload.get('full_text', ''))
            
            # Extract from metadata if available
            visa_types = payload.get('visa_types', [])
            categories = payload.get('categories', [])
            if isinstance(visa_types, list):
                metadata['visa_types'].update(visa_types)
            if isinstance(categories, list):
                metadata['categories'].update(categories)
            
            # Extract facts from content
            content = payload.get('full_text', '')
            
            # Extract dates
            date_patterns = [
                r'(?:March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}',
                r'\d{1,2}/\d{1,2}/\d{4}',
                r'FY\s*20\d{2}',
                r'October\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20\d{2}'
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, content, re.IGNORECASE)
                metadata['dates'].extend(dates[:3])  # Limit per article
            
            # Extract fees
            fee_patterns = [
                r'\$[\d,]+(?:\.\d{2})?',
                r'USD?\s*[\d,]+',
            ]
            
            for pattern in fee_patterns:
                fees = re.findall(pattern, content, re.IGNORECASE)
                metadata['fees'].extend(fees[:3])
            
            # Extract important numbers
            number_patterns = [
                r'(\d{1,3},\d{3})\s*(?:visas?|applications?|registrations?)',
                r'cap.*?(\d{1,3},\d{3})',
                r'quota.*?(\d{1,3},\d{3})'
            ]
            
            for pattern in number_patterns:
                numbers = re.findall(pattern, content, re.IGNORECASE)
                metadata['numbers'].extend(numbers[:2])
        
        # Deduplicate and limit
        metadata['dates'] = list(set(metadata['dates']))[:10]
        metadata['fees'] = list(set(metadata['fees']))[:10]
        metadata['numbers'] = list(set(metadata['numbers']))[:10]
        
        return metadata
    
    def create_enhanced_prompt(self, query: str, search_results: List, query_types: List[str] = None) -> str:
        """Create an enhanced prompt based on query type and content analysis."""
        
        if not query_types:
            query_types = self.detect_query_type(query)
        
        metadata = self.extract_context_metadata(search_results)
        
        # Build context sections
        context_sections = []
        
        for i, result in enumerate(search_results, 1):
            payload = result.payload
            title = payload.get('title', f'Article {i}')
            content = payload.get('full_text', payload.get('text_preview', ''))[:1000]  # More content
            score = result.score
            
            context_sections.append(f"""ARTICLE {i} (Relevance: {score:.3f}):
Title: {title}
Content: {content}
""")
        
        context = "\n".join(context_sections)
        
        # Base prompt with improvements
        base_prompt = f"""You are an expert visa consultant providing accurate information based solely on the provided articles. 

CONTEXT FROM OFFICIAL VISA ARTICLES:
{context}

EXTRACTED KEY INFORMATION:
- Available Dates: {', '.join(metadata['dates'][:5]) if metadata['dates'] else 'None mentioned'}
- Available Fees: {', '.join(metadata['fees'][:5]) if metadata['fees'] else 'None mentioned'}
- Important Numbers: {', '.join(metadata['numbers'][:3]) if metadata['numbers'] else 'None mentioned'}
- Visa Types Covered: {', '.join(metadata['visa_types']) if metadata['visa_types'] else 'General'}
- Categories: {', '.join(metadata['categories']) if metadata['categories'] else 'General'}

USER QUESTION: {query}

INSTRUCTIONS:
1. Answer ONLY based on the provided articles above
2. Use specific facts, dates, and numbers from the articles
3. If information is not in the articles, clearly state "This information is not available in the provided articles"
4. Be specific and detailed when information is available
5. Always cite which article number you're referencing
6. Do not make assumptions or add information not in the articles
7. If multiple articles have conflicting information, mention both versions"""
        
        # Add query-specific instructions
        if 'fees' in query_types:
            base_prompt += """
8. For fee questions: Provide exact amounts, fee types, and any conditions mentioned
9. Specify if fees are for registration, petition, premium processing, or other services"""
        
        if 'dates' in query_types:
            base_prompt += """
8. For date questions: Provide specific dates, deadlines, and timelines mentioned
9. Clarify which fiscal year or calendar year the dates refer to"""
        
        if 'documents' in query_types:
            base_prompt += """
8. For document questions: List all specific documents mentioned
9. Distinguish between registration documents and petition documents"""
        
        if 'process' in query_types:
            base_prompt += """
8. For process questions: Explain step-by-step procedures mentioned
9. Include any prerequisites or requirements for each step"""
        
        base_prompt += "\n\nANSWER:"
        
        return base_prompt
    
    def create_fee_specific_prompt(self, query: str, search_results: List) -> str:
        """Create a specialized prompt for fee-related queries."""
        
        metadata = self.extract_context_metadata(search_results)
        
        # Extract all fee information more thoroughly
        fee_details = []
        for i, result in enumerate(search_results, 1):
            content = result.payload.get('full_text', '')
            title = result.payload.get('title', f'Article {i}')
            
            # Look for fee contexts
            fee_contexts = []
            sentences = content.split('.')
            for sentence in sentences:
                if any(fee_word in sentence.lower() for fee_word in ['fee', 'cost', '$', 'usd', 'payment']):
                    fee_contexts.append(sentence.strip())
            
            if fee_contexts:
                fee_details.append(f"Article {i} ({title}): {' '.join(fee_contexts[:3])}")
        
        fee_context = "\n\n".join(fee_details)
        
        return f"""You are a visa fee specialist. Answer the fee question using ONLY the official information provided.

DETAILED FEE INFORMATION FROM ARTICLES:
{fee_context}

EXTRACTED FEE AMOUNTS: {', '.join(metadata['fees']) if metadata['fees'] else 'No specific amounts found'}

USER QUESTION: {query}

INSTRUCTIONS:
- Provide ALL fee amounts mentioned in the articles
- Specify what each fee is for (registration, petition, premium processing, etc.)
- Include any conditions or variations mentioned
- If fee information is not available, clearly state this
- Do not assume or estimate any fee amounts
- Reference which article contains each fee information

DETAILED FEE ANSWER:"""
    
    def create_date_specific_prompt(self, query: str, search_results: List) -> str:
        """Create a specialized prompt for date/timeline queries."""
        
        metadata = self.extract_context_metadata(search_results)
        
        # Extract timeline information
        timeline_details = []
        for i, result in enumerate(search_results, 1):
            content = result.payload.get('full_text', '')
            title = result.payload.get('title', f'Article {i}')
            
            # Look for date contexts
            date_contexts = []
            sentences = content.split('.')
            for sentence in sentences:
                if any(date_word in sentence.lower() for date_word in ['march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', '2025', '2026', 'deadline', 'timeline']):
                    date_contexts.append(sentence.strip())
            
            if date_contexts:
                timeline_details.append(f"Article {i} ({title}): {' '.join(date_contexts[:3])}")
        
        timeline_context = "\n\n".join(timeline_details)
        
        return f"""You are a visa timeline specialist. Answer the date/timeline question using ONLY the official information provided.

DETAILED TIMELINE INFORMATION FROM ARTICLES:
{timeline_context}

EXTRACTED DATES: {', '.join(metadata['dates']) if metadata['dates'] else 'No specific dates found'}

USER QUESTION: {query}

INSTRUCTIONS:
- Provide ALL relevant dates mentioned in the articles
- Specify what each date represents (registration deadline, lottery date, filing period, etc.)
- Include fiscal year vs calendar year clarifications
- Mention any date changes or updates
- If date information is not available, clearly state this
- Do not assume or estimate any dates
- Reference which article contains each date information

DETAILED TIMELINE ANSWER:"""
    
    def create_document_specific_prompt(self, query: str, search_results: List) -> str:
        """Create a specialized prompt for document requirement queries."""
        
        # Extract document information
        doc_details = []
        for i, result in enumerate(search_results, 1):
            content = result.payload.get('full_text', '')
            title = result.payload.get('title', f'Article {i}')
            
            # Look for document contexts
            doc_contexts = []
            sentences = content.split('.')
            for sentence in sentences:
                if any(doc_word in sentence.lower() for doc_word in ['document', 'certificate', 'transcript', 'passport', 'i-20', 'w2', 'resume', 'requirement']):
                    doc_contexts.append(sentence.strip())
            
            if doc_contexts:
                doc_details.append(f"Article {i} ({title}): {' '.join(doc_contexts[:3])}")
        
        doc_context = "\n\n".join(doc_details)
        
        return f"""You are a visa documentation specialist. Answer the document question using ONLY the official information provided.

DETAILED DOCUMENT INFORMATION FROM ARTICLES:
{doc_context}

USER QUESTION: {query}

INSTRUCTIONS:
- List ALL documents mentioned in the articles
- Separate registration documents from petition documents
- Include any specific requirements or conditions for documents
- Mention if documents are copies or originals
- Specify any document evaluation requirements
- If document information is not available, clearly state this
- Do not add documents not mentioned in the articles
- Reference which article contains each document requirement

DETAILED DOCUMENT REQUIREMENTS:"""
    
    def get_optimal_prompt(self, query: str, search_results: List) -> str:
        """Get the optimal prompt based on query analysis."""
        
        query_types = self.detect_query_type(query)
        
        # Use specialized prompts for specific query types
        if len(query_types) == 1:
            if 'fees' in query_types:
                return self.create_fee_specific_prompt(query, search_results)
            elif 'dates' in query_types:
                return self.create_date_specific_prompt(query, search_results)
            elif 'documents' in query_types:
                return self.create_document_specific_prompt(query, search_results)
        
        # Use enhanced general prompt for mixed or general queries
        return self.create_enhanced_prompt(query, search_results, query_types)


# Example usage and testing
def demonstrate_prompt_improvements():
    """Demonstrate the prompt improvements."""
    
    templates = ImprovedPromptTemplates()
    
    # Example test queries from validation
    test_queries = [
        "What is the H1B fee for 2026?",
        "When is the H1B lottery for 2026?", 
        "What documents do I need for H1B?",
        "How does H1B lottery work?",
        "Premium processing fee for H1B"
    ]
    
    for query in test_queries:
        query_types = templates.detect_query_type(query)
        print(f"\nQuery: {query}")
        print(f"Detected types: {query_types}")
        print(f"Would use: {'Specialized' if len(query_types) == 1 else 'Enhanced general'} prompt")


if __name__ == "__main__":
    demonstrate_prompt_improvements()