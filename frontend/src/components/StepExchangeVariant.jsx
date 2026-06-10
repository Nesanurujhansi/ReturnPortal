import { useState, useEffect } from "react";
import { getProductVariants } from "../api";

export default function StepExchangeVariant({ order, selectedItems, onNext, onBack, initialExchanges }) {
  const [variantsData, setVariantsData] = useState({}); // { itemId: List of variants }
  const [loading, setLoading] = useState(true);
  const [exchanges, setExchanges] = useState(initialExchanges || {});

  useEffect(() => {
    async function loadAllVariants() {
      const dataMap = {};
      const initialExch = { ...exchanges };

      for (const itemId of Object.keys(selectedItems)) {
        const item = order.items.find((i) => i.id === itemId);
        if (item) {
          // If product_id is not explicitly mock, fetch variants
          // In mock orders, line items might not have product_id, but our mock order verified route matches product_id to line item or mock DB order_items.
          // Let's assume we map variants if we query the product variants API
          try {
            // We use the item ID as a fallback if product_id is empty, but we can look it up.
            // Let's call our API with a mock or real product_id:
            const prodId = item.product_id || item.id || "default";
            const response = await getProductVariants(prodId);
            if (response && response.success && response.variants) {
              dataMap[itemId] = response.variants;
              
              // Set default initial exchange variant if not already set
              if (!initialExch[itemId]) {
                const firstAvail = response.variants[0];
                initialExch[itemId] = {
                  variant_id: firstAvail ? firstAvail.variant_id : "",
                  title: firstAvail ? firstAvail.title : "",
                  price: firstAvail ? firstAvail.price : 0.0
                };
              }
            }
          } catch (e) {
            console.error("Failed to load variants for item", itemId, e);
          }
        }
      }

      setVariantsData(dataMap);
      setExchanges(initialExch);
      setLoading(false);
    }

    loadAllVariants();
  }, [order, selectedItems]);

  const handleExchangeChange = (itemId, variantId, variantsList) => {
    const selectedVar = variantsList.find((v) => v.variant_id === variantId);
    setExchanges((prev) => ({
      ...prev,
      [itemId]: {
        variant_id: variantId,
        title: selectedVar ? selectedVar.title : "",
        price: selectedVar ? selectedVar.price : 0.0
      }
    }));
  };

  const handleContinue = () => {
    // Format exchange variant expected by API schemas
    const finalExchanges = {};
    for (const [itemId, exch] of Object.entries(exchanges)) {
      finalExchanges[itemId] = {
        size: exch.title || "",
        color: exch.variant_id || ""
      };
    }
    onNext(finalExchanges);
  };

  if (loading) {
    return (
      <div className="card anim-fade-in">
        <h2>Loading product variants...</h2>
      </div>
    );
  }

  return (
    <div className="card anim-fade-in">
      <h2>Select Exchange Variants</h2>
      <p className="subtitle">Choose the variant you would like in exchange.</p>

      <div className="exchange-list">
        {order.items
          .filter((item) => !!selectedItems[item.id])
          .map((item) => {
            const currentExchange = exchanges[item.id] || { variant_id: "", title: "", price: 0.0 };
            const options = variantsData[item.id] || [];

            return (
              <div key={item.id} className="exchange-item-card">
                <div className="exchange-item-header">
                  <img src={item.image} alt={item.name} className="product-thumb-sm" />
                  <div>
                    <h4>{item.name}</h4>
                    <p className="product-variant">Original: {item.variant}</p>
                  </div>
                </div>

                <div className="exchange-selectors">
                  {options.length > 0 ? (
                    <div className="field-group">
                      <label htmlFor={`exchange-variant-${item.id}`}>Available Variants</label>
                      <select
                        id={`exchange-variant-${item.id}`}
                        value={currentExchange.variant_id}
                        onChange={(e) => handleExchangeChange(item.id, e.target.value, options)}
                      >
                        {options.map((v) => (
                          <option key={v.variant_id} value={v.variant_id} disabled={!v.available}>
                            {v.title} - ${v.price.toFixed(2)} {!v.available ? "(Out of Stock)" : ""}
                          </option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <p className="error-text">No exchange variants available for this item.</p>
                  )}
                </div>
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

