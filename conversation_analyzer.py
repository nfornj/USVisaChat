"""Advanced conversation analysis for better Q&A extraction and context understanding."""

import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

import openai

@dataclass
class ConversationThread:
    """Represents a conversation thread with question and answers."""
    question_text: str
    answer_texts: List[str]
    topic: str
    confidence_score: float
    thread_id: str

@dataclass
class QAPair:
    """Represents a question-answer pair extracted from conversations."""
    question: str
    answer: str
    topic: str
    confidence: float
    upvotes: int = 0  # Based on reactions/replies
    timestamp: datetime = None

class ConversationAnalyzer:
    """Analyzes conversations to extract meaningful Q&A pairs and context."""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
        if not openai_client:
            print("Warning: OpenAI client not available - using fallback analysis methods")
        
        # Patterns for identifying questions
        self.question_patterns = [
            r'\?',  # Contains question mark
            r'^(what|how|when|where|why|which|who|can|could|would|should|is|are|do|does|did)\b',
            r'\b(help|advice|suggest|recommend|experience|anyone|somebody)\b',
            r'\b(process|procedure|requirement|document|step|timeline)\b.*\?',
        ]
        
        # Patterns for identifying answers/solutions
        self.answer_patterns = [
            r'\b(yes|no|try|use|go|visit|call|email|submit|apply)\b',
            r'\b(solution|answer|worked|success|approved|got|received)\b',
            r'\b(embassy|consulate|website|portal|office|center)\b',
            r'\b(document|form|fee|appointment|slot|date)\b',
        ]
        
        # Common visa-related topics for clustering
        self.visa_topics = {
            'appointment_booking': ['appointment', 'slot', 'booking', 'schedule', 'calendar'],
            'document_requirements': ['document', 'form', 'requirement', 'paperwork', 'certificate'],
            'processing_times': ['processing', 'timeline', 'duration', 'wait', 'delay'],
            'interview_preparation': ['interview', 'question', 'preparation', 'practice', 'tips'],
            'visa_stamping': ['stamping', 'passport', 'visa', 'stamp', 'collection'],
            'fee_payment': ['fee', 'payment', 'cost', 'charge', 'money', 'dollar'],
            'embassy_updates': ['embassy', 'consulate', 'closure', 'holiday', 'announcement'],
            'visa_denial': ['denial', 'rejected', 'refused', '221g', 'administrative'],
            'travel_restrictions': ['travel', 'restriction', 'ban', 'covid', 'entry'],
        }
    
    def is_question(self, text: str) -> float:
        """Determine if a message is likely a question. Returns confidence score 0-1."""
        if not text:
            return 0.0
        
        text_lower = text.lower().strip()
        score = 0.0
        
        # Check for question patterns
        for pattern in self.question_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 0.3
        
        # Boost score for explicit question words at start
        if re.match(r'^(what|how|when|where|why|which|who|can|could|would|should)\b', text_lower):
            score += 0.4
        
        # Question mark gives high confidence
        if '?' in text:
            score += 0.5
        
        # Help-seeking language
        help_words = ['help', 'advice', 'suggest', 'anyone', 'experience', 'know']
        for word in help_words:
            if word in text_lower:
                score += 0.2
                break
        
        return min(score, 1.0)
    
    def is_answer(self, text: str, question_text: str = None) -> float:
        """Determine if a message is likely an answer. Returns confidence score 0-1."""
        if not text:
            return 0.0
        
        text_lower = text.lower().strip()
        score = 0.0
        
        # Check for answer patterns
        for pattern in self.answer_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                score += 0.2
        
        # Definitive answers
        definitive_starters = ['yes', 'no', 'you can', 'you should', 'you need', 'try', 'go to']
        for starter in definitive_starters:
            if text_lower.startswith(starter):
                score += 0.4
                break
        
        # Experience sharing
        experience_words = ['i did', 'i got', 'i went', 'i called', 'i submitted', 'worked for me']
        for exp in experience_words:
            if exp in text_lower:
                score += 0.3
                break
        
        # Instructional language
        instruction_words = ['step', 'process', 'procedure', 'first', 'then', 'next', 'finally']
        for word in instruction_words:
            if word in text_lower:
                score += 0.2
                break
        
        # Length bonus (longer messages more likely to be helpful answers)
        if len(text) > 100:
            score += 0.1
        if len(text) > 200:
            score += 0.1
        
        return min(score, 1.0)
    
    def classify_topic(self, text: str) -> Tuple[str, float]:
        """Classify message topic based on keywords."""
        text_lower = text.lower()
        topic_scores = {}
        
        for topic, keywords in self.visa_topics.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            
            if score > 0:
                topic_scores[topic] = score / len(keywords)
        
        if topic_scores:
            best_topic = max(topic_scores.items(), key=lambda x: x[1])
            return best_topic[0], best_topic[1]
        
        return 'general', 0.1
    
    async def find_conversation_threads_from_csv(self, messages_data: List[Dict], 
                                      time_window_hours: int = 24) -> List[ConversationThread]:
        """Find conversation threads by analyzing message patterns, replies, and temporal proximity."""
        
        # Get recent messages from the chat
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        result = await session.execute(
            select(Message)
            .where(
                and_(
                    Message.chat_id == chat_id,
                    Message.timestamp >= cutoff_time,
                    Message.content.isnot(None),
                    Message.content != ''
                )
            )
            .order_by(Message.timestamp)
        )
        
        messages = result.scalars().all()
        threads = []
        processed_questions = set()  # Avoid duplicate processing
        
        # Create a lookup for quick reply resolution
        msg_lookup = {msg.telegram_id: msg for msg in messages}
        
        # Group messages by reply chains and topic similarity
        for i, msg in enumerate(messages):
            if msg.id in processed_questions:
                continue
                
            question_score = self.is_question(msg.content)
            
            if question_score > 0.6:  # High confidence question
                answer_messages = []
                
                # Method 1: Find direct replies to this message
                direct_replies = [m for m in messages if m.reply_to_id == msg.telegram_id]
                for reply in direct_replies:
                    answer_score = self.is_answer(reply.content, msg.content)
                    if answer_score > 0.4:  # Lower threshold for direct replies
                        answer_messages.append(reply)
                
                # Method 2: Find contextual answers in temporal proximity
                for j in range(i + 1, min(i + 15, len(messages))):  # Increased window
                    next_msg = messages[j]
                    
                    # Skip if already found as direct reply
                    if next_msg in answer_messages:
                        continue
                    
                    # Skip if too much time has passed
                    time_diff = (next_msg.timestamp - msg.timestamp).total_seconds()
                    if time_diff > 7200:  # 2 hours (increased from 1 hour)
                        break
                    
                    # Check if it's a contextual answer
                    answer_score = self.is_answer(next_msg.content, msg.content)
                    
                    # Boost score for direct replies
                    if next_msg.reply_to_id == msg.telegram_id:
                        answer_score += 0.4
                    # Boost for replies to replies (conversation chains)
                    elif next_msg.is_reply and next_msg.reply_to_id in [m.telegram_id for m in answer_messages]:
                        answer_score += 0.2
                    # Boost for same user responding (self-correction/addition)
                    elif next_msg.user_id == msg.user_id and "actually" in next_msg.content.lower():
                        answer_score += 0.2
                    
                    if answer_score > 0.5:
                        answer_messages.append(next_msg)
                
                # Method 3: Find reply chains (A asks, B replies, C replies to B, etc.)
                reply_chain_messages = []
                for answer_msg in answer_messages[:]:  # Copy to avoid modification during iteration
                    chain_replies = [m for m in messages if m.reply_to_id == answer_msg.telegram_id]
                    for chain_reply in chain_replies:
                        if self.is_answer(chain_reply.content, msg.content) > 0.3:
                            reply_chain_messages.append(chain_reply)
                
                answer_messages.extend(reply_chain_messages)
                
                # Remove duplicates and sort by timestamp
                answer_messages = list({msg.id: msg for msg in answer_messages}.values())
                answer_messages.sort(key=lambda x: x.timestamp)
                
                if answer_messages:
                    topic, topic_confidence = self.classify_topic(msg.content)
                    
                    # Calculate enhanced confidence score
                    reply_bonus = len(direct_replies) * 0.1  # Bonus for direct replies
                    chain_bonus = len(reply_chain_messages) * 0.05  # Bonus for reply chains
                    confidence = min(question_score + topic_confidence + reply_bonus + chain_bonus, 1.0)
                    
                    thread = ConversationThread(
                        question_message=msg,
                        answer_messages=answer_messages,
                        topic=topic,
                        confidence_score=confidence,
                        thread_id=f"thread_{msg.id}_{len(answer_messages)}_{len(direct_replies)}"
                    )
                    threads.append(thread)
                    processed_questions.add(msg.id)
        
        # Sort threads by confidence score (best first)
        threads.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return threads
    
    async def extract_qa_pairs(self, threads: List[ConversationThread]) -> List[QAPair]:
        """Extract clean Q&A pairs from conversation threads using LLM or fallback methods."""
        qa_pairs = []
        
        for thread in threads:
            try:
                question_text = thread.question_message.content
                answers_text = "\n".join([msg.content for msg in thread.answer_messages])
                
                if self.openai_client:
                    # Use LLM to clean and structure the Q&A
                    prompt = f"""
                    Extract a clean question-answer pair from this Telegram conversation about visa/immigration:
                    
                    QUESTION: {question_text}
                    
                    ANSWERS: {answers_text}
                    
                    Please provide:
                    1. A clear, well-formatted question
                    2. A comprehensive answer combining the best information from all responses
                    3. Rate the quality/usefulness of this Q&A pair (1-10)
                    
                    Format as JSON:
                    {{
                        "question": "cleaned question",
                        "answer": "comprehensive answer", 
                        "quality_score": 8,
                        "main_topic": "appointment_booking"
                    }}
                    """
                    
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are an expert at extracting and cleaning visa/immigration Q&A pairs from Telegram conversations."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.3
                    )
                    
                    import json
                    result = json.loads(response.choices[0].message.content.strip())
                    
                    if result.get('quality_score', 0) >= 6:  # Only keep high-quality pairs
                        qa_pair = QAPair(
                            question=result['question'],
                            answer=result['answer'],
                            question_message_id=thread.question_message.id,
                            answer_message_ids=[msg.id for msg in thread.answer_messages],
                            topic=result.get('main_topic', thread.topic),
                            confidence=result.get('quality_score', 0) / 10.0,
                            timestamp=thread.question_message.timestamp
                        )
                        qa_pairs.append(qa_pair)
                else:
                    # Fallback: Simple Q&A pair creation without LLM
                    # Basic quality scoring based on answer length and count
                    total_answer_length = sum(len(msg.content) for msg in thread.answer_messages)
                    answer_count = len(thread.answer_messages)
                    
                    # Simple quality score based on answer characteristics
                    quality_score = min(5 + (answer_count * 1.5) + (total_answer_length / 100), 10)
                    
                    if quality_score >= 6:  # Only keep reasonable quality pairs
                        # Combine answers simply
                        combined_answer = " ".join([msg.content for msg in thread.answer_messages])
                        
                        qa_pair = QAPair(
                            question=question_text,
                            answer=combined_answer,
                            question_message_id=thread.question_message.id,
                            answer_message_ids=[msg.id for msg in thread.answer_messages],
                            topic=thread.topic,
                            confidence=quality_score / 10.0,
                            timestamp=thread.question_message.timestamp
                        )
                        qa_pairs.append(qa_pair)
                    
            except Exception as e:
                print(f"Error processing thread {thread.thread_id}: {e}")
                continue
        
        return qa_pairs
    
    async def create_enhanced_embeddings(self, qa_pairs: List[QAPair]) -> List[Dict[str, Any]]:
        """Create enhanced embeddings that include conversation context."""
        enhanced_vectors = []
        
        # Skip if no OpenAI client available
        if not self.openai_client:
            print("OpenAI client not available - skipping embedding generation for Q&A pairs")
            return enhanced_vectors
        
        for qa_pair in qa_pairs:
            # Create rich text for embedding that includes context
            enhanced_text = f"""
            Question: {qa_pair.question}
            
            Answer: {qa_pair.answer}
            
            Topic: {qa_pair.topic}
            
            Context: This is a verified Q&A pair from visa community discussions with {len(qa_pair.answer_message_ids)} supporting responses.
            """
            
            # Generate embedding
            try:
                response = await self.openai_client.embeddings.create(
                    model="text-embedding-ada-002",
                    input=enhanced_text.strip()
                )
                
                embedding = response.data[0].embedding
                
                # Enhanced metadata for better retrieval
                metadata = {
                    "type": "qa_pair",
                    "question": qa_pair.question,
                    "answer": qa_pair.answer[:500],  # Truncate for metadata
                    "topic": qa_pair.topic,
                    "confidence": qa_pair.confidence,
                    "question_message_id": qa_pair.question_message_id,
                    "answer_message_ids": qa_pair.answer_message_ids,
                    "timestamp": qa_pair.timestamp.isoformat(),
                    "answer_count": len(qa_pair.answer_message_ids),
                    "quality_indicators": {
                        "has_multiple_answers": len(qa_pair.answer_message_ids) > 1,
                        "answer_length": len(qa_pair.answer),
                        "topic_confidence": qa_pair.confidence
                    }
                }
                
                enhanced_vectors.append({
                    "id": f"qa_{qa_pair.question_message_id}",
                    "embedding": embedding,
                    "metadata": metadata
                })
                
            except Exception as e:
                print(f"Error creating embedding for Q&A pair: {e}")
                continue
        
        return enhanced_vectors
    
    async def find_similar_questions(self, new_question: str, existing_qa_pairs: List[QAPair], 
                                   threshold: float = 0.8) -> List[QAPair]:
        """Find similar questions to avoid duplicates and surface existing answers."""
        try:
            # Generate embedding for new question
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=new_question
            )
            new_embedding = response.data[0].embedding
            
            # Calculate similarity with existing questions
            import numpy as np
            
            similar_pairs = []
            for qa_pair in existing_qa_pairs:
                # You'd need to store embeddings for existing questions
                # This is a simplified version
                similarity = self._calculate_text_similarity(new_question, qa_pair.question)
                if similarity > threshold:
                    similar_pairs.append(qa_pair)
            
            return sorted(similar_pairs, key=lambda x: x.confidence, reverse=True)
            
        except Exception as e:
            print(f"Error finding similar questions: {e}")
            return []
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity calculation (you'd use embeddings in practice)."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

# Usage example for CSV-based processing
async def analyze_conversations_from_csv(messages_data: List[Dict]):
    """Analyze conversations from CSV data and extract Q&A pairs."""
    
    try:
        openai_client = openai.OpenAI()  # Initialize with your API key
    except:
        openai_client = None
        
    analyzer = ConversationAnalyzer(openai_client)
    
    # Find conversation threads
    threads = await analyzer.find_conversation_threads_from_csv(messages_data, time_window_hours=48)
    print(f"Found {len(threads)} conversation threads")
    
    # Extract Q&A pairs
    qa_pairs = await analyzer.extract_qa_pairs(threads)
    print(f"Extracted {len(qa_pairs)} high-quality Q&A pairs")
    
    # Create enhanced embeddings
    if openai_client:
        enhanced_vectors = await analyzer.create_enhanced_embeddings(qa_pairs)
        print(f"Created {len(enhanced_vectors)} enhanced vectors")
    else:
        enhanced_vectors = []
        print("Skipped embeddings (no OpenAI client)")
    
    return qa_pairs, enhanced_vectors

if __name__ == "__main__":
    # Example usage with CSV data
    import asyncio
    
    async def main():
        # Example CSV data structure
        sample_data = [
            {"content": "How long is visa processing?", "timestamp": "2023-10-01T10:00:00", "user_id": "user1"},
            {"content": "Usually 2-3 weeks", "timestamp": "2023-10-01T10:01:00", "user_id": "user2"},
        ]
        
        qa_pairs, vectors = await analyze_conversations_from_csv(sample_data)
        
        for qa in qa_pairs[:3]:  # Show first 3
            print(f"\nQ: {qa.question}")
            print(f"A: {qa.answer[:200]}...")
            print(f"Topic: {qa.topic}, Confidence: {qa.confidence:.2f}")
    
    asyncio.run(main())
