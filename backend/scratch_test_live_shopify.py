import asyncio
import httpx
import json
from app.config import settings

async def main():
    store_url = settings.SHOPIFY_STORE_URL
    token = settings.SHOPIFY_ACCESS_TOKEN
    version = settings.SHOPIFY_API_VERSION
    
    order_id = "7140199760048"
    email = "baranivasan@lateshipment.co"
    
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json"
    }
    
    print(f"Testing Shopify Admin API endpoints for Store: {store_url}, API Version: {version}")
    print("="*80)
    
    # 1. Fetch Order Details
    order_url = f"https://{store_url}/admin/api/{version}/orders/{order_id}.json"
    print(f"\n[1] GET Order Details URL: {order_url}")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(order_url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                order_data = resp.json().get("order", {})
                print("Order Information retrieved:")
                print(f"  Name/Order Number: {order_data.get('name')}")
                print(f"  Email: {order_data.get('email')}")
                print(f"  Fulfillment Status: {order_data.get('fulfillment_status')}")
                print(f"  Financial Status: {order_data.get('financial_status')}")
                print(f"  Total Price: {order_data.get('total_price')} {order_data.get('currency')}")
                print(f"  Created At: {order_data.get('created_at')}")
                
                # Print Customer Name
                customer = order_data.get("customer", {})
                print(f"  Customer Name: {customer.get('first_name')} {customer.get('last_name')}")
                
                # 2. Print Line Items
                print("\n[2] Line Items details:")
                for item in order_data.get("line_items", []):
                    print(f"  - ID: {item.get('id')}")
                    print(f"    Title: {item.get('title')}")
                    print(f"    Price: {item.get('price')}")
                    print(f"    Quantity: {item.get('quantity')}")
                    print(f"    Variant ID: {item.get('variant_id')}")
                    print(f"    Variant Title: {item.get('variant_title')}")
                    print(f"    Product ID: {item.get('product_id')}")
                    print(f"    SKU: {item.get('sku')}")
            else:
                print(f"Error payload: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")
            
    # 2. Fetch Order Fulfillments
    fulfillment_url = f"https://{store_url}/admin/api/{version}/orders/{order_id}/fulfillments.json"
    print(f"\n[3] GET Fulfillments URL: {fulfillment_url}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(fulfillment_url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                fulfillments = resp.json().get("fulfillments", [])
                print(f"Fulfillments retrieved ({len(fulfillments)}):")
                for f in fulfillments:
                    print(f"  - ID: {f.get('id')}")
                    print(f"    Status: {f.get('status')}")
                    print(f"    Tracking Company: {f.get('tracking_company')}")
                    print(f"    Tracking Number: {f.get('tracking_number')}")
                    print(f"    Tracking URL: {f.get('tracking_url')}")
            else:
                print(f"Error payload: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")
            
    # 3. Fetch Order Refund History
    refund_url = f"https://{store_url}/admin/api/{version}/orders/{order_id}/refunds.json"
    print(f"\n[4] GET Refund History URL: {refund_url}")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(refund_url, headers=headers)
            print(f"Status Code: {resp.status_code}")
            if resp.status_code == 200:
                refunds = resp.json().get("refunds", [])
                print(f"Refunds retrieved ({len(refunds)}):")
                for r in refunds:
                    print(f"  - ID: {r.get('id')}")
                    print(f"    Created At: {r.get('created_at')}")
                    print(f"    Note: {r.get('note')}")
                    print("    Refund Line Items:")
                    for ri in r.get("refund_line_items", []):
                        print(f"      - Line Item ID: {ri.get('line_item_id')}, Quantity: {ri.get('quantity')}, Subtotal: {ri.get('subtotal')}")
            else:
                print(f"Error payload: {resp.text}")
        except Exception as e:
            print(f"Request failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
