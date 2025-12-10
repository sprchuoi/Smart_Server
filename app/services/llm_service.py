import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import Intent

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service for intent parsing and natural language processing."""
    
    def __init__(self):
        self.local_model = None
        self.provider = settings.LLM_PROVIDER
        
    async def initialize(self):
        """Initialize LLM model."""
        try:
            if self.provider == "local" and settings.LLM_MODEL_PATH:
                await self._load_local_model()
            logger.info(f"LLM Service initialized with provider: {self.provider}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            if settings.LLM_FALLBACK_PROVIDER:
                logger.info(f"Will use fallback provider: {settings.LLM_FALLBACK_PROVIDER}")
                self.provider = settings.LLM_FALLBACK_PROVIDER
    
    async def _load_local_model(self):
        """Load local LLM model using llama-cpp-python."""
        try:
            from llama_cpp import Llama
            
            logger.info(f"Loading local LLM model from {settings.LLM_MODEL_PATH}")
            self.local_model = Llama(
                model_path=settings.LLM_MODEL_PATH,
                n_ctx=2048,
                n_threads=4,
                n_gpu_layers=0  # Set to > 0 if GPU available
            )
            logger.info("Local LLM model loaded successfully")
        except FileNotFoundError:
            logger.warning(f"LLM model file not found at {settings.LLM_MODEL_PATH}")
            self.local_model = None
        except Exception as e:
            logger.error(f"Error loading local LLM model: {e}")
            self.local_model = None
    
    async def parse_intent(self, user_message: str) -> Dict[str, Any]:
        """Parse user message to extract intent and entities."""
        try:
            # Create prompt for intent parsing
            prompt = self._create_intent_prompt(user_message)
            
            # Get response from LLM
            if self.provider == "local" and self.local_model:
                response = await self._query_local_model(prompt)
            elif self.provider == "openai":
                response = await self._query_openai(prompt)
            elif self.provider == "anthropic":
                response = await self._query_anthropic(prompt)
            else:
                # Fallback to simple rule-based parsing
                response = self._simple_intent_parsing(user_message)
            
            # Store intent in database
            await self._store_intent(user_message, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            return {
                "intent_type": "unknown",
                "entities": {},
                "confidence": 0.0,
                "actions": []
            }
    
    def _create_intent_prompt(self, user_message: str) -> str:
        """Create prompt for intent parsing."""
        return f"""Parse the following smart home command and extract:
1. Intent type (e.g., control_device, query_status, automation, report)
2. Entities (device names, actions, values, conditions)
3. Actions to execute

User message: "{user_message}"

Respond in JSON format:
{{
  "intent_type": "...",
  "entities": {{}},
  "confidence": 0.0-1.0,
  "actions": []
}}"""
    
    async def _query_local_model(self, prompt: str) -> Dict[str, Any]:
        """Query local LLM model."""
        try:
            output = self.local_model(
                prompt,
                max_tokens=256,
                temperature=0.7,
                stop=["User:", "\n\n"]
            )
            
            response_text = output['choices'][0]['text'].strip()
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            logger.error(f"Error querying local model: {e}")
            return self._simple_intent_parsing(prompt)
    
    async def _query_openai(self, prompt: str) -> Dict[str, Any]:
        """Query OpenAI API."""
        try:
            if not settings.OPENAI_API_KEY:
                raise ValueError("OpenAI API key not configured")
            
            import openai
            openai.api_key = settings.OPENAI_API_KEY
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a smart home assistant that parses user commands."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=256
            )
            
            response_text = response.choices[0].message.content
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            logger.error(f"Error querying OpenAI: {e}")
            return self._simple_intent_parsing(prompt)
    
    async def _query_anthropic(self, prompt: str) -> Dict[str, Any]:
        """Query Anthropic Claude API."""
        try:
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("Anthropic API key not configured")
            
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            
            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=256,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = message.content[0].text
            return self._parse_llm_response(response_text)
            
        except Exception as e:
            logger.error(f"Error querying Anthropic: {e}")
            return self._simple_intent_parsing(prompt)
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response text to extract JSON."""
        try:
            # Try to find JSON in response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return self._simple_intent_parsing(response_text)
                
        except json.JSONDecodeError:
            return self._simple_intent_parsing(response_text)
    
    def _simple_intent_parsing(self, message: str) -> Dict[str, Any]:
        """Simple rule-based intent parsing as fallback."""
        message_lower = message.lower()
        
        # Detect intent type
        intent_type = "unknown"
        entities = {}
        actions = []
        confidence = 0.6
        
        if any(word in message_lower for word in ["turn on", "switch on", "enable"]):
            intent_type = "control_device"
            entities["action"] = "turn_on"
            actions.append({"type": "control", "action": "on"})
            
        elif any(word in message_lower for word in ["turn off", "switch off", "disable"]):
            intent_type = "control_device"
            entities["action"] = "turn_off"
            actions.append({"type": "control", "action": "off"})
            
        elif any(word in message_lower for word in ["status", "check", "how is"]):
            intent_type = "query_status"
            actions.append({"type": "query", "target": "status"})
            
        elif any(word in message_lower for word in ["report", "generate", "show me"]):
            intent_type = "report"
            actions.append({"type": "generate_report"})
            
        return {
            "intent_type": intent_type,
            "entities": entities,
            "confidence": confidence,
            "actions": actions
        }
    
    async def _store_intent(self, user_message: str, intent_data: Dict[str, Any]):
        """Store parsed intent in database."""
        try:
            async with AsyncSessionLocal() as session:
                intent = Intent(
                    user_message=user_message,
                    intent_type=intent_data.get("intent_type", "unknown"),
                    entities=json.dumps(intent_data.get("entities", {})),
                    confidence=intent_data.get("confidence", 0.0),
                    actions=json.dumps(intent_data.get("actions", [])),
                    processed=False
                )
                session.add(intent)
                await session.commit()
                logger.info(f"Stored intent: {intent_data['intent_type']}")
        except Exception as e:
            logger.error(f"Error storing intent: {e}")


# Global LLM service instance
llm_service = LLMService()
