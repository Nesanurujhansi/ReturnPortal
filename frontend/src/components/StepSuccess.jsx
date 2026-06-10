import React from "react";

export default function StepSuccess({ result, onRestart }) {
  const { return_id, tracking_number, carrier, shipping_label_url } = result || {};

  return (
    <div className="card success-card anim-fade-in">
      <div className="success-badge">✓</div>
      <h2>Return Request Submitted!</h2>
      <p className="subtitle">
        Your request has been registered under ID: <strong>{return_id || "RET-XXXXXX"}</strong>
      </p>

      <div className="shipping-instructions">
        <h3>What to do next:</h3>
        <ol>
          <li>
            <strong>Print your Prepaid Label:</strong> Click the button below to retrieve your shipping label.
          </li>
          <li>
            <strong>Pack your items:</strong> Place all items in the original packaging or a secure box.
          </li>
          <li>
            <strong>Attach the label:</strong> Securely tape the shipping label to the outside of your package.
          </li>
          <li>
            <strong>Drop off:</strong> Take your package to any local post office or authorized package drop station.
          </li>
        </ol>
      </div>

      <div className="label-box">
        <div className="label-info">
          <h4>Prepaid Return Shipping Label</h4>
          <p className="text-sm">Carrier: {carrier || "USPS"} Ground Advantage</p>
          <p className="text-xs text-gray">Tracking: {tracking_number || "9400 0000 0000 0000 0000 00"}</p>
        </div>
        <button 
          className="btn btn-accent btn-sm" 
          onClick={() => window.open(shipping_label_url || "#", "_blank") || alert("Simulating PDF download...")}
        >
          📥 Download Shipping Label (PDF)
        </button>
      </div>

      <button className="btn btn-primary" onClick={onRestart}>
        Return to Portal Home
      </button>
    </div>
  );
}
