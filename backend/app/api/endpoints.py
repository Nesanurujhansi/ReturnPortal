import io
import mimetypes
import logging
import datetime
import random
from bson import ObjectId
from fastapi import APIRouter, HTTPException, File, UploadFile, status
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any

from app.models.schemas import (
    OrderVerifyRequest, OrderVerifyResponse, ItemDetail,
    ReturnCalculateRequest, ReturnCalculateResponse,
    ReturnCreateRequest, ReturnCreateResponse, ReturnDetailResponse
)
from app.services.shopify_service import ShopifyService
from app.services.return_calculation_service import ReturnCalculationService
from app.services.status_service import StatusService
from app.services.shipping_label_service import ShippingLabelService
from app.database.mongodb import db

logger = logging.getLogger("app.api")
router = APIRouter()

@router.post("/orders/verify", response_model=OrderVerifyResponse)
async def verify_order(payload: OrderVerifyRequest):
    order = await ShopifyService.verify_order(payload.order_number, payload.email)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or email mismatch. For testing, try #1001 with customer@example.com."
        )
    
    items = []
    for line in order.get("line_items", []):
        exchange_options = {
            "sizes": ["Small", "Medium", "Large", "X-Large"],
            "colors": ["Indigo", "Black Denim", "Light Wash", "White", "Tan", "Heather Gray"]
        }
        
        # Determine image
        image_url = None
        if "product_id" in line and line["product_id"]:
            try:
                prod = await ShopifyService.get_product_details(str(line["product_id"]))
                if prod and prod.get("images"):
                    image_url = prod["images"][0].get("src")
            except Exception:
                pass
        if not image_url:
            image_url = "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&q=80&w=300"

        # Calculate tax
        tax = 0.0
        tax_lines = line.get("tax_lines", [])
        if tax_lines:
            tax = sum(float(tl.get("price", 0.0)) for tl in tax_lines)

        items.append(
            ItemDetail(
                id=str(line["id"]),
                name=line["title"],
                price=float(line["price"]),
                quantity=line["quantity"],
                variant=line.get("variant_title") or "Default Variant",
                image=image_url,
                exchangeOptions=exchange_options
            )
        )

    customer_name = "Valued Customer"
    cust = order.get("customer")
    if cust:
        customer_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or customer_name

    # Shopify order structure matches normalized response format requirements
    return OrderVerifyResponse(
        success=True,
        order_number=payload.order_number,
        email=payload.email,
        customer_name=customer_name,
        items=items
    )

