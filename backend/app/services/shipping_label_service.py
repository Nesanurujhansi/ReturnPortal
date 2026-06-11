import random
import logging
from typing import Dict, Any
from app.database.mongodb import db

logger = logging.getLogger("app.services.label")

class ShippingLabelService:
    @classmethod
    async def generate_mock_label(cls, return_id: str) -> Dict[str, Any]:
        """
        Generates return tracking details and mock label number.
        Stores output inside shipping_labels collection.
        """
        # Determine counter or index to make sequential labels, e.g. RET-2026-XXXXX
        serial = random.randint(10000, 99999)
        label_number = f"RET-2026-{serial}"
        tracking_number = f"940010000000{random.randint(1000000000, 9999999999)}"
        carrier = "USPS"

        label_doc = {
            "return_id": return_id,
            "label_number": label_number,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "shipping_label_url": f"http://localhost:8000/api/labels/{return_id}.pdf"
        }

        if db.shipping_labels is not None:
            try:
                await db.shipping_labels.insert_one(label_doc.copy())
                logger.info(f"Generated mock shipping label {label_number} for return {return_id}")
            except Exception as e:
                logger.error(f"Failed to save shipping label record: {e}")

        return label_doc
