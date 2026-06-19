import asyncio
from app.database.mongodb import db, connect_to_mongo

async def main():
    await connect_to_mongo()
    print("Database connected:", db.db is not None)
    
    if db.returns is not None:
        # 1. Search returns collection
        cursor = db.returns.find({"order_details.order_number": "1368"})
        requests = await cursor.to_list(length=100)
        print(f"\n--- Found {len(requests)} Return Request(s) in 'returns' collection ---")
        for r in requests:
            print(f"Return ID: {r.get('return_id')}")
            print(f"  Order: {r.get('order_details', {}).get('order_number')}")
            print(f"  Email: {r.get('customer_details', {}).get('email')}")
            print(f"  Method: {r.get('return_method')}")
            print(f"  Status: {r.get('status')}")
            print(f"  Total Amount: {r.get('total_amount')}")
            print(f"  Created At: {r.get('created_at')}")
            
            # 2. Print items
            print("  Items Returned:")
            for item in r.get("items", []):
                print(f"    - Item ID: {item.get('item_id')}, Qty: {item.get('quantity')}, Reason: {item.get('reason')}, Image File ID: {item.get('image_file_id')}")
                
            # 3. Print shipping
            shipping = r.get("shipping", {})
            print(f"  Shipping label file ID: {shipping.get('label_file_id')}")
            print(f"  Tracking: {shipping.get('tracking_number')}, Carrier: {shipping.get('carrier')}")
            print(f"  Label URL: {shipping.get('shipping_label_url')}")
    else:
        print("db.returns is not initialized.")
            
if __name__ == "__main__":
    asyncio.run(main())
