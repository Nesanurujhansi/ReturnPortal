const BASE_URL = "http://localhost:8000/api";

export async function verifyOrder(orderNumber, email) {
  const response = await fetch(`${BASE_URL}/orders/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ order_number: orderNumber, email })
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Verification failed");
  }
  return response.json();
}

export async function getReturnMethods() {
  const response = await fetch(`${BASE_URL}/return-methods`);
  if (!response.ok) throw new Error("Failed to fetch return methods");
  return response.json();
}

export async function getReturnReasons() {
  const response = await fetch(`${BASE_URL}/return-reasons`);
  if (!response.ok) throw new Error("Failed to fetch return reasons");
  return response.json();
}

export async function calculateReturn(method, items, orderNumber, email) {
  const formattedItems = Object.entries(items).map(([itemId, qty]) => ({
    item_id: itemId,
    quantity: qty,
    reason: "Standard Return"
  }));

  const response = await fetch(`${BASE_URL}/returns/calculate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      order_number: orderNumber,
      email: email,
      method,
      items: formattedItems
    })
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Calculation failed");
  }
  return response.json();
}

export async function submitReturn(payload) {
  const response = await fetch(`${BASE_URL}/returns/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Submission failed");
  }
  return response.json();
}

export async function uploadImage(file, orderId, productId, reason) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("order_id", orderId);
  formData.append("product_id", productId);
  formData.append("reason", reason);

  const response = await fetch(`${BASE_URL}/uploads/return-image`, {
    method: "POST",
    body: formData
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Image upload failed");
  }
  return response.json(); // returns { success, file_id, filename, content_type, message }
}

export async function chatWithAgent(sessionId, history, message) {
  const response = await fetch(`${BASE_URL}/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      history: history.map(h => ({ role: h.role, content: h.content })),
      message
    })
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || "Agent chat failed");
  }
  return response.json();
}

export async function getAgentSession(sessionId) {
  const response = await fetch(`${BASE_URL}/agent/session/${sessionId}`);
  if (!response.ok) throw new Error("Failed to fetch session metadata");
  return response.json();
}

export async function clearAgentSession(sessionId) {
  const response = await fetch(`${BASE_URL}/agent/session/${sessionId}`, {
    method: "DELETE"
  });
  if (!response.ok) throw new Error("Failed to clear session");
  return response.json();
}

export async function getProductVariants(productId) {
  const response = await fetch(`${BASE_URL}/products/${productId}/variants`);
  if (!response.ok) throw new Error("Failed to fetch product variants");
  return response.json();
}

export async function getOrderFulfillment(orderId) {
  const response = await fetch(`${BASE_URL}/orders/${orderId}/fulfillment`);
  if (!response.ok) throw new Error("Failed to fetch order fulfillment status");
  return response.json();
}


