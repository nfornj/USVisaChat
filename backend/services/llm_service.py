"""
Flexible LLM Service
Supports both Ollama (local development) and Groq API (production deployment)
Uses Llama 3.1 8B model for both environments
"""

import os
import logging
import httpx
from typing import Dict, Optional
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    OLLAMA = "ollama"
    GROQ = "groq"


class LLMService:
    """
    Flexible LLM service that can use either:
    - Ollama (local development) - Llama 3.1 8B
    - Groq API (production) - Llama 3.1 8B
    """
    
    def __init__(self):
        self.provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        self.model_name = os.getenv('LLM_MODEL', 'llama3.2:3b')
        
        # Ollama configuration
        self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
        
        # Groq configuration
        self.groq_api_key = os.getenv('GROQ_API_KEY')
        self.groq_base_url = 'https://api.groq.com/openai/v1'
        
        # Model mapping for different providers
        self.model_mapping = {
            'ollama': self.model_name,  # e.g., "llama3.1:8b"
            'groq': 'llama-3.1-8b-instant'  # Groq model name
        }
        
        logger.info(f"🤖 LLM Service initialized:")
        logger.info(f"   Provider: {self.provider}")
        logger.info(f"   Model: {self.model_mapping.get(self.provider, self.model_name)}")
        
        if self.provider == 'groq' and not self.groq_api_key:
            logger.warning("⚠️  GROQ_API_KEY not found, falling back to Ollama")
            self.provider = 'ollama'
    
    async def generate_response(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 400,
        stream: bool = False
    ) -> str:
        """
        Generate response using the configured LLM provider
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Response creativity (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            
        Returns:
            Generated response text
        """
        try:
            if self.provider == 'ollama':
                return await self._generate_ollama(
                    prompt, system_prompt, temperature, max_tokens, stream
                )
            elif self.provider == 'groq':
                return await self._generate_groq(
                    prompt, system_prompt, temperature, max_tokens, stream
                )
            else:
                raise ValueError(f"Unknown LLM provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}")
            return f"Error generating response: {str(e)}"
    
    async def _generate_ollama(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> str:
        """Generate response using Ollama (local)"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model_mapping['ollama'],
                    "prompt": full_prompt,
                    "stream": stream,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['response'].strip()
            else:
                raise Exception(f"Ollama error: {response.status_code} - {response.text}")
    
    async def _generate_groq(
        self, 
        prompt: str, 
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
        stream: bool
    ) -> str:
        """Generate response using Groq API (production)"""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_mapping['groq'],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.groq_base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                raise Exception(f"Groq API error: {response.status_code} - {response.text}")
    
    def get_provider_info(self) -> Dict[str, str]:
        """Get current provider information"""
        return {
            "provider": self.provider,
            "model": self.model_mapping.get(self.provider, self.model_name),
            "host": self.ollama_host if self.provider == 'ollama' else self.groq_base_url,
            "api_key_configured": bool(self.groq_api_key) if self.provider == 'groq' else True
        }


# Global LLM service instance
llm_service = LLMService()
