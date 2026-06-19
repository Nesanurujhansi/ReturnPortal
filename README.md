# Return Portal

A full-stack Return Portal designed to manage e-commerce returns, integrate with the Shopify Admin API, persist return configurations in MongoDB, store media uploads in GridFS, and prepare for future AI Agent workflows using LangChain and Gemini.

## Project Structure

```text
return-portal/
├── backend/                  # FastAPI Backend
│   ├── app/
│   │   ├── api/              # API endpoints / routers
│   │   ├── config.py         # App configuration & Environment loader
│   │   ├── database/         # MongoDB and GridFS connections
│   │   ├── main.py           # FastAPI entrypoint & structured request logging
│   │   ├── models/           # Pydantic and Database models
│   │   ├── services/         # Shopify API & Business logic services
│   │   └── utils/            # Helper functions
│   ├── .env.example          # Sample environment variables
│   └── requirements.txt      # Python dependencies
├── frontend/                 # React.js Frontend (Vite)
│   ├── src/                  # React source files
│   └── package.json          # Node dependencies
├── postman/                  # Postman Collections and environment variable setups
└── README.md                 # Setup guidelines
```

---

## Getting Started

### Prerequisites

- **Python**: version 3.10 or higher
- **Node.js**: version 18 or higher
- **MongoDB**: A running MongoDB instance locally or in the cloud (for database and GridFS storage).
  - Setup a local instance on `mongodb://localhost:27017` or update the `MONGODB_URI` env value.
  - The application automatically initializes the following database collections on startup:
    * `returns` - Single primary collection storing the complete return request details in a single document (order details, customer details, method, items, calculations, shipping tracking/PDF label IDs, status, and timestamps).
    * `audit_logs` - Action tracker for database adjustments.
    * `agent_conversations` - Conversational state logs.
  - **GridFS File Storage**: Actual uploaded image files (for damaged/defective products) and generated PDF shipping labels are stored inside GridFS binary buckets (`fs.files` and `fs.chunks`). The return documents refer to these using `image_file_id` and `label_file_id`, ensuring no large binaries are stored directly inside the main `returns` collection.

---

### Backend Setup

1. **Navigate to the backend folder**:
   ```bash
   cd backend
   ```

2. **Create a Python Virtual Environment**:
   ```bash
   python -m venv .venv
   ```

3. **Activate the Virtual Environment**:
   - **Windows (PowerShell)**:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Windows (CMD)**:
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **macOS/Linux**:
     ```bash
     source .venv/bin/activate
     ```

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables**:
   - Create `.env` from `.env.example`:
     ```bash
     cp .env.example .env
     ```
   - Make sure to add your Shopify Admin API keys:
     ```env
     SHOPIFY_STORE_URL=your-store.myshopify.com
     SHOPIFY_ACCESS_TOKEN=shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     SHOPIFY_API_VERSION=2024-04
     ```

