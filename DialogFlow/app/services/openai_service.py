"""
OpenAI service for handling API interactions.
"""
import json
import logging
from typing import Dict, List, Any, Optional
import openai
from app.config import OPENAI_API_KEY, OPENAI_MODEL, SYSTEM_PROMPTS

# Configure logging
logger = logging.getLogger(__name__)

# Set OpenAI API key
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY
else:
    logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")


class OpenAIService:
    """
    Service for interacting with OpenAI API.
    """
    
    @staticmethod
    async def create_chat_completion(messages: List[Dict[str, Any]], 
                              system_prompt: Optional[str] = None) -> str:
        """
        Generate a response using OpenAI's chat completion API.
        
        Args:
            messages: List of message objects
            system_prompt: Optional system prompt to override the default
            
        Returns:
            The generated response content
            
        Raises:
            Exception: If there is an error with the OpenAI API
        """
        try:
            # Add system prompt if provided
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            # Call OpenAI API
            response = await openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                n=1,
                stream=False
            )
            
            # Return the content of the response
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error while calling OpenAI API: {str(e)}")
            raise
    
    @staticmethod
    async def extract_structured_data(text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from text using OpenAI.
        
        Args:
            text: The text to extract data from
            schema: The schema for the expected structured data
            
        Returns:
            Extracted structured data
            
        Raises:
            Exception: If there is an error with the OpenAI API or parsing the response
        """
        try:
            # Create messages for the API call
            messages = [
                {"role": "system", "content": f"""
                Extract structured information from the given text according to the following schema: 
                {json.dumps(schema, indent=2)}
                
                Return ONLY a valid JSON object containing the extracted information.
                If information is not present in the text, leave the corresponding field as null.
                """},
                {"role": "user", "content": text}
            ]
            
            # Call OpenAI API
            response = await openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.0,  # Use lower temperature for more deterministic results
                max_tokens=1000,
                n=1,
                stream=False
            )
            
            # Parse the response as JSON
            response_text = response.choices[0].message.content
            
            # Clean up the response to extract only the JSON part
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error(f"Could not find JSON in response: {response_text}")
                return {}
                
            json_text = response_text[json_start:json_end]
            
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON: {json_text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error while extracting structured data: {str(e)}")
            raise
    
    @staticmethod
    async def analyze_sentiment(text: str) -> Dict[str, float]:
        """
        Analyze sentiment in the given text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Dictionary with sentiment scores
            
        Raises:
            Exception: If there is an error with the OpenAI API
        """
        try:
            # Create messages for the API call
            messages = [
                {"role": "system", "content": """
                Analyze the sentiment in the given text. Rate the following emotional dimensions on a scale from 0.0 to 1.0:
                - Positivity: How positive the message is (0.0 = very negative, 1.0 = very positive)
                - Engagement: How engaged the user is (0.0 = disinterested, 1.0 = highly engaged)
                - Decisiveness: How decisive the user is (0.0 = very uncertain, 1.0 = very decisive)
                - Satisfaction: How satisfied the user is (0.0 = very unsatisfied, 1.0 = very satisfied)
                
                Return ONLY a valid JSON object with these four dimensions.
                """},
                {"role": "user", "content": text}
            ]
            
            # Call OpenAI API
            response = await openai.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.0,
                max_tokens=500,
                n=1,
                stream=False
            )
            
            # Parse the response as JSON
            response_text = response.choices[0].message.content
            
            # Clean up the response to extract only the JSON part
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error(f"Could not find JSON in response: {response_text}")
                return {
                    "positivity": 0.5,
                    "engagement": 0.5,
                    "decisiveness": 0.5,
                    "satisfaction": 0.5
                }
                
            json_text = response_text[json_start:json_end]
            
            try:
                return json.loads(json_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON: {json_text}")
                return {
                    "positivity": 0.5,
                    "engagement": 0.5,
                    "decisiveness": 0.5,
                    "satisfaction": 0.5
                }
                
        except Exception as e:
            logger.error(f"Error while analyzing sentiment: {str(e)}")
            raise


# Create a singleton instance
openai_service = OpenAIService() 