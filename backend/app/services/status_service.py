import datetime
import logging
from typing import Optional, Dict, Any
from app.database.mongodb import db

logger = logging.getLogger("app.services.status")

VALID_STATUSES = {
    "Created",
    "Pending Review",
    "Approved",
    "Rejected",
    "Label Generated",
    "In Transit",
    "Completed"
}

class StatusService:
    @classmethod
    async def get_return_status(cls, return_id: str) -> Optional[Dict[str, Any]]:
        """Fetch current status and timestamps of a return request."""
        if db.returns is not None:
            try:
                ret = await db.returns.find_one({"return_id": return_id})
                if ret:
                    return {
                        "return_id": ret.get("return_id"),
                        "status": ret.get("status", "Created"),
                        "created_at": ret.get("created_at"),
                        "updated_at": ret.get("updated_at", ret.get("created_at"))
                    }
            except Exception as e:
                logger.error(f"Error fetching return status for {return_id}: {e}")
        return None

    @classmethod
    async def transition_status(cls, return_id: str, new_status: str) -> bool:
        """Transitions return request status and appends audit log entry."""
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status value: {new_status}")

        updated = False
        now_str = datetime.datetime.utcnow().isoformat()

        if db.returns is not None:
            try:
                result = await db.returns.update_one(
                    {"return_id": return_id},
                    {"$set": {"status": new_status, "updated_at": now_str}}
                )
                if result.modified_count > 0:
                    # Write audit log
                    await db.audit_logs.insert_one({
                        "event": "STATUS_TRANSITION",
                        "return_id": return_id,
                        "timestamp": now_str,
                        "details": f"Transitioned status to {new_status}"
                    })
                    updated = True
                    logger.info(f"Transitioned return {return_id} status to {new_status}")
            except Exception as e:
                logger.error(f"Failed to transition return status: {e}")

        return updated
