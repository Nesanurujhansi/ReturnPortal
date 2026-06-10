import { useState } from "react";

export default function StepProductSelection({ order, onNext, onBack, initialSelectedItems }) {
  const [selectedItems, setSelectedItems] = useState(
    initialSelectedItems || {} // Format: { item_id: quantity }
  );
  const [error, setError] = useState("");

  const handleCheckboxChange = (itemId, maxQty) => {
    setSelectedItems((prev) => {
      const updated = { ...prev };
      if (updated[itemId]) {
        delete updated[itemId];
      } else {
        updated[itemId] = 1;
      }
      return updated;
    });
    setError("");
  };

  const handleQuantityChange = (itemId, qty) => {
    setSelectedItems((prev) => ({
      ...prev,
      [itemId]: Number(qty)
    }));
  };

  const handleContinue = () => {
    if (Object.keys(selectedItems).length === 0) {
      setError("Please select at least one product to return.");
      return;
    }
    onNext(selectedItems);
  };

  return (
    <div className="card anim-fade-in">
      <h2>Select Products to Return</h2>
      <p className="subtitle">Choose the products and the quantity you want to send back.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="product-list">
        {order.items.map((item) => {
          const isChecked = !!selectedItems[item.id];
          return (
            <div key={item.id} className={`product-card ${isChecked ? "selected" : ""}`}>
              <div className="product-left">
                <input
                  type="checkbox"
                  checked={isChecked}
                  onChange={() => handleCheckboxChange(item.id, item.quantity)}
                  className="product-checkbox"
                />
                <img src={item.image} alt={item.name} className="product-thumb" />
                <div className="product-info">
                  <h4>{item.name}</h4>
                  <p className="product-variant">{item.variant}</p>
                  <p className="product-price">${item.price.toFixed(2)}</p>
                </div>
              </div>

              {isChecked && (
                <div className="product-quantity-selector">
                  <label htmlFor={`qty-${item.id}`}>Qty:</label>
                  <select
                    id={`qty-${item.id}`}
                    value={selectedItems[item.id]}
                    onChange={(e) => handleQuantityChange(item.id, e.target.value)}
                  >
                    {[...Array(item.quantity).keys()].map((n) => (
                      <option key={n + 1} value={n + 1}>
                        {n + 1}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="actions-bar">
        <button onClick={onBack} className="btn btn-secondary">
          Back
        </button>
        <button onClick={handleContinue} className="btn btn-primary">
          Continue
        </button>
      </div>
    </div>
  );
}
