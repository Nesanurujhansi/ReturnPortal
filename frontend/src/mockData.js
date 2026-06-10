export const mockOrders = {
  "1001": {
    orderNumber: "1001",
    email: "customer@example.com",
    customerName: "Alex Mercer",
    items: [
      {
        id: "item_01",
        name: "Classic Denim Jacket",
        price: 89.00,
        quantity: 1,
        variant: "Indigo / Medium",
        image: "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?auto=format&fit=crop&q=80&w=300",
        exchangeOptions: {
          sizes: ["Small", "Medium", "Large", "X-Large"],
          colors: ["Indigo", "Black Denim", "Light Wash"]
        }
      },
      {
        id: "item_02",
        name: "Premium Cotton Tee",
        price: 29.00,
        quantity: 2,
        variant: "Heather Gray / Medium",
        image: "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?auto=format&fit=crop&q=80&w=300",
        exchangeOptions: {
          sizes: ["Small", "Medium", "Large"],
          colors: ["Heather Gray", "Off-White", "Midnight Black"]
        }
      }
    ]
  },
  "1002": {
    orderNumber: "1002",
    email: "hello@world.com",
    customerName: "Sarah Connor",
    items: [
      {
        id: "item_03",
        name: "Minimalist Leather Sneakers",
        price: 120.00,
        quantity: 1,
        variant: "White / US 9",
        image: "https://images.unsplash.com/photo-1549298916-b41d501d3772?auto=format&fit=crop&q=80&w=300",
        exchangeOptions: {
          sizes: ["US 8", "US 9", "US 10", "US 11"],
          colors: ["White", "Black", "Tan"]
        }
      }
    ]
  }
};
