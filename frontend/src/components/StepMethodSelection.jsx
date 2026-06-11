import { useState, useEffect } from "react";
import { getReturnMethods } from "../api";

export default function StepMethodSelection({ onNext, onBack, initialMethod }) {
  const [methodsList, setMethodsList] = useState([]);
  const [method, setMethod] = useState(initialMethod || "");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMethods() {
      try {
        const data = await getReturnMethods();
        setMethodsList(data);
      } catch (err) {
        setError("Failed to fetch return methods from database.");
      } finally {
        setLoading(false);
      }
    }
    loadMethods();
  }, []);

  const handleSelect = (selectedMethod) => {
    setMethod(selectedMethod);
    setError("");
  };

  const handleContinue = () => {
    if (!method) {
      setError("Please choose a return option to proceed.");
      return;
    }
    onNext(method);
  };

  if (loading) {
    return (
      <div className="card anim-fade-in">
        <h2>Loading return methods...</h2>
      </div>
    );
  }

  const renderMethodIcon = (methodId) => {
    if (methodId === "refund") {
      return (
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="svg-icon">
          <rect x="2" y="5" width="20" height="14" rx="2" ry="2" />
          <path d="M12 9a2.5 2.5 0 1 0 0 5 2.5 2.5 0 1 0 0-5z" />
        </svg>
      );
    }
    if (methodId === "credit") {
      return (
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="svg-icon">
          <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
          <line x1="1" y1="10" x2="23" y2="10" />
        </svg>
      );
    }
    return (
      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="svg-icon">
        <path d="M21.5 2v6h-6" />
        <path d="M21.34 15.57a10 10 0 1 1-.57-8.38l.57-.57" />
      </svg>
    );
  };

  return (
    <div className="card anim-fade-in">
      <h2>Choose Return Method</h2>
      <p className="subtitle">Select how you would like us to process your return request.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="method-grid">
        {methodsList.map((m) => {
          return (
            <div
              key={m.id}
              className={`method-card ${method === m.id ? "active" : ""}`}
              onClick={() => handleSelect(m.id)}
            >
              <div className="icon-badge">{renderMethodIcon(m.id)}</div>
              <h3>{m.title}</h3>
              <p>{m.description}</p>
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
