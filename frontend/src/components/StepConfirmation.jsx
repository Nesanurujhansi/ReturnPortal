import React, { useState, useEffect } from "react";
import { calculateReturn, submitReturn } from "../api";

export default function StepConfirmation({
  order,
  selectedItems,
  method,
  reasons,
  exchanges,
  onNext,
  onBack,
  orderNumber,
  email
}) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [summary, setSummary] = useState({ subtotal: 0, handling_fee: 0, total_refund_amount: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    async function getCalculation() {
      try {
        const data = await calculateReturn(method, selectedItems, orderNumber, email);
        setSummary(data);
      } catch (err) {
        setError("Failed to calculate returns. Please check details.");
      } finally {
        setLoading(false);
      }
    }
    getCalculation();
  }, [method, selectedItems, orderNumber, email]);

  const handleSubmit = async () => {
    setError("");
    setSubmitting(true);

    // Format selected items for submission
    const itemsPayload = Object.entries(selectedItems).map(([itemId, qty]) => {
      const reasonState = reasons[itemId] || {};
      const exchangeState = exchanges?.[itemId] || null;

      return {
        item_id: itemId,
        quantity: qty,
        reason: reasonState.reason || "Returned",
        notes: reasonState.notes || "",
        image_file_id: reasonState.image_file_id || null,
        exchange_variant: exchangeState ? {
          size: exchangeState.size || "",
          color: exchangeState.color || ""
        } : null
      };
    });

    const payload = {
      order_number: orderNumber,
      email: email,
      method,
      items: itemsPayload,
      subtotal: summary.subtotal,
      handling_fee: summary.handling_fee,
      total_amount: summary.total_refund_amount
    };

    try {
      const result = await submitReturn(payload);
      onNext(result);
    } catch (err) {
      setError(err.message || "Failed to submit return request.");
    } finally {
      setSubmitting(false);
    }
  };

  const getMethodLabel = () => {
    switch (method) {
      case "refund":
        return "Refund to Original Payment Method";
      case "credit":
        return "Store Credit (Instant activation)";
      case "exchange":
        return "Exchange for Different Variant";
      default:
        return "";
    }
  };

  if (loading) {
    return (
      <div className="card anim-fade-in">
        <h2>Loading summary...</h2>
      </div>
    );
  }

  const renderMethodIcon = (methodId) => {
    if (methodId === "refund") {
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="svg-icon">
          <rect x="2" y="5" width="20" height="14" rx="2" ry="2" />
          <path d="M12 9a2.5 2.5 0 1 0 0 5 2.5 2.5 0 1 0 0-5z" />
        </svg>
      );
    }
    if (methodId === "credit") {
      return (
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="svg-icon">
          <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
          <line x1="1" y1="10" x2="23" y2="10" />
        </svg>
      );
    }
    return (
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="svg-icon">
        <path d="M21.5 2v6h-6" />
        <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l.57-.57" />
      </svg>
    );
  };

  return (
    <div className="card anim-fade-in">
      <h2>Confirm Return Details</h2>
      <p className="subtitle">Please review your return request before submitting.</p>

      {error && <div className="error-banner" style={{ marginBottom: "20px" }}>{error}</div>}

      <div className="confirm-section">
        <h3>Return Method</h3>
        <div className="confirm-method-badge">
          <span className="icon" style={{ display: "inline-flex", alignItems: "center" }}>
            {renderMethodIcon(method)}
          </span>
          <div>
            <strong>{getMethodLabel()}</strong>
            <p className="text-sm">
              {method === "refund"
                ? "Will be returned to original payment card."
                : method === "credit"
                ? "Code will be emailed to you instantly after processing."
                : "Exchange order will ship immediately."}
            </p>
          </div>
        </div>
      </div>

      <div className="confirm-section">
        <h3>Items to Return</h3>
        <div className="confirm-items-list">
          {order.items
            .filter((item) => !!selectedItems[item.id])
            .map((item) => {
              const reasonInfo = reasons[item.id] || {};
              const exchangeInfo = exchanges?.[item.id] || null;

              return (
                <div key={item.id} className="confirm-item-row">
                  <img src={item.image} alt={item.name} className="product-thumb-sm" />
                  <div className="confirm-item-details">
                    <h4>{item.name}</h4>
                    <p className="text-sm text-gray">Original: {item.variant} &times; {selectedItems[item.id]}</p>
                    {reasonInfo.reason && (
                      <p className="text-sm text-italic">Reason: {reasonInfo.reason}</p>
                    )}
                    {exchangeInfo && (
                      <div className="exchange-tag" style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ display: "inline-block" }}>
                          <path d="M21.5 2v6h-6" />
                          <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l.57-.57" />
                        </svg>
                        Exchange For: {exchangeInfo.color} / {exchangeInfo.size}
                      </div>
                    )}
                  </div>
                  <div className="confirm-item-price">
                    ${(item.price * selectedItems[item.id]).toFixed(2)}
                  </div>
                </div>
              );
            })}
        </div>
      </div>

      <div className="confirm-section summary-box">
        <h3>Summary of Charges</h3>
        <div className="summary-row">
          <span>Item Subtotal</span>
          <span>${summary.subtotal.toFixed(2)}</span>
        </div>
        <div className="summary-row">
          <span>Return Handling Fee</span>
          <span>{summary.handling_fee > 0 ? `$${summary.handling_fee.toFixed(2)}` : "FREE"}</span>
        </div>
        <hr className="divider" />
        <div className="summary-row total">
          <span>
            {method === "refund"
              ? "Estimated Refund"
              : method === "credit"
              ? "Total Store Credit"
              : "Exchange Value"}
          </span>
          <span className="accent-color">${summary.total_refund_amount.toFixed(2)}</span>
        </div>
      </div>

      <div className="actions-bar">
        <button onClick={onBack} className="btn btn-secondary" disabled={submitting}>
          Back
        </button>
        <button onClick={handleSubmit} className="btn btn-primary" disabled={submitting}>
          {submitting ? "Submitting..." : "Submit Return Request"}
        </button>
      </div>
    </div>
  );
}
