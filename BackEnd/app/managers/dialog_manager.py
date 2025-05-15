import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, UTC
import json
import aiohttp
from functools import lru_cache

class DialogManager:
    """Manages dialog interactions and message processing"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the dialog manager with configuration"""
        self.config = config
        self.message_queue = asyncio.Queue()
        self.response_cache = {}
        self._welcome_messages = {}
        self._load_welcome_messages()
    
    def _load_welcome_messages(self):
        """Load welcome messages from configuration"""
        try:
            with open(self.config.get('welcome_messages_path', 'config/welcome_messages.json'), 'r') as f:
                self._welcome_messages = json.load(f)
        except FileNotFoundError:
            self._welcome_messages = {
                'default': "Hi I'm AutoVend, your smart assistant! How can I assist you in finding your ideal vehicle today?"
            }
    
    @lru_cache(maxsize=100)
    def get_welcome_message(self, language: str = 'en') -> str:
        """Get welcome message for specified language"""
        return self._welcome_messages.get(language, self._welcome_messages['default'])
    
    async def process_message(self, session_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming message and generate response"""
        # Add message to queue for processing
        await self.message_queue.put({
            'session_id': session_id,
            'message': message,
            'context': context,
            'timestamp': datetime.now(UTC).isoformat()
        })
        
        # Get cached response if available
        cache_key = f"{session_id}:{message}"
        if cache_key in self.response_cache:
            return self.response_cache[cache_key]
        
        # Process message asynchronously
        try:
            response = await self._generate_response(session_id, message, context)
            # Cache the response
            self.response_cache[cache_key] = response
            return response
        except Exception as e:
            # Log error and return fallback response
            print(f"Error processing message: {e}")
            return {
                'error': 'Failed to process message',
                'fallback_response': "I apologize, but I'm having trouble processing your request right now. Could you please try again?"
            }
    
    async def _generate_response(self, session_id: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response for the message"""
        # This is where you would integrate with your LLM or other response generation system
        # For now, we'll simulate a delay
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Example response structure
        return {
            'message_id': session_id,
            'sender_type': 'system',
            'sender_id': 'agent_123',
            'content': f"Processed response for: {message}",
            'timestamp': datetime.now(UTC).isoformat(),
            'status': 'delivered'
        }
    
    async def start_processing_loop(self):
        """Start the message processing loop"""
        while True:
            try:
                # Get message from queue
                message_data = await self.message_queue.get()
                
                # Process message
                response = await self._generate_response(
                    message_data['session_id'],
                    message_data['message'],
                    message_data['context']
                )
                
                # Store response in cache
                cache_key = f"{message_data['session_id']}:{message_data['message']}"
                self.response_cache[cache_key] = response
                
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception as e:
                print(f"Error in processing loop: {e}")
                await asyncio.sleep(1)  # Prevent tight loop on error
    
    def clear_cache(self, session_id: Optional[str] = None):
        """Clear response cache for a session or all sessions"""
        if session_id:
            # Clear specific session cache
            keys_to_remove = [k for k in self.response_cache.keys() if k.startswith(f"{session_id}:")]
            for key in keys_to_remove:
                del self.response_cache[key]
        else:
            # Clear all cache
            self.response_cache.clear()
    
    async def close(self):
        """Clean up resources"""
        # Wait for queue to be empty
        await self.message_queue.join()
        # Clear cache
        self.clear_cache() 