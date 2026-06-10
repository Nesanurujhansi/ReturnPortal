import { useState, useRef, useEffect } from "react";
import { chatWithAgent, clearAgentSession, getAgentSession } from "../api";

export default function ChatAgent() {
  const [sessionId] = useState(() => "session_" + Math.random().toString(36).substring(2, 9));
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hi! I am your AI Return Assistant. Please provide your **Order Number** and **Email** to get started."
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [nextAction, setNextAction] = useState("collect_order_details");
  const [sessionData, setSessionData] = useState(null);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchSessionStatus = async () => {
    try {
      const data = await getAgentSession(sessionId);
      if (data && data.success) {
        setSessionData(data.data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSend = async (e, customMessage = null) => {
    if (e) e.preventDefault();
    const messageToSend = customMessage || input;
    if (!messageToSend.trim() || loading) return;

    const userMsg = { role: "user", content: messageToSend };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Fetch response from API
      const result = await chatWithAgent(sessionId, messages, userMsg.content);
      setMessages((prev) => [...prev, { role: "assistant", content: result.reply }]);
      setNextAction(result.next_action);
      await fetchSessionStatus();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry, I hit an error: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await clearAgentSession(sessionId);
      setMessages([
        {
          role: "assistant",
          content: "Hi! I am your AI Return Assistant. Please provide your **Order Number** and **Email** to get started."
        }
      ]);
      setNextAction("collect_order_details");
      setSessionData(null);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getSuggestedActionButtons = () => {
    if (loading) return null;
    
    switch (nextAction) {
      case "collect_order_details":
        return (
          <div className="suggested-actions">
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Order #1001, customer@example.com")}>
              Try Demo Order #1001
            </button>
          </div>
        );
      case "select_product":
        return (
          <div className="suggested-actions">
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Return Classic Denim Jacket")}>
              Classic Denim Jacket
            </button>
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Return Premium Cotton Tee")}>
              Premium Cotton Tee
            </button>
          </div>
        );
      case "select_return_method":
        return (
          <div className="suggested-actions">
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Refund")}>
              Refund (Original Payment)
            </button>
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Store Credit")}>
              Store Credit
            </button>
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Exchange")}>
              Exchange
            </button>
          </div>
        );
      case "select_return_reason":
        return (
          <div className="suggested-actions">
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Changed Mind")}>
              Changed Mind
            </button>
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Size Didn't Fit")}>
              Size Didn't Fit
            </button>
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "Damaged Product")}>
              Damaged Product (Requires Note/Photo)
            </button>
          </div>
        );
      case "collect_notes":
        return (
          <div className="suggested-actions">
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "The size is way too big.")}>
              Explain: Too big
            </button>
          </div>
        );
      case "collect_image":
        return (
          <div className="suggested-actions text-xs text-gray" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span>Please upload an image in the form and copy/paste file ID:</span>
            <button className="btn btn-secondary text-xs" onClick={() => handleSend(null, "file_id " + (sessionData?.image_file_id || "file_id_placeholder"))}>
              Submit file_id: {sessionData?.image_file_id || "None (Upload First)"}
            </button>
          </div>
        );
      case "confirm_return":
        return (
          <div className="suggested-actions">
            <button className="btn btn-primary text-xs" onClick={() => handleSend(null, "confirm")}>
              Confirm & Submit Return
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="card chat-card anim-fade-in">
      <div className="chat-header">
        <div className="chat-avatar">🤖</div>
        <div style={{ flex: 1 }}>
          <h3>AI Return Assistant</h3>
          <p className="status-indicator">Online &bull; Powered by Gemini</p>
        </div>
        <button className="btn btn-secondary text-xs" style={{ padding: "6px 12px" }} onClick={handleReset}>
          Reset
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-bubble-wrapper ${msg.role}`}>
            <div className={`chat-bubble ${msg.role}`}>
              {String(msg.content || "").split("\n").map((line, lIdx) => (
                <p key={lIdx} style={{ margin: "4px 0" }}>
                  {line}
                </p>
              ))}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-bubble-wrapper assistant">
            <div className="chat-bubble assistant typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {getSuggestedActionButtons()}

      <form onSubmit={handleSend} className="chat-input-area" style={{ marginTop: "15px" }}>
        <input
          type="text"
          placeholder="Type your message here..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary btn-chat-send" disabled={loading}>
          Send
        </button>
      </form>
    </div>
  );
}
