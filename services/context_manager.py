from typing import List, Dict
from services.gemini_service import GeminiService
import config
import logging

logger = logging.getLogger(__name__)

class ContextManager:
    def __init__(self):
        self.gemini_service = GeminiService()
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for Russian)"""
        return len(text) // 3
    
    def _calculate_context_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Calculate total tokens in context"""
        total_tokens = 0
        for msg in messages:
            total_tokens += self._estimate_tokens(msg["content"])
        return total_tokens
    
    async def prepare_context(
        self, 
        messages: List[Dict[str, str]], 
        encrypted_api_key: str,
        model_name: str
    ) -> List[Dict[str, str]]:
        """Prepare context for Gemini, summarizing if needed"""
        
        if not messages:
            return messages
        
        total_tokens = self._calculate_context_tokens(messages)
        
        # If context is within limits, return as is
        if total_tokens <= config.MAX_CONTEXT_TOKENS:
            return messages
        
        # Calculate how many messages to summarize
        target_tokens = int(config.MAX_CONTEXT_TOKENS * config.CONTEXT_SUMMARY_RATIO)
        
        # Find split point
        current_tokens = 0
        split_index = 0
        
        for i, msg in enumerate(messages):
            msg_tokens = self._estimate_tokens(msg["content"])
            if current_tokens + msg_tokens > target_tokens:
                split_index = i
                break
            current_tokens += msg_tokens
        
        # Ensure we don't summarize everything
        if split_index < 2:
            # Just keep the most recent messages if context is too large
            recent_tokens = 0
            for i in range(len(messages) - 1, -1, -1):
                msg_tokens = self._estimate_tokens(messages[i]["content"])
                if recent_tokens + msg_tokens > config.MAX_CONTEXT_TOKENS:
                    return messages[i + 1:]
                recent_tokens += msg_tokens
            return messages
        
        try:
            # Summarize old messages
            old_messages = messages[:split_index]
            summary = await self.gemini_service.summarize_context(encrypted_api_key, old_messages, model_name)
            
            # Create summary message
            summary_message = {
                "role": "model",
                "content": f"[Краткое содержание предыдущего разговора: {summary}]"
            }
            
            # Return summary + recent messages
            return [summary_message] + messages[split_index:]
            
        except Exception as e:
            logger.error(f"Context summarization failed: {e}")
            # Fallback: just keep recent messages
            recent_tokens = 0
            for i in range(len(messages) - 1, -1, -1):
                msg_tokens = self._estimate_tokens(messages[i]["content"])
                if recent_tokens + msg_tokens > config.MAX_CONTEXT_TOKENS:
                    return messages[i + 1:]
                recent_tokens += msg_tokens
            return messages