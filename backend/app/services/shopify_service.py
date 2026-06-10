import httpx
import logging
from typing import Optional, Dict, Any, List
from app.config import settings

logger = logging.getLogger("app.shopify")

# Simulated live Shopify orders for local testing when Shopify is not connected
MOCK_SHOPIFY_DATABASE = {
    "1001": {
        "id": 4507894982782,
        "name": "#1001",
        "email": "customer@example.com",
        "customer": {"id": 607182902, "first_name": "Alex", "last_name": "Mercer"},
        "fulfillment_status": "fulfilled",
        "line_items": [
            {
                "id": "item_01",
                "title": "Classic Denim Jacket",
                "price": "89.00",
                "quantity": 1,
                "variant_title": "Indigo / Medium",
                "product_id": 7891230,
                "variant_id": 9923842,
                "sku": "JKT-DEN-001",
                "tax_lines": [{"price": "7.12"}]
            },
            {
                "id": "item_02",
                "title": "Premium Cotton Tee",
                "price": "29.00",
                "quantity": 2,
                "variant_title": "Heather Gray / Medium",
                "product_id": 7891231,
                "variant_id": 9923843,
                "sku": "TEE-COT-002",
                "tax_lines": [{"price": "2.32"}]
            }
        ],
        "refunds": []
    },
    "1002": {
        "id": 4507894982783,
        "name": "#1002",
        "email": "hello@world.com",
        "customer": {"id": 607182903, "first_name": "Sarah", "last_name": "Connor"},
        "fulfillment_status": "fulfilled",
        "line_items": [
            {
                "id": "item_03",
                "title": "Minimalist Leather Sneakers",
                "price": "120.00",
                "quantity": 1,
                "variant_title": "White / US 9",
                "product_id": 7891232,
                "variant_id": 9923844,
                "sku": "SH-LTR-003",
                "tax_lines": [{"price": "9.60"}]
            }
        ],
        "refunds": []
    }
}

