import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from app.agent.return_agent import ReturnAgent
from app.agent.memory import memory_store

logger = logging.getLogger("app.api.agent")
router = APIRouter()
agent_instance = ReturnAgent()

class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str

class ChatPayload(BaseModel):
    session_id: str = Field(..., description="Unique user session ID")
    history: List[ChatMessage] = Field(default=[], description="Chat history list")
    message: str = Field(..., description="Customer message")

@router.post("/agent/chat")
async def chat_with_agent(payload: ChatPayload):
    try:
        history_list = [{"role": msg.role, "content": msg.content} for msg in payload.history]
        res = await agent_instance.run_chat(payload.session_id, history_list, payload.message)
        return {
            "success": True,
            "reply": res["reply"],
            "session_id": payload.session_id,
            "next_action": res["next_action"]
        }
    except Exception as e:
        logger.error(f"Chat agent endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conversational Agent failed: {str(e)}"
        )

@router.get("/agent/session/{session_id}")
async def get_agent_session(session_id: str):
    """Retrieve session memory store context."""
    session = memory_store.get_session(session_id)
    return {
        "success": True,
        "session_id": session_id,
        "data": session
    }

@router.delete("/agent/session/{session_id}")
async def delete_agent_session(session_id: str):
    """Clear conversational session memory."""
    memory_store.clear_session(session_id)
    return {
        "success": True,
        "message": f"Session {session_id} has been deleted."
    }
