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

  return (
    <div className="card anim-fade-in">
      <h2>Choose Return Method</h2>
      <p className="subtitle">Select how you would like us to process your return request.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="method-grid">
        {methodsList.map((m) => {
          const icon = m.id === "refund" ? "💵" : m.id === "credit" ? "💳" : "🔄";
          return (
            <div
              key={m.id}
              className={`method-card ${method === m.id ? "active" : ""}`}
              onClick={() => handleSelect(m.id)}
            >
              <div className="icon-badge">{icon}</div>
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
