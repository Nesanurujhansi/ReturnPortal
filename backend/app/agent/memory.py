import logging
from typing import Dict, Any

logger = logging.getLogger("app.agent.memory")

class SessionMemory:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "order_number": None,
                "email": None,
                "order_id": None,
                "selected_product": None,
                "quantity": None,
                "return_method": None,
                "return_reason": None,
                "notes": None,
                "image_file_id": None,
                "exchange_variant": None
            }
        return self.sessions[session_id]

    def update_session(self, session_id: str, data: Dict[str, Any]):
        session = self.get_session(session_id)
        for k, v in data.items():
            if k in session:
                session[k] = v

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

memory_store = SessionMemory()