class ShopifyService:
    @staticmethod
    def _is_configured() -> bool:
        return (
            settings.SHOPIFY_STORE_URL != "your-store.myshopify.com" and 
            "xxxxxxxx" not in settings.SHOPIFY_ACCESS_TOKEN and
            settings.SHOPIFY_ACCESS_TOKEN != ""
        )

    @classmethod
    def _get_masked_token(cls) -> str:
        token = settings.SHOPIFY_ACCESS_TOKEN
        if not token:
            return "None"
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}...{token[-4:]}"

    @classmethod
    async def verify_order(cls, order_number: str, email: str) -> Optional[Dict[str, Any]]:
        """Search Shopify order by order number, verify customer email matches, and return order details."""
        clean_num = order_number.strip().replace("#", "")
        clean_email = email.strip().lower()

        if not cls._is_configured():
            logger.info("Shopify credentials not set; falling back to simulated shopify data.")
            mock_order = MOCK_SHOPIFY_DATABASE.get(clean_num)
            if mock_order and mock_order["email"].lower() == clean_email:
                return mock_order
            return None

        # Mask token in logs
        masked_token = cls._get_masked_token()
        logger.info(f"Querying Shopify for order #{clean_num} using token {masked_token}")

        url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/orders.json"
        headers = {
            "X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN,
            "Content-Type": "application/json"
        }
        params = {
            "name": f"#{clean_num}",
            "status": "any"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 429:
                    logger.warning("Shopify API Rate Limited (429).")
                    raise HTTPException(status_code=429, detail="Shopify service is busy. Please try again shortly.")
                
                response.raise_for_status()
                data = response.json()
                
                orders = data.get("orders", [])
                for order in orders:
                    # Match email
                    if order.get("email", "").lower() == clean_email:
                        return order
                return None
        except httpx.HTTPStatusError as e:
            logger.error(f"Shopify Admin API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Shopify Admin API returned status {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Shopify verify_order error: {e}")
            raise Exception(f"Failed to query Shopify order API: {str(e)}")

    @classmethod
    async def get_order_details(cls, order_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete order details from Shopify."""
        if not cls._is_configured():
            for mock_order in MOCK_SHOPIFY_DATABASE.values():
                if str(mock_order["id"]) == str(order_id) or mock_order["name"].replace("#", "") == str(order_id):
                    return mock_order
            return None

        url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/orders/{order_id}.json"
        headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    logger.warning("Shopify API Rate Limited (429).")
                    raise HTTPException(status_code=429, detail="Shopify service is busy. Please try again shortly.")
                response.raise_for_status()
                return response.json().get("order")
        except Exception as e:
            logger.error(f"Shopify get_order_details error: {e}")
            raise Exception(f"Failed to fetch Shopify order details: {str(e)}")

    @classmethod
    async def get_order_items(cls, order_id: str) -> List[Dict[str, Any]]:
        """Fetch line items from the order."""
        order = await cls.get_order_details(order_id)
        if not order:
            return []
        return order.get("line_items", [])

    @classmethod
    async def get_customer_details(cls, customer_id: str) -> Optional[Dict[str, Any]]:
        """Fetch customer details."""
        if not cls._is_configured():
            return {"id": customer_id, "first_name": "Mock", "last_name": "Customer", "email": "customer@example.com"}

        url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/customers/{customer_id}.json"
        headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    logger.warning("Shopify API Rate Limited (429).")
                    raise HTTPException(status_code=429, detail="Shopify service is busy. Please try again shortly.")
                response.raise_for_status()
                return response.json().get("customer")
        except Exception as e:
            logger.error(f"Shopify get_customer_details error: {e}")
            raise Exception(f"Failed to fetch Shopify customer: {str(e)}")

    @classmethod
    async def get_product_details(cls, product_id: str) -> Optional[Dict[str, Any]]:
        """Fetch product information."""
        if not cls._is_configured():
            return {
                "id": product_id,
                "title": "Mock Product",
                "images": [{"src": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?auto=format&fit=crop&q=80&w=300"}]
            }

        url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/products/{product_id}.json"
        headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    return None
                if response.status_code == 429:
                    logger.warning("Shopify API Rate Limited (429).")
                    raise HTTPException(status_code=429, detail="Shopify service is busy. Please try again shortly.")
                response.raise_for_status()
                return response.json().get("product")
        except Exception as e:
            logger.error(f"Shopify get_product_details error: {e}")
            raise Exception(f"Failed to fetch Shopify product: {str(e)}")

    @classmethod
    async def get_product_variants(cls, product_id: str) -> List[Dict[str, Any]]:
        """Fetch available variants for exchange workflow."""
        if not cls._is_configured():
            return [
                {"id": 9923842, "title": "Indigo / Medium", "option1": "Indigo", "option2": "Medium", "price": "89.00", "inventory_quantity": 5},
                {"id": 9923843, "title": "Black Denim / Large", "option1": "Black Denim", "option2": "Large", "price": "89.00", "inventory_quantity": 10}
            ]

        url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/products/{product_id}/variants.json"
        headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 429:
                    logger.warning("Shopify API Rate Limited (429).")
                    raise HTTPException(status_code=429, detail="Shopify service is busy. Please try again shortly.")
                response.raise_for_status()
                return response.json().get("variants", [])
        except Exception as e:
            logger.error(f"Shopify get_product_variants error: {e}")
            raise Exception(f"Failed to fetch Shopify variants: {str(e)}")

    @classmethod
    async def get_fulfillment_status(cls, order_id: str) -> Optional[str]:
        """Fetch fulfillment/shipment status."""
        order = await cls.get_order_details(order_id)
        if not order:
            return None
        return order.get("fulfillment_status")

    @classmethod
    async def get_refund_history(cls, order_id: str) -> List[Dict[str, Any]]:
        """Fetch refund information if available."""
        if not cls._is_configured():
            return []

        url = f"https://{settings.SHOPIFY_STORE_URL}/admin/api/{settings.SHOPIFY_API_VERSION}/orders/{order_id}/refunds.json"
        headers = {"X-Shopify-Access-Token": settings.SHOPIFY_ACCESS_TOKEN}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 404:
                    return []
                if response.status_code == 429:
                    logger.warning("Shopify API Rate Limited (429).")
                    raise HTTPException(status_code=429, detail="Shopify service is busy. Please try again shortly.")
                response.raise_for_status()
                return response.json().get("refunds", [])
        except Exception as e:
            logger.error(f"Shopify get_refund_history error: {e}")
            raise Exception(f"Failed to fetch Shopify refund history: {str(e)}")