6. **Run the Backend Server**:
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be running at [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive Swagger API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### Frontend Setup

1. **Navigate to the frontend folder**:
   ```bash
   cd frontend
   ```

2. **Install Node Modules**:
   ```bash
   npm install
   ```

3. **Start the Development Server**:
   ```bash
   npm run dev
   ```
   The frontend application will be active at [http://localhost:5173](http://localhost:5173).

---

## Tech Stack & Architecture Highlights

- **FastAPI**: Lightweight, asynchronous web framework built on modern Python standards.
- **React (Vite)**: Frontend framework with smooth layouts, loading indicators, and validation rules.
- **MongoDB GridFS**: Setup for chunked storage of large return slip images or return-related media files up to 5MB.
- **Shopify Admin API**: Asynchronous service integration fetching live e-commerce order details, variants, inventory levels, and fulfillment states. Includes token masking to protect secrets.
- **Gemini + LangChain**: Environment variable scaffolding ready to import LLM agents during the next phase.

---

## API Testing with Postman

We have included a Postman Collection and Environment configuration in the `postman/` directory to facilitate quick testing of all return portal APIs.

### Setup and Import Instructions

1. **Open Postman** (Desktop app or Web interface).
2. **Import Collection**:
   - Click **Import** in the top-left corner.
   - Choose the file: `postman/return_portal_api_collection.json`.
3. **Import Environment**:
   - Click **Import** again.
   - Choose the file: `postman/return_portal_environment.json`.
4. **Select Environment**:
   - In the top-right environment selector dropdown, select **Return Portal Environment**.
   - Make sure your FastAPI backend is running on `http://localhost:8000`.

---

### Step-by-Step API Testing Order

To validate the full e-commerce returns pipeline correctly, execute the Postman requests in the following sequence:

#### Step 1: Health Check
- **API**: `GET /api/health`
- **Purpose**: Verify backend and database status.

#### Step 2: Order Verification
- **API**: `POST /api/orders/verify`
- **Payload**:
  ```json
  {
    "order_number": "1001",
    "email": "customer@example.com"
  }
  ```
- **Purpose**: Verifies that the order exists and email matches. Sets up validation parameters.

#### Step 3: Get Order Items
- **API**: `GET /api/orders/{order_id}/items`
- **Purpose**: Fetches normalized product information (product_id, variant_id, sku, price, tax, etc.) from Shopify line items.

#### Step 4: Fetch Product Variants
- **API**: `GET /api/products/{product_id}/variants`
- **Purpose**: Retrieve variant listings (price, stock, titles) of product to exchange.

#### Step 5: Upload Verification Image (MongoDB GridFS)
- **API**: `POST /api/uploads/return-image`
- **Form Data**:
  - `file`: Choose an image file (PNG, JPG, JPEG, WEBP) under 5MB.
  - `order_id`: Order ID reference string (e.g., `1001`).
  - `product_id`: Product ID reference (e.g., `item_01`).
  - `reason`: Customer reason tag (e.g., `Defective / Damaged`).
- **Purpose**: Validates file size (max 5MB) and type constraints, uploads binary to GridFS, and returns the `file_id`.

#### Step 6: Retrieve Image Binary
- **API**: `GET /api/uploads/{file_id}`
- **Purpose**: Verifies that the image retrieves correctly from GridFS bucket as a streaming response.

#### Step 7: Calculate Refund/Exchange Total
- **API**: `POST /api/returns/calculate`
- **Payload**:
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
- **Purpose**: Assesses handling fees ($5.99 for Refund, $0.00 for Store Credit/Exchange) and returns totals.

#### Step 8: Create Return Request
- **API**: `POST /api/returns/create`
- **Purpose**: Submits request details to database and sets up USPS carrier tracking.

#### Step 9: Get Return Details & Status
- **API**: `GET /api/returns/{return_id}` and `GET /api/returns/{return_id}/status`
- **Purpose**: Retrieve return header records and see return workflow progress indicators.

---

## Known Limitations & Production Notes

- **Fulfillment checks**: Currently verification APIs allow return operations on orders where fulfillment status is `fulfilled` or mock equivalent.
- **USPS Labels generation**: The shipping labels integration provides mock PDFs. Real integrations (e.g., EasyPost/ShipStation) will replace this mock service.
- **Shopify Mock Database**: In development/diagnostic checks, if Shopify configurations are missing, the system automatically falls back to `MOCK_SHOPIFY_DATABASE` orders `#1001` and `#1002`.

---

## Example Returns Document (Single-Collection Design)

The complete return request payload, customer/order mappings, calculation summaries, and GridFS label/image references are stored as a single document in the `returns` collection:

```json
{
  "_id": "60d5ec4b1234567890abcdef",
  "return_id": "RET-123456",
  "order_details": {
    "order_id": "123456789",
    "order_number": "1368",
    "fulfillment_status": "fulfilled"
  },
  "customer_details": {
    "name": "Baranivasan",
    "email": "baranivasan@lateshipment.co"
  },
  "return_method": "refund",
  "items": [
    {
      "item_id": "987654321",
      "quantity": 1,
      "reason": "Damaged Product",
      "notes": "The item arrived with a broken zipper.",
      "image_file_id": "60d5ec4b1234567890abc111",
      "exchange_variant": null
    }
  ],
  "subtotal": 20.50,
  "handling_fee": 5.99,
  "total_amount": 14.51,
  "shipping": {
    "label_number": "RET-2026-12345",
    "tracking_number": "9400100000001234567890",
    "carrier": "USPS",
    "label_file_id": "60d5ec4b1234567890abc222",
    "shipping_label_url": "http://localhost:8000/api/uploads/60d5ec4b1234567890abc222"
  },
  "status": "Created",
  "created_at": "2026-06-19T10:00:00.000Z",
  "updated_at": "2026-06-19T10:00:00.000Z"
}
```

---

## Next Phase: LangChain + Gemini Return Agent

In Phase 9, we will bootstrap an AI Return Assistant that:
- Reads chat logs from `agent_conversations` collection.
- Translates customer queries using Gemini LLMs.
- Automates order status queries, checks rules validations, and manages exceptions dynamically.

