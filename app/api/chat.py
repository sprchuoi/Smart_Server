from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.llm_service import llm_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    message: str


class IntentResponse(BaseModel):
    intent_type: str
    entities: dict
    confidence: float
    actions: list
    response: str


@router.post("/", response_model=IntentResponse)
async def process_chat_message(chat: ChatMessage):
    """Process a chat message and extract intent."""
    try:
        # Parse intent using LLM
        intent_data = await llm_service.parse_intent(chat.message)
        
        # Generate response based on intent
        response_text = _generate_response(intent_data)
        
        return {
            **intent_data,
            "response": response_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


def _generate_response(intent_data: dict) -> str:
    """Generate a human-readable response based on intent."""
    intent_type = intent_data.get("intent_type", "unknown")
    
    if intent_type == "control_device":
        action = intent_data.get("entities", {}).get("action", "action")
        return f"I'll {action} the device for you."
    
    elif intent_type == "query_status":
        return "Let me check the status for you."
    
    elif intent_type == "report":
        return "I'll generate that report for you."
    
    elif intent_type == "automation":
        return "I'll set up that automation."
    
    else:
        return "I'm not sure I understood that. Could you rephrase?"
