import { useState } from "react";
import { verifyOrder } from "../api";

export default function StepOrderVerification({ onNext, initialOrderNumber, initialEmail }) {
  const [orderNumber, setOrderNumber] = useState(initialOrderNumber || "");
  const [email, setEmail] = useState(initialEmail || "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const cleanOrderNum = orderNumber.trim().replace("#", "");
    const cleanEmail = email.trim().toLowerCase();

    if (!cleanOrderNum || !cleanEmail) {
      setError("Please fill in both fields.");
      setLoading(false);
      return;
    }

    try {
      const data = await verifyOrder(cleanOrderNum, cleanEmail);
      onNext(data, cleanOrderNum, cleanEmail);
    } catch (err) {
      setError(err.message || "Failed to find order. Please verify inputs.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card anim-fade-in">
      <h2>Verify Your Order</h2>
      <p className="subtitle">Enter details to retrieve your order and request a return.</p>
      
      <form onSubmit={handleSubmit} className="form-group">
        {error && <div className="error-banner">{error}</div>}
        
        <div className="field-group">
          <label htmlFor="order-number">Order Number</label>
          <input
            id="order-number"
            type="text"
            placeholder="e.g. #1001"
            value={orderNumber}
            onChange={(e) => setOrderNumber(e.target.value)}
            disabled={loading}
          />
        </div>

        <div className="field-group">
          <label htmlFor="email">Email Address</label>
          <input
            id="email"
            type="email"
            placeholder="e.g. customer@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={loading}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Searching..." : "Find Order"}
        </button>
      </form>
    </div>
  );
}
