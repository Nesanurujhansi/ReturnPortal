import datetime
import random
import uuid
import logging
from typing import Dict, Any, List, Optional
from app.database.connection import db_instance
from app.services.shopify_service import ShopifyService
from app.models.schemas import ReturnItemSelection, ReturnCreateRequest

logger = logging.getLogger("app.returns")

# Local in-memory store for fallback offline storage
SIMULATED_RETURNS_DB = {}

class ReturnService:
    @staticmethod
    def calculate_summary(method: str, items: List[ReturnItemSelection], order_items: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate item subtotal, fees, and final value."""
        subtotal = 0.0
        
        # Build price lookup table from Shopify/Mock items
        price_lookup = {item["id"]: float(item["price"]) for item in order_items}
        
        for item in items:
            price = price_lookup.get(item.item_id, 0.0)
            subtotal += price * item.quantity

        # Waive fee for Store Credit and Exchange
        handling_fee = 5.99 if method == "refund" else 0.00
        total_amount = max(0.0, subtotal - handling_fee)

        return {
            "subtotal": round(subtotal, 2),
            "handling_fee": round(handling_fee, 2),
            "total_amount": round(total_amount, 2)
        }

    @classmethod
    async def create_return_request(cls, request_data: ReturnCreateRequest) -> Dict[str, Any]:
        """Validates returns business logic and persists the return request."""
        # 1. Fetch order details to validate items
        order = await ShopifyService.verify_order(request_data.order_number, request_data.email)
        if not order:
            raise ValueError("Order not found or email does not match.")

        # 2. Check items belong to the order and quantities do not exceed original purchase
        order_items = order.get("line_items", [])
        order_items_map = {item["id"]: item for item in order_items}

        for request_item in request_data.items:
            orig_item = order_items_map.get(request_item.item_id)
            if not orig_item:
                raise ValueError(f"Product ID {request_item.item_id} does not belong to this order.")
            
            if request_item.quantity > orig_item["quantity"]:
                raise ValueError(f"Return quantity for {orig_item['title']} exceeds purchased quantity.")

            # 3. Defective/Damaged validation check: requires notes and image upload (image_file_id)
            if "defective" in request_item.reason.lower() or "damaged" in request_item.reason.lower():
                if not request_item.notes or len(request_item.notes.strip()) < 5:
                    raise ValueError(f"Damaged items require descriptive comments/notes.")
                if not request_item.image_file_id:
                    raise ValueError(f"Uploading an image is required when returning damaged items.")

            # 4. Exchange validation check: exchange requires variant selection
            if request_data.method == "exchange" and not request_item.exchange_variant:
                raise ValueError(f"Exchange option requires specifying a target variant size or color.")

        # Recalculate summary to prevent tampering
        summary = cls.calculate_summary(request_data.method, request_data.items, order_items)
        
        # Unique return ID and shipping details
        return_id = f"RET-{random.randint(100000, 999999)}"
        tracking_number = f"940010000000{random.randint(1000000000, 9999999999)}"
        carrier = "USPS"
        status = "Pending Review"  # Default status

        return_doc = {
            "return_id": return_id,
            "order_number": request_data.order_number,
            "email": request_data.email,
            "method": request_data.method,
            "items": [item.model_dump() for item in request_data.items],
            "subtotal": summary["subtotal"],
            "handling_fee": summary["handling_fee"],
            "total_amount": summary["total_amount"],
            "status": status,
            "tracking_number": tracking_number,
            "carrier": carrier,
            "shipping_label_url": f"https://shipping-carrier.com/labels/{return_id}.pdf",
            "created_at": datetime.datetime.utcnow().isoformat()
        }

        # 5. Persist return request
        if db_instance.return_requests is not None:
            try:
                await db_instance.return_requests.insert_one(return_doc.copy())
                # Add audit log
                audit_log = {
                    "event": "RETURN_CREATED",
                    "return_id": return_id,
                    "order_number": request_data.order_number,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "details": f"Created return of type {request_data.method}"
                }
                await db_instance.audit_logs.insert_one(audit_log)
            except Exception as e:
                logger.error(f"Failed to persist return in MongoDB: {e}")
                SIMULATED_RETURNS_DB[return_id] = return_doc
        else:
            logger.info("Using simulated in-memory store to save return request.")
            SIMULATED_RETURNS_DB[return_id] = return_doc

        return return_doc

    @classmethod
    async def get_return_by_id(cls, return_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve return details by Return ID."""
        if db_instance.return_requests is not None:
            try:
                ret = await db_instance.return_requests.find_one({"return_id": return_id})
                if ret:
                    # Strip MongoDB '_id' object to make it serializable
                    ret.pop("_id", None)
                    return ret
            except Exception as e:
                logger.error(f"MongoDB return retrieve error: {e}")
        
        return SIMULATED_RETURNS_DB.get(return_id)
