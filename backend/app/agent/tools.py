import json
import logging
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool

from app.services.shopify_service import ShopifyService
from app.services.return_service import ReturnService
from app.models.schemas import ReturnItemSelection, ReturnCreateRequest

logger = logging.getLogger("app.agent.tools")

@tool
def verify_order_tool(order_number: str, email: str) -> str:
    """
    Verifies that an order exists and matches the customer's email.
    Args:
        order_number: The e-commerce order identifier (e.g., '1001' or '1002').
        email: The customer's email address.
    Returns:
        JSON string containing the verification status and order items if successful.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # Run async function in sync wrapper
        order = loop.run_until_complete(ShopifyService.verify_order(order_number, email))
        if order:
            return json.dumps({
                "success": True,
                "customer_name": f"{order.get('customer', {}).get('first_name', '')} {order.get('customer', {}).get('last_name', '')}".strip(),
                "order_number": order_number,
                "email": email,
                "items": [
                    {
                        "id": item["id"],
                        "name": item["title"],
                        "price": float(item["price"]),
                        "quantity": item["quantity"],
                        "variant": item["variant_title"]
                    }
                    for item in order.get("line_items", [])
                ]
            })
        return json.dumps({"success": False, "detail": "Order not found or email does not match."})
    except Exception as e:
        logger.error(f"verify_order_tool error: {e}")
        return json.dumps({"success": False, "detail": str(e)})

@tool
def get_order_items_tool(order_id: str) -> str:
    """
    Retrieves the line items inside a specific order ID.
    Args:
        order_id: The order ID or number.
    Returns:
        JSON list of items.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        items = loop.run_until_complete(ShopifyService.get_order_items(order_id))
        return json.dumps([
            {
                "id": item["id"],
                "name": item["title"],
                "price": float(item["price"]),
                "quantity": item["quantity"],
                "variant": item["variant_title"]
            }
            for item in items
        ])
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def calculate_return_tool(method: str, items_json: str, order_items_json: str) -> str:
    """
    Calculates subtotal, handling fees, and refund totals before submitting a return.
    Args:
        method: Return method ('refund', 'credit', 'exchange').
        items_json: JSON string representing list of Selected items: [{"item_id": "...", "quantity": 1}]
        order_items_json: JSON list of order items from order details to look up prices.
    Returns:
        JSON string of calculated return totals.
    """
    try:
        items_list = json.loads(items_json)
        order_items = json.loads(order_items_json)
        
        # Map input to Pydantic objects
        selections = [
            ReturnItemSelection(
                item_id=x["item_id"],
                quantity=x["quantity"],
                reason="Calculated by Agent"
            )
            for x in items_list
        ]
        
        summary = ReturnService.calculate_summary(method, selections, order_items)
        return json.dumps(summary)
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def create_return_request_tool(
    order_number: str,
    email: str,
    method: str,
    items_json: str,
    subtotal: float,
    handling_fee: float,
    total_amount: float
) -> str:
    """
    Submits and registers the return request in the database.
    Args:
        order_number: The order number.
        email: The customer's email.
        method: The return method ('refund', 'credit', 'exchange').
        items_json: JSON string representing the selected return items and their reasons:
                    [{"item_id": "...", "quantity": 1, "reason": "...", "notes": "...", "image_file_id": "...", "exchange_variant": {"size": "M"}}]
        subtotal: Subtotal calculated.
        handling_fee: Fee calculated.
        total_amount: Final amount/value.
    Returns:
        JSON string containing the created Return ID and tracking details.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        items_list = json.loads(items_json)
        selections = []
        for item in items_list:
            selections.append(
                ReturnItemSelection(
                    item_id=item["item_id"],
                    quantity=item["quantity"],
                    reason=item.get("reason", "Returned via Agent"),
                    notes=item.get("notes"),
                    image_file_id=item.get("image_file_id"),
                    exchange_variant=item.get("exchange_variant")
                )
            )

        payload = ReturnCreateRequest(
            order_number=order_number,
            email=email,
            method=method,
            items=selections,
            subtotal=subtotal,
            handling_fee=handling_fee,
            total_amount=total_amount
        )
        
        ret_doc = loop.run_until_complete(ReturnService.create_return_request(payload))
        return json.dumps({
            "success": True,
            "return_id": ret_doc["return_id"],
            "status": ret_doc["status"],
            "tracking_number": ret_doc["tracking_number"],
            "carrier": ret_doc["carrier"],
            "shipping_label_url": ret_doc["shipping_label_url"]
        })
    except Exception as e:
        return json.dumps({"success": False, "detail": str(e)})

@tool
def upload_image_tool(file_bytes_base64: str, filename: str) -> str:
    """
    Simulates uploading an image to the database GridFS bucket for return validation.
    Args:
        file_bytes_base64: Base64 encoded bytes of the uploaded image file.
        filename: Name of the uploaded file.
    Returns:
        JSON string returning the generated file_id.
    """
    import asyncio
    import base64
    from fastapi import UploadFile
    from app.api.endpoints import upload_return_image
    
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        file_bytes = base64.b64decode(file_bytes_base64)
        
        # Mock file wrapping for internal API upload call
        file_like = io.BytesIO(file_bytes)
        
        # Note: inside python, upload_return_image expects an UploadFile
        # Let's bypass HTTP router and trigger local file persistence directly:
        from app.database.connection import db_instance
        from bson import ObjectId
        from app.api.endpoints import SIMULATED_FILES

        file_id = str(ObjectId())
        # Cache file
        SIMULATED_FILES[file_id] = {
            "bytes": file_bytes,
            "filename": filename,
            "contentType": "image/png"
        }
        
        return json.dumps({"file_id": file_id, "filename": filename})
    except Exception as e:
        return json.dumps({"error": str(e)})

@tool
def get_return_status_tool(return_id: str) -> str:
    """
    Retrieves the status and logs of an active return request.
    Args:
        return_id: The Return ID identifier, e.g., 'RET-123456'.
    Returns:
        JSON description of the return details.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    try:
        ret = loop.run_until_complete(ReturnService.get_return_by_id(return_id))
        if ret:
            return json.dumps(ret)
        return json.dumps({"error": f"Return {return_id} not found."})
    except Exception as e:
        return json.dumps({"error": str(e)})