@router.get("/orders/{order_id}")
async def get_order_details(order_id: str):
    order = await ShopifyService.get_order_details(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
    
    customer_name = "Valued Customer"
    cust = order.get("customer")
    if cust:
        customer_name = f"{cust.get('first_name', '')} {cust.get('last_name', '')}".strip() or customer_name

    return {
        "id": str(order.get("id")),
        "name": order.get("name"),
        "email": order.get("email"),
        "customer_name": customer_name,
        "fulfillment_status": order.get("fulfillment_status"),
        "items_count": len(order.get("line_items", []))
    }

@router.get("/orders/{order_id}/items")
async def get_order_items(order_id: str):
    items = await ShopifyService.get_order_items(order_id)
    if not items:
        raise HTTPException(status_code=404, detail="No items found for this order ID.")
    
    mapped_items = []
    for line in items:
        image_url = None
        if "product_id" in line and line["product_id"]:
            try:
                prod = await ShopifyService.get_product_details(str(line["product_id"]))
                if prod and prod.get("images"):
                    image_url = prod["images"][0].get("src")
            except Exception:
                pass
        if not image_url:
            image_url = "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&q=80&w=300"

        tax = 0.0
        tax_lines = line.get("tax_lines", [])
        if tax_lines:
            tax = sum(float(tl.get("price", 0.0)) for tl in tax_lines)

        mapped_items.append({
            "line_item_id": str(line["id"]),
            "product_id": str(line.get("product_id", "")),
            "variant_id": str(line.get("variant_id", "")),
            "title": line["title"],
            "sku": line.get("sku", ""),
            "quantity": line["quantity"],
            "price": float(line["price"]),
            "tax": tax,
            "image_url": image_url
        })
    return {
        "success": true,
        "items": mapped_items
    }


@router.get("/return-methods")
async def get_return_methods():
    """Fetches return methods configuration from MongoDB."""
    if db.return_methods is not None:
        try:
            cursor = db.return_methods.find({"active": True})
            methods = await cursor.to_list(length=10)
            # Map description metadata
            method_desc = {
                "refund": "Refund to original payment card (-$5.99 restocking fee)",
                "credit": "Receive digital store credit code with 10% bonus (FREE)",
                "exchange": "Exchange for another size or variant (FREE)"
            }
            return [
                {
                    "id": m["method"],
                    "title": m["method"].capitalize(),
                    "description": method_desc.get(m["method"], "Return option")
                }
                for m in methods
            ]
        except Exception as e:
            logger.error(f"Error reading return methods: {e}")
            
    # Hardcoded fallback
    return [
        {"id": "refund", "title": "Refund", "description": "Refund to original payment card (-$5.99 restocking fee)"},
        {"id": "credit", "title": "Store Credit", "description": "Receive digital store credit code with 10% bonus (FREE)"},
        {"id": "exchange", "title": "Exchange", "description": "Exchange for another size or variant (FREE)"}
    ]

@router.get("/return-reasons")
async def get_return_reasons():
    """Fetches return reasons configuration from MongoDB."""
    if db.return_reasons is not None:
        try:
            cursor = db.return_reasons.find({})
            reasons = await cursor.to_list(length=20)
            return [r["reason"] for r in reasons]
        except Exception as e:
            logger.error(f"Error reading return reasons: {e}")

    # Fallback reasons
    return [
        "Damaged Product",
        "Wrong Item",
        "Size Didn't Fit",
        "Changed Mind",
        "Product Defective",
        "Order Misplaced"
    ]

@router.post("/returns/calculate", response_model=ReturnCalculateResponse)
async def calculate_return(payload: ReturnCalculateRequest):
    order = await ShopifyService.verify_order(payload.order_number, payload.email)
    if not order:
        raise HTTPException(status_code=404, detail="Order details unavailable for calculations.")
    
    # Format inputs
    items_list = [{"item_id": item.item_id, "quantity": item.quantity} for item in payload.items]
    summary = await ReturnCalculationService.calculate(payload.method, items_list, order.get("line_items", []))
    
    return ReturnCalculateResponse(
        subtotal=summary["subtotal"],
        handling_fee=summary["restocking_fee"] if payload.method == "refund" else 0.00,
        total_refund_amount=summary["total"],
        method=payload.method
    )

@router.post("/returns/create", response_model=ReturnCreateResponse)
async def create_return_request(payload: ReturnCreateRequest):
    # 1. Verify order details
    order = await ShopifyService.verify_order(payload.order_number, payload.email)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or email does not match.")

    order_items = order.get("line_items", [])
    order_items_map = {item["id"]: item for item in order_items}

    # Retrieve configurable validation reasons from MongoDB
    reasons_config = {}
    if db.return_reasons is not None:
        try:
            cursor = db.return_reasons.find({})
            db_reasons = await cursor.to_list(length=20)
            reasons_config = {r["reason"]: r for r in db_reasons}
        except Exception as e:
            logger.error(f"Failed to fetch reasons configuration: {e}")

    # 2. Iterate and validate business rules for each item
    for request_item in payload.items:
        orig_item = order_items_map.get(request_item.item_id)
        if not orig_item:
            raise HTTPException(
                status_code=400,
                detail=f"Product ID {request_item.item_id} does not belong to this order."
            )
        
        # Quantity cap check
        if request_item.quantity > orig_item["quantity"]:
            raise HTTPException(
                status_code=400,
                detail="Return quantity cannot exceed purchased quantity."
            )

        # Dynamic Reason Config rules checks
        rule = reasons_config.get(request_item.reason)
        if rule:
            # Notes validation check
            if rule.get("requires_notes") and (not request_item.notes or len(request_item.notes.strip()) < 5):
                raise HTTPException(
                    status_code=400,
                    detail="Notes are required for this return reason."
                )
            # Image validation check
            if rule.get("requires_image") and not request_item.image_file_id:
                raise HTTPException(
                    status_code=400,
                    detail="Image is required for damaged product returns."
                )
            # Additional validation details (e.g. Order Misplaced requires additional explanation)
            if rule.get("requires_additional_reason") and (not request_item.notes or len(request_item.notes.strip()) < 10):
                raise HTTPException(
                    status_code=400,
                    detail="Detailed additional reason description is required for misplaced orders."
                )

        # Exchange validation check
        if payload.method == "exchange":
            if not request_item.exchange_variant or not request_item.exchange_variant.get("color"):
                raise HTTPException(
                    status_code=400,
                    detail="Exchange option requires specifying a target variant size or color."
                )
            
            # Look up variants of this product using Shopify Admin API
            try:
                # Retrieve matching variant list
                prod_id = orig_item.get("product_id")
                if prod_id:
                    variants = await ShopifyService.get_product_variants(str(prod_id))
                    # The color field holds the selected variant_id. Match variant_id in the variants list.
                    target_var_id = request_item.exchange_variant.get("color")
                    matched_var = next((v for v in variants if str(v.get("id")) == str(target_var_id)), None)
                    if not matched_var:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid or unavailable exchange variant."
                        )
                    # Check stock if inventory is provided
                    if "inventory_quantity" in matched_var and matched_var["inventory_quantity"] <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid or unavailable exchange variant."
                        )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to check exchange variant availability: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Invalid or unavailable exchange variant."
                )

    # 3. Persistence inside return_requests and return_items collections
    return_id = f"RET-{random.randint(100000, 999999)}"
    now_str = datetime.datetime.utcnow().isoformat()

    # Generate labels
    label_info = await ShippingLabelService.generate_mock_label(return_id)

    return_request_doc = {
        "return_id": return_id,
        "order_number": payload.order_number,
        "email": payload.email,
        "method": payload.method,
        "subtotal": payload.subtotal,
        "handling_fee": payload.handling_fee,
        "total_amount": payload.total_amount,
        "status": "Created",
        "created_at": now_str,
        "updated_at": now_str
    }

    if db.return_requests is not None:
        try:
            # Insert request header
            await db.return_requests.insert_one(return_request_doc.copy())
            
            # Insert item lines
            for item in payload.items:
                await db.return_items.insert_one({
                    "return_request_id": return_id,
                    "product_id": item.item_id,
                    "quantity": item.quantity,
                    "reason": item.reason,
                    "notes": item.notes,
                    "image_file_id": item.image_file_id
                })

            # Audit log
            await db.audit_logs.insert_one({
                "event": "RETURN_CREATED",
                "return_id": return_id,
                "timestamp": now_str,
                "details": f"Created return request {return_id} with method {payload.method}"
            })
        except Exception as e:
            logger.error(f"Failed to write return request details: {e}")
            raise HTTPException(status_code=500, detail="Database write failure.")

    return ReturnCreateResponse(
        success=True,
        return_id=return_id,
        status="Created",
        tracking_number=label_info["tracking_number"],
        carrier=label_info["carrier"],
        shipping_label_url=label_info["shipping_label_url"],
        created_at=now_str
    )

@router.get("/returns/{return_id}", response_model=ReturnDetailResponse)
async def get_return_request(return_id: str):
    if db.return_requests is not None:
        try:
            ret = await db.return_requests.find_one({"return_id": return_id})
            if ret:
                # Retrieve item lines
                items_cursor = db.return_items.find({"return_request_id": return_id})
                db_items = await items_cursor.to_list(length=100)
                
                items = [
                    {
                        "item_id": i["product_id"],
                        "quantity": i["quantity"],
                        "reason": i["reason"],
                        "notes": i.get("notes"),
                        "image_file_id": i.get("image_file_id")
                    }
                    for i in db_items
                ]

                return ReturnDetailResponse(
                    return_id=ret["return_id"],
                    order_number=ret["order_number"],
                    email=ret["email"],
                    method=ret["method"],
                    items=items,
                    subtotal=ret["subtotal"],
                    handling_fee=ret["handling_fee"],
                    total_amount=ret["total_amount"],
                    status=ret["status"],
                    tracking_number="9400100000000000000000",  # Default or loaded
                    carrier="USPS",
                    created_at=ret["created_at"]
                )
        except Exception as e:
            logger.error(f"Failed to fetch return detailed view: {e}")
            
    raise HTTPException(status_code=404, detail="Return request not found.")

@router.get("/returns/{return_id}/status")
async def get_return_status(return_id: str):
    """Retrieves current return status details."""
    status_info = await StatusService.get_return_status(return_id)
    if not status_info:
        raise HTTPException(status_code=404, detail=f"Return request {return_id} not found.")
    return status_info

@router.get("/products/{product_id}/variants")
async def get_product_variants(product_id: str):
    """Fetch available variants for a product ID."""
    variants = await ShopifyService.get_product_variants(product_id)
    normalized = []
    for var in variants:
        # options
        opt1 = var.get("option1")
        opt2 = var.get("option2")
        title = var.get("title", "")
        price = float(var.get("price", 0.0))
        available = var.get("inventory_quantity", 0) > 0 if "inventory_quantity" in var else True

        normalized.append({
            "variant_id": str(var["id"]),
            "title": title,
            "option1": opt1,
            "option2": opt2,
            "price": price,
            "available": available
        })
    return {
        "success": True,
        "variants": normalized
    }

@router.get("/orders/{order_id}/fulfillment")
async def get_order_fulfillment(order_id: str):
    """Fetch fulfillment status of an order."""
    status_val = await ShopifyService.get_fulfillment_status(order_id)
    return {
        "success": True,
        "fulfillment_status": status_val or "unfulfilled"
    }

