"""
Smart chat response synthesizer that analyzes vector search results
and creates human-like summaries instead of just showing raw messages.
"""
from typing import List, Dict, Any
import re
from collections import Counter


class ChatSynthesizer:
    """Synthesizes coherent answers from multiple conversation snippets"""
    
    def __init__(self):
        # Keywords for detecting different question types
        self.document_keywords = ['document', 'documents', 'required', 'requirement', 'need', 'paperwork', 'papers']
        self.timeline_keywords = ['how long', 'timeline', 'processing time', 'wait', 'duration', 'days', 'weeks', 'months']
        self.experience_keywords = ['experience', 'interview', 'what happened', 'my experience', 'went through']
        self.process_keywords = ['how to', 'process', 'steps', 'procedure', 'apply']
        self.location_keywords = ['consulate', 'embassy', 'location', 'mumbai', 'delhi', 'chennai', 'hyderabad', 'kolkata']
        
    def detect_question_type(self, query: str) -> str:
        """Detect what type of question the user is asking"""
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in self.document_keywords):
            return 'documents'
        elif any(kw in query_lower for kw in self.timeline_keywords):
            return 'timeline'
        elif any(kw in query_lower for kw in self.experience_keywords):
            return 'experience'
        elif any(kw in query_lower for kw in self.process_keywords):
            return 'process'
        elif any(kw in query_lower for kw in self.location_keywords):
            return 'location'
        else:
            return 'general'
    
    def extract_documents(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract and deduplicate document mentions from results"""
        documents = []
        seen = set()
        
        doc_patterns = [
            r'DS[-\s]?160',
            r'passport',
            r'I[-\s]?20',
            r'I[-\s]?797',
            r'appointment\s+(?:letter|confirmation)',
            r'photo(?:graph)?s?',
            r'resume',
            r'offer\s+letter',
            r'pay\s+stub(?:s)?',
            r'W[-\s]?2',
            r'tax\s+return(?:s)?',
            r'bank\s+statement(?:s)?',
            r'visa\s+fee\s+receipt',
            r'SEVIS\s+fee',
            r'LCA',
            r'petition',
            r'invitation\s+letter',
            r'birth\s+certificate',
        ]
        
        for result in results[:15]:  # Check more results
            text = result.get('text', '')
            text_lower = text.lower()
            
            # Extract document mentions
            for pattern in doc_patterns:
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                for match in matches:
                    normalized = match.strip().upper()
                    if normalized not in seen and len(normalized) > 2:
                        seen.add(normalized)
                        # Get context around the match
                        documents.append(match.strip())
        
        return documents
    
    def extract_timelines(self, results: List[Dict[str, Any]]) -> List[str]:
        """Extract timeline/duration mentions"""
        timelines = []
        
        for result in results[:10]:
            text = result.get('text', '')
            
            # Look for time patterns
            time_patterns = [
                r'\d+\s*(?:day|days|week|weeks|month|months)',
                r'\d+[-\s]?\d+\s*(?:day|days|week|weeks|month|months)',
                r'within\s+\d+\s*(?:day|days|week|weeks)',
                r'took\s+\d+\s*(?:day|days|week|weeks)',
                r'waited\s+\d+\s*(?:day|days|week|weeks)',
            ]
            
            for pattern in time_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if match not in timelines:
                        timelines.append(match.strip())
        
        return timelines[:5]
    
    def extract_key_points(self, results: List[Dict[str, Any]], question_type: str) -> List[str]:
        """Extract key points from results based on question type"""
        points = []
        seen_texts = set()
        
        for result in results[:15]:  # Check more results
            text = result.get('text', '').strip()
            
            # Skip very short texts, duplicate texts, or questions
            if len(text) < 20 or text.lower() in seen_texts or text.endswith('?'):
                continue
            
            seen_texts.add(text.lower())
            
            # Filter based on question type
            text_lower = text.lower()
            
            if question_type == 'documents' and any(kw in text_lower for kw in ['passport', 'ds-160', 'i-20', 'i-797', 'photograph', 'receipt', 'document', 'certificate']):
                points.append(text)
            elif question_type == 'timeline' and any(kw in text_lower for kw in ['day', 'week', 'month', 'time', 'took', 'wait']):
                points.append(text)
            elif question_type == 'experience' and any(kw in text_lower for kw in ['interview', 'experience', 'asked', 'officer', 'counter']):
                points.append(text)
            elif question_type in ['process', 'general']:
                points.append(text)
        
        return points[:6]
    
    def synthesize_response(self, query: str, results: List[Dict[str, Any]], total_found: int) -> str:
        """Create a synthesized, human-like response"""
        
        if not results:
            return self._create_no_results_response(query)
        
        # Detect question type
        question_type = self.detect_question_type(query)
        
        # Build response
        response_parts = []
        
        # Introduction
        intro = self._create_introduction(query, total_found, question_type)
        response_parts.append(intro)
        
        # Main content based on question type
        if question_type == 'documents':
            content = self._synthesize_documents(results)
        elif question_type == 'timeline':
            content = self._synthesize_timeline(results)
        elif question_type == 'experience':
            content = self._synthesize_experience(results)
        else:
            content = self._synthesize_general(results)
        
        response_parts.append(content)
        
        # Add context
        context = self._add_context(results)
        if context:
            response_parts.append(context)
        
        return '\n\n'.join(response_parts)
    
    def _create_introduction(self, query: str, total_found: int, question_type: str) -> str:
        """Create a natural introduction"""
        if total_found > 1000:
            return f"I found **{total_found:,}+ conversations** about this. Here's what the community says:"
        elif total_found > 100:
            return f"Based on **{total_found:,}+ discussions**, here's what I found:"
        elif total_found > 10:
            return f"I found **{total_found} relevant conversations**. Here's a summary:"
        else:
            return f"I found **{total_found} conversations** about this:"
    
    def _synthesize_documents(self, results: List[Dict[str, Any]]) -> str:
        """Synthesize document requirements"""
        documents = self.extract_documents(results)
        key_points = self.extract_key_points(results, 'documents')
        
        response = "📄 **Required Documents:**\n\n"
        
        if documents:
            # Group similar documents
            doc_list = list(set([d.upper() for d in documents[:15]]))
            for doc in sorted(doc_list):
                response += f"• {doc}\n"
        
        # Add any additional context from key points
        if key_points:
            response += "\n**Additional Information:**\n\n"
            for point in key_points[:3]:
                response += f"• {point}\n"
        
        return response
    
    def _synthesize_timeline(self, results: List[Dict[str, Any]]) -> str:
        """Synthesize timeline information"""
        timelines = self.extract_timelines(results)
        key_points = self.extract_key_points(results, 'timeline')
        
        response = "⏰ **Processing Timeline:**\n\n"
        
        if timelines:
            for timeline in timelines[:5]:
                response += f"• {timeline}\n"
        
        if key_points:
            response += "\n**What people are saying:**\n\n"
            for point in key_points[:3]:
                response += f"• {point}\n"
        
        return response
    
    def _synthesize_experience(self, results: List[Dict[str, Any]]) -> str:
        """Synthesize interview/experience information"""
        key_points = self.extract_key_points(results, 'experience')
        
        response = "💬 **Community Experiences:**\n\n"
        
        for point in key_points[:5]:
            response += f"• {point}\n\n"
        
        return response
    
    def _synthesize_general(self, results: List[Dict[str, Any]]) -> str:
        """Synthesize general information"""
        key_points = self.extract_key_points(results, 'general')
        
        response = ""
        
        if key_points:
            # First point as main answer
            response += f"{key_points[0]}\n\n"
            
            # Additional points
            if len(key_points) > 1:
                response += "**Additional Information:**\n\n"
                for point in key_points[1:5]:
                    response += f"• {point}\n"
        else:
            # No direct answers found - show that we found related conversations
            response += "**Based on the conversations I found:**\n\n"
            for result in results[:5]:
                text = result.get('text', '').strip()
                if len(text) > 20 and not text.endswith('?'):
                    response += f"• {text}\n"
        
        return response
    
    def _add_context(self, results: List[Dict[str, Any]]) -> str:
        """Add contextual information"""
        # Extract visa types
        visa_types = []
        locations = []
        
        for result in results[:10]:
            metadata = result.get('metadata', {})
            visa_type = metadata.get('visa_type', '')
            location = metadata.get('location', '')
            
            if visa_type and visa_type != 'unknown':
                visa_types.append(visa_type.upper())
            if location and location != 'unknown':
                locations.append(location.title())
        
        context_parts = []
        
        if visa_types:
            unique_types = list(set(visa_types))[:3]
            context_parts.append(f"**Visa Types:** {', '.join(unique_types)}")
        
        if locations:
            unique_locations = list(set(locations))[:3]
            context_parts.append(f"**Locations:** {', '.join(unique_locations)}")
        
        return '\n'.join(context_parts) if context_parts else ''
    
    def _create_no_results_response(self, query: str) -> str:
        """Response when no results found"""
        return f"""I couldn't find specific information about "{query}" in the visa conversations database.

**Try asking about:**
• Document requirements for specific visa types
• Processing timelines and wait times
• Interview experiences at different consulates
• Visa application procedures
• Dropbox eligibility requirements"""
