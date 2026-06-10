import { useState, useEffect } from "react";
import { getReturnReasons, uploadImage } from "../api";

export default function StepReturnReason({ order, selectedItems, onNext, onBack, initialReasons }) {
  const [reasonsList, setReasonsList] = useState([]);
  const [reasons, setReasons] = useState(
    initialReasons ||
      order.items
        .filter((item) => !!selectedItems[item.id])
        .reduce((acc, item) => {
          acc[item.id] = { reason: "", notes: "", image: null, imageName: "", image_file_id: null };
          return acc;
        }, {})
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState({}); // { itemId: boolean }

  useEffect(() => {
    async function loadReasons() {
      try {
        const data = await getReturnReasons();
        setReasonsList(data);
      } catch (err) {
        setError("Failed to fetch return reasons from database.");
      } finally {
        setLoading(false);
      }
    }
    loadReasons();
  }, []);

  const handleReasonChange = (itemId, field, value) => {
    setReasons((prev) => ({
      ...prev,
      [itemId]: {
        ...prev[itemId],
        [field]: value
      }
    }));
    setError("");
  };

  const handleImageChange = async (itemId, e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Please select an image file (PNG, JPG, WEBP).");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setError("Maximum file size allowed is 5MB.");
      return;
    }

    setUploading((prev) => ({ ...prev, [itemId]: true }));
    setError("");

    try {
      const currentReason = reasons[itemId]?.reason || "Not Specified";
      // Upload to GridFS with order_id, product_id, reason
      const uploadResult = await uploadImage(file, order.orderNumber, itemId, currentReason);
      
      const reader = new FileReader();
      reader.onload = () => {
        setReasons((prev) => ({
          ...prev,
          [itemId]: {
            ...prev[itemId],
            image: reader.result,
            imageName: file.name,
            image_file_id: uploadResult.file_id
          }
        }));
      };
      reader.readAsDataURL(file);
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
    } finally {
      setUploading((prev) => ({ ...prev, [itemId]: false }));
    }
  };

  const handleContinue = () => {
    for (const [itemId, qty] of Object.entries(selectedItems)) {
      const itemState = reasons[itemId];
      if (!itemState || !itemState.reason) {
        setError("Please select a return reason for all selected items.");
        return;
      }

      // Check damaged/defective rules
      const cleanReason = itemState.reason.toLowerCase();
      if (cleanReason.includes("damaged") || cleanReason.includes("defective")) {
        if (!itemState.notes || itemState.notes.trim().length < 5) {
          setError("Notes are required for this return reason.");
          return;
        }
        if (!itemState.image_file_id) {
          setError("Image is required for damaged product returns.");
          return;
        }
      }

      // Check wrong item requires notes
      if (cleanReason.includes("wrong") && (!itemState.notes || itemState.notes.trim().length < 5)) {
        setError("Notes are required for this return reason.");
        return;
      }

      // Check misplaced order requires detailed explaining
      if (cleanReason.includes("misplaced") && (!itemState.notes || itemState.notes.trim().length < 10)) {
        setError("Detailed additional reason description is required for misplaced orders.");
        return;
      }
    }
    onNext(reasons);
  };

  if (loading) {
    return (
      <div className="card anim-fade-in">
        <h2>Loading return reasons...</h2>
      </div>
    );
  }

  return (
    <div className="card anim-fade-in">
      <h2>Why are you returning?</h2>
      <p className="subtitle">Please provide reasons and optionally upload photos for each item.</p>

      {error && <div className="error-banner">{error}</div>}

      <div className="reasons-container">
        {order.items
          .filter((item) => !!selectedItems[item.id])
          .map((item) => {
            const itemState = reasons[item.id] || { reason: "", notes: "", image: null, imageName: "", image_file_id: null };
            const isUploading = !!uploading[item.id];
            const cleanReason = itemState.reason.toLowerCase();
            const notesRequired = cleanReason.includes("damaged") || cleanReason.includes("defective") || cleanReason.includes("wrong") || cleanReason.includes("misplaced");
            const imageRequired = cleanReason.includes("damaged") || cleanReason.includes("defective");

            return (
              <div key={item.id} className="reason-item-card">
                <div className="reason-item-header">
                  <img src={item.image} alt={item.name} className="product-thumb-sm" />
                  <div>
                    <h4>{item.name}</h4>
                    <p className="product-variant">{item.variant} &times; {selectedItems[item.id]}</p>
                  </div>
                </div>

                <div className="reason-fields">
                  <div className="field-group">
                    <label htmlFor={`reason-${item.id}`}>Reason for Return</label>
                    <select
                      id={`reason-${item.id}`}
                      value={itemState.reason}
                      onChange={(e) => handleReasonChange(item.id, "reason", e.target.value)}
                    >
                      <option value="">-- Select a reason --</option>
                      {reasonsList.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="field-group">
                    <label htmlFor={`notes-${item.id}`}>
                      Notes / Additional Details 
                      {notesRequired && " (Required)"}
                    </label>
                    <textarea
                      id={`notes-${item.id}`}
                      placeholder="Tell us more about the issue..."
                      value={itemState.notes}
                      onChange={(e) => handleReasonChange(item.id, "notes", e.target.value)}
                      rows={2}
                    />
                  </div>

                  <div className="field-group">
                    <label>
                      Upload Image 
                      {imageRequired && " (Required)"}
                    </label>
                    <div className="file-upload-wrapper">
                      <label className="file-upload-btn">
                        {isUploading ? "Uploading..." : "Choose Photo"}
                        <input
                          type="file"
                          accept="image/*"
                          onChange={(e) => handleImageChange(item.id, e)}
                          disabled={isUploading}
                        />
                      </label>
                      <span className="file-upload-name">
                        {itemState.imageName || "No file selected"}
                      </span>
                    </div>
                    {itemState.image && (
                      <div className="image-preview-box">
                        <img src={itemState.image} alt="Preview" />
                      </div>
                    )}
                  </div>
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
