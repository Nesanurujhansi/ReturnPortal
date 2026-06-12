import { verifyOrder, getProductVariants, getOrderFulfillment } from "../api.js";

// Ensure global.fetch is mocked or we can use the native global.fetch in Node 18+
// Node 18+ includes native fetch. If Jest environment is 'node', it will use it.

describe("Shopify API Integration Tests (via Backend Endpoints)", () => {
  
  // Real-world Edge Case 1: Order Verification Success (Order #1001)
  test("should successfully verify order #1001 and match customer email", async () => {
    const orderNumber = "1001";
    const email = "customer@example.com";
    
    const data = await verifyOrder(orderNumber, email);
    console.log("Response payload for Order #1001 verification:", JSON.stringify(data, null, 2));
    
    expect(data.success).toBe(true);
    expect(data.order_number).toBe("1001");
    expect(data.customer_name).toBe("Alex Mercer");
    expect(data.email).toBe("customer@example.com");
  });

  // Real-world Edge Case 2: Order Verification Success (Order #1002)
  test("should successfully verify order #1002 and match customer email", async () => {
    const orderNumber = "1002";
    const email = "hello@world.com";
    
    const data = await verifyOrder(orderNumber, email);
    console.log("Response payload for Order #1002 verification:", JSON.stringify(data, null, 2));
    
    expect(data.success).toBe(true);
    expect(data.order_number).toBe("1002");
    expect(data.customer_name).toBe("Sarah Connor");
    expect(data.email).toBe("hello@world.com");
  });

  // Real-world Edge Case 3: Order Not Found / Email Mismatch
  test("should fail verification if order number does not exist or email mismatches", async () => {
    const orderNumber = "9999";
    const email = "wrong@example.com";
    
    await expect(verifyOrder(orderNumber, email)).rejects.toThrow("Order not found or email mismatch");
  });

  // Real-world Edge Case 4: Fetch Product Variants for Exchange
  test("should retrieve available product variants for exchange workflow", async () => {
    const productId = "7891230"; // ID from Alex Mercer's Denim Jacket
    const data = await getProductVariants(productId);
    console.log("Response payload for Product variants:", JSON.stringify(data, null, 2));
    
    expect(data.success).toBe(true);
    expect(Array.isArray(data.variants)).toBe(true);
    expect(data.variants.length).toBeGreaterThan(0);
    expect(data.variants[0]).toHaveProperty("variant_id");
    expect(data.variants[0]).toHaveProperty("title");
  });

  // Real-world Edge Case 5: Fetch Order Fulfillment Status
  test("should check order fulfillment status successfully", async () => {
    const orderId = "4507894982782"; // Shopify ID for Order 1001
    const data = await getOrderFulfillment(orderId);
    console.log("Response payload for order fulfillment:", JSON.stringify(data, null, 2));
    
    expect(data).toHaveProperty("success");
    expect(data).toHaveProperty("fulfillment_status");
    expect(data.fulfillment_status).toBe("fulfilled");
  });
});
