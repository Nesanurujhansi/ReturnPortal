# Return Portal API Test Guide

This testing guide provides step-by-step diagnostic procedures for importing and running the complete Postman testing suite against your local Return Portal backend API.

---

## 1. Environment & Variables

Import `postman/return_portal_environment.json` first. The environment defines the following variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `base_url` | `http://localhost:8000` | The backend FastAPI port path. |
| `order_id` | `1001` | Sample order number. |
| `customer_email` | `customer@example.com` | Verified purchaser email. |
| `return_id` | `RET-XXXXXX` | Auto-populated by create return tests. |
| `file_id` | `XXXXXX` | Auto-populated by GridFS image upload tests. |
| `shopify_store_url`| `your-store.myshopify.com` | Simulated store endpoint url. |
| `shopify_access_token`| `shpat_xxxxxxxxxxxxxxxxxxxxxxxx` | Authentication token. |

---

## 2. Recommended Sequential Test Checklist

Run the requests inside the collection folder in the following sequence:

### Step 1: Diagnostic Health Check
- **Request**: `GET /api/health`
- **Verification**: Assures that FastAPI is up and MongoDB is connected (returns `healthy`).

### Step 2: Verify Order
- **Request**: `POST /api/orders/verify`
- **Request Body**:
  ```json
  {
    "order_number": "1001",
    "email": "customer@example.com"
  }
  ```
- **Verification**: Tests order exists and matches email.

### Step 3: Fetch Order Details & Items
- **Request**: `GET /api/orders/{order_id}`
  - Fetches order status, total price, and customer mappings.
- **Request**: `GET /api/orders/{order_id}/items`
  - Fetches line items that can be returned.

### Step 4: Upload Verification Image (GridFS)
- **Request**: `POST /api/uploads/return-image`
- **Form-Data**:
  - `file`: Choose a local image file (under 5MB).
  - `order_id`: `1001`
  - `product_id`: `item_01`
  - `reason`: `Defective / Damaged`
- **Verification**: Check it returns `success: true` and a `file_id`. The collection script will automatically save this value to the environment.

### Step 5: Retrieve Image
- **Request**: `GET /api/uploads/{file_id}`
- **Verification**: Downloads the raw binary stream back from GridFS with correct content type.

### Step 6: Calculate Refund Total
- **Request**: `POST /api/returns/calculate`
- **Request Body**:
  ```json
  {
    "order_number": "1001",
    "email": "customer@example.com",
    "method": "refund",
    "items": [
      {
        "item_id": "item_01",
        "quantity": 1,
        "reason": "Too Large"
      }
    ]
  }
  ```
- **Verification**: Calculates taxes, fees ($5.99 for Refund, $0.00 for Credit/Exchange) and returns subtotal calculations.

### Step 7: Create Return Request
- **Request**: `POST /api/returns/create`
- **Request Body**:
  ```json
  {
    "order_number": "1001",
    "email": "customer@example.com",
    "method": "refund",
    "items": [
      {
        "item_id": "item_01",
        "quantity": 1,
        "reason": "Too Large",
        "notes": "Length is too large around arms.",
        "image_file_id": null
      }
    ],
    "subtotal": 89.00,
    "handling_fee": 5.99,
    "total_amount": 83.01
  }
  ```
- **Verification**: Registers the return in the MongoDB database, generates a `return_id`, and saves it to the environment.

### Step 8: Retrieve Return Details
- **Request**: `GET /api/returns/{return_id}`
- **Verification**: Queries database to confirm return request record has persisted.

### Step 9: Cleanup Image (Delete)
- **Request**: `DELETE /api/uploads/{file_id}`
- **Verification**: Deletes file binary from GridFS and cleans up returns metadata.

---

## 3. Validation Error Cases Tested

The folder `Validation Error Tests` contains negative test cases to check robust error handling:

1. **Verify Order - Invalid Order ID**:
   - `POST /api/orders/verify` with order ID `9999` returns `404 Not Found`.
2. **Verify Order - Invalid Email**:
   - `POST /api/orders/verify` with incorrect email returns `404 Not Found`.
3. **Create Return - Quantity Exceeds Purchased**:
   - `POST /api/returns/create` with return quantity `15` returns `400 Bad Request`.
4. **Create Return - Damaged Product Missing Image**:
   - `POST /api/returns/create` with reason `Defective / Damaged` but no `image_file_id` returns `400 Bad Request`.
5. **Upload Media - Reject Unsupported File Type**:
   - `POST /api/uploads/return-image` with non-image file returns `400 Bad Request`.
