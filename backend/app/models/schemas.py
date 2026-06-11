from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict

class OrderVerifyRequest(BaseModel):
    order_number: str = Field(..., description="E-commerce order ID, e.g. 1001")
    email: EmailStr = Field(..., description="Customer billing/contact email")

class ItemDetail(BaseModel):
    id: str
    name: str
    price: float
    quantity: int
    variant: str
    image: Optional[str] = None
    exchangeOptions: Optional[Dict[str, List[str]]] = None

class OrderVerifyResponse(BaseModel):
    success: bool
    order_number: str
    email: str
    customer_name: str
    items: List[ItemDetail]

class ReturnItemSelection(BaseModel):
    item_id: str
    quantity: int = Field(..., ge=1)
    reason: str
    notes: Optional[str] = None
    image_file_id: Optional[str] = None  # GridFS file_id
    exchange_variant: Optional[Dict[str, str]] = None  # e.g., {"size": "Large", "color": "Black"}

class ReturnCalculateRequest(BaseModel):
    order_number: str
    email: EmailStr
    method: str  # refund, credit, exchange
    items: List[ReturnItemSelection]

class ReturnCalculateResponse(BaseModel):
    subtotal: float
    handling_fee: float
    total_refund_amount: float
    method: str

class ReturnCreateRequest(BaseModel):
    order_number: str
    email: EmailStr
    method: str
    items: List[ReturnItemSelection]
    subtotal: float
    handling_fee: float
    total_amount: float

class ReturnCreateResponse(BaseModel):
    success: bool
    return_id: str
    status: str
    tracking_number: str
    carrier: str
    shipping_label_url: str
    created_at: str

class ReturnDetailResponse(BaseModel):
    return_id: str
    order_number: str
    email: str
    method: str
    items: List[ReturnItemSelection]
    subtotal: float
    handling_fee: float
    total_amount: float
    status: str
    tracking_number: str
    carrier: str
    shipping_label_url: Optional[str] = None
    created_at: str
