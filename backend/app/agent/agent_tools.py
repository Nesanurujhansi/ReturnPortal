import json
import logging
import asyncio
from app.services.shopify_service import ShopifyService
from app.services.return_calculation_service import ReturnCalculationService
from app.services.status_service import StatusService
from app.database.mongodb import db
from app.models.schemas import ReturnItemSelection, ReturnCreateRequest
from app.api.endpoints import create_return_request

logger = logging.getLogger("app.agent.tools")

def _run_async(coro):
    """Safely runs a coroutine even if an event loop is already running in the current thread (e.g. Uvicorn)."""
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # If loop is already running, schedule the task and wait for it synchronously using a future
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result()
    except RuntimeError:
        pass
    
    # If no running loop, create/run one directly
    new_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()

def verify_order_tool(order_number: str, email: str) -> str:
    """Verify order using Shopify API."""
    try:
        order = _run_async(ShopifyService.verify_order(order_number, email))
        if order:
            customer_name = "Valued Customer"
            cust = order.get("customer")
            if cust:
                customer_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or customer_name
            return json.dumps({
                "success": True,
                "order_id": str(order["id"]),
                "order_number": order.get("name", "").replace("#", ""),
                "customer_name": customer_name,
                "email": order.get("email"),
                "fulfillment_status": order.get("fulfillment_status")
            })
        return json.dumps({"success": False, "message": "Order not found or email does not match."})
    except Exception as e:
        logger.error(f"verify_order_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def get_order_items_tool(order_id: str) -> str:
    """Fetch returnable line items."""
    try:
        items = _run_async(ShopifyService.get_order_items(order_id))
        normalized = []
        for line in items:
            normalized.append({
                "line_item_id": str(line["id"]),
                "product_id": str(line.get("product_id", "")),
                "variant_id": str(line.get("variant_id", "")),
                "title": line["title"],
                "sku": line.get("sku", ""),
                "quantity": line["quantity"],
                "price": float(line["price"])
            })
        return json.dumps({"success": True, "items": normalized})
    except Exception as e:
        logger.error(f"get_order_items_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def get_return_methods_tool() -> str:
    """List Refund, Store Credit, Exchange return methods."""
    try:
        async def fetch_methods():
            cursor = db.return_methods.find({"active": True})
            methods = await cursor.to_list(length=10)
            return [m["method"] for m in methods]
        methods_list = _run_async(fetch_methods())
        return json.dumps({"success": True, "methods": methods_list})
    except Exception as e:
        logger.error(f"get_return_methods_tool error: {e}")
        return json.dumps({"success": True, "methods": ["refund", "credit", "exchange"]})

def get_return_reasons_tool() -> str:
    """List return reasons and their validation requirements."""
    try:
        async def fetch_reasons():
            cursor = db.return_reasons.find({})
            reasons = await cursor.to_list(length=20)
            return [
                {
                    "reason": r["reason"],
                    "requires_image": r.get("requires_image", False),
                    "requires_notes": r.get("requires_notes", False),
                    "requires_additional_reason": r.get("requires_additional_reason", False)
                }
                for r in reasons
            ]
        reasons_list = _run_async(fetch_reasons())
        return json.dumps({"success": True, "reasons": reasons_list})
    except Exception as e:
        logger.error(f"get_return_reasons_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def upload_image_guidance_tool(reason: str) -> str:
    """Tell user whether image is required for a return reason."""
    try:
        async def check_reason():
            rule = await db.return_reasons.find_one({"reason": reason})
            if not rule:
                # case insensitive match try
                async for r in db.return_reasons.find({}):
                    if r["reason"].lower() == reason.lower():
                        rule = r
                        break
            if rule:
                return rule.get("requires_image", False)
            return "damaged" in reason.lower() or "defective" in reason.lower()
        requires = _run_async(check_reason())
        return json.dumps({"success": True, "reason": reason, "requires_image": requires})
    except Exception as e:
        logger.error(f"upload_image_guidance_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def calculate_return_tool(order_id: str, product_id: str, quantity: int, return_method: str, reason: str) -> str:
    """Calculate refund/store credit/exchange summary."""
    try:
        order = _run_async(ShopifyService.get_order_details(order_id))
        if not order:
            return json.dumps({"success": False, "message": "Order not found."})
        order_items = order.get("line_items", [])
        items_list = [{"item_id": product_id, "quantity": quantity}]
        summary = _run_async(ReturnCalculationService.calculate(return_method, items_list, order_items))
        return json.dumps({
            "success": True,
            "subtotal": summary["subtotal"],
            "handling_fee": summary["restocking_fee"] if return_method == "refund" else 0.00,
            "total_refund_amount": summary["total"],
            "method": return_method
        })
    except Exception as e:
        logger.error(f"calculate_return_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def get_product_variants_tool(product_id: str) -> str:
    """Fetch Shopify variants for exchange."""
    try:
        variants = _run_async(ShopifyService.get_product_variants(product_id))
        normalized = []
        for var in variants:
            normalized.append({
                "variant_id": str(var["id"]),
                "title": var.get("title", ""),
                "price": float(var.get("price", 0.0)),
                "available": var.get("inventory_quantity", 0) > 0 if "inventory_quantity" in var else True
            })
        return json.dumps({"success": True, "variants": normalized})
    except Exception as e:
        logger.error(f"get_product_variants_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def create_return_request_tool(
    order_id: str,
    email: str,
    product_id: str,
    quantity: int,
    return_method: str,
    reason: str,
    notes: str = None,
    image_file_id: str = None,
    exchange_variant_id: str = None
) -> str:
    """Create return request using existing backend workflow."""
    try:
        # Get order details to look up order_number
        order = _run_async(ShopifyService.get_order_details(order_id))
        if not order:
            return json.dumps({"success": False, "message": "Order not found."})
        order_number = order.get("name", "").replace("#", "")

        # Call calculator to get subtotals/fees
        order_items = order.get("line_items", [])
        items_list = [{"item_id": product_id, "quantity": quantity}]
        summary = _run_async(ReturnCalculationService.calculate(return_method, items_list, order_items))

        # Format items payload
        items_payload = [{
            "item_id": product_id,
            "quantity": quantity,
            "reason": reason,
            "notes": notes,
            "image_file_id": image_file_id,
            "exchange_variant": {"size": "", "color": exchange_variant_id} if exchange_variant_id else None
        }]

        # Create create request schema payload
        payload = ReturnCreateRequest(
            order_number=order_number,
            email=email,
            method=return_method,
            items=items_payload,
            subtotal=summary["subtotal"],
            handling_fee=summary["restocking_fee"] if return_method == "refund" else 0.00,
            total_amount=summary["total"]
        )

        res = _run_async(create_return_request(payload))
        return json.dumps({
            "success": True,
            "return_id": res.return_id,
            "status": res.status,
            "tracking_number": res.tracking_number,
            "carrier": res.carrier,
            "shipping_label_url": res.shipping_label_url,
            "created_at": res.created_at
        })
    except Exception as e:
        logger.error(f"create_return_request_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def get_return_status_tool(return_id: str) -> str:
    """Fetch return request status."""
    try:
        status_info = _run_async(StatusService.get_return_status(return_id))
        if status_info:
            return json.dumps({"success": True, "status": status_info})
        return json.dumps({"success": False, "message": "Return request not found."})
    except Exception as e:
        logger.error(f"get_return_status_tool error: {e}")
        return json.dumps({"success": False, "message": str(e)})

def update_return_session_details_tool(
    product_id: str = None,
    quantity: int = None,
    return_method: str = None,
    return_reason: str = None,
    notes: str = None,
    image_file_id: str = None,
    exchange_variant_id: str = None
) -> str:
    """
    Call this tool to save or update active return session details in memory.
    Use it immediately when the customer specifies the item to return, quantity, return method (refund/credit/exchange), reason, notes, image, or exchange variant selection.
    """
    try:
        return json.dumps({
            "success": True,
            "product_id": product_id,
            "quantity": quantity,
            "return_method": return_method,
            "return_reason": return_reason,
            "notes": notes,
            "image_file_id": image_file_id,
            "exchange_variant_id": exchange_variant_id
        })
    except Exception as e:
        return json.dumps({"success": False, "message": str(e)})


