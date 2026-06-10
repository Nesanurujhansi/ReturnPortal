import logging
from typing import List, Dict, Any
from app.database.mongodb import db

logger = logging.getLogger("app.services.calculation")

# Default configurations to fall back on if settings collection is unreachable
DEFAULT_CONFIG = {
    "restocking_fee_percentage": 0.10,
    "store_credit_bonus_percentage": 0.10,
    "tax_percentage": 0.08
}

class ReturnCalculationService:
    @classmethod
    async def get_config(cls) -> Dict[str, float]:
        """Fetch config settings from MongoDB."""
        if db.settings_col is not None:
            try:
                config = await db.settings_col.find_one({"_id": "global_config"})
                if config:
                    return {
                        "restocking_fee_percentage": config.get("restocking_fee_percentage", 0.10),
                        "store_credit_bonus_percentage": config.get("store_credit_bonus_percentage", 0.10),
                        "tax_percentage": config.get("tax_percentage", 0.08)
                    }
            except Exception as e:
                logger.error(f"Failed to fetch global config from database: {e}")
        return DEFAULT_CONFIG

    @classmethod
    async def calculate(cls, method: str, items: List[Dict[str, Any]], order_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates refund, store credit, or exchange summaries.
        items: [{"item_id": "item_01", "quantity": 1}]
        """
        config = await cls.get_config()
        tax_pct = config["tax_percentage"]
        restock_pct = config["restocking_fee_percentage"]
        bonus_pct = config["store_credit_bonus_percentage"]

        # Build price lookup table from Shopify items
        price_lookup = {item["id"]: float(item["price"]) for item in order_items}
        
        subtotal = 0.0
        for selected_item in items:
            item_id = selected_item["item_id"]
            qty = selected_item["quantity"]
            price = price_lookup.get(item_id, 0.0)
            subtotal += price * qty

        tax = subtotal * tax_pct
        restocking_fee = 0.0
        bonus_credit = 0.0
        adjustments = 0.0
        total = 0.0

        if method == "refund":
            restocking_fee = subtotal * restock_pct
            total = subtotal + tax - restocking_fee
        elif method == "credit":
            bonus_credit = subtotal * bonus_pct
            total = subtotal + tax + bonus_credit - adjustments
        elif method == "exchange":
            total = subtotal  # Exchange matches exact value swaps

        return {
            "subtotal": round(subtotal, 2),
            "tax": round(tax, 2),
            "restocking_fee": round(restocking_fee, 2),
            "bonus_credit": round(bonus_credit, 2),
            "adjustments": round(adjustments, 2),
            "total": round(max(0.0, total), 2),
            "method": method
        }
