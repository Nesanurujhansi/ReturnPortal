import { useState, useRef, useEffect } from "react";
import { chatWithAgent, clearAgentSession, getAgentSession } from "../api";

export default function ChatAgent() {
  const [sessionId] = useState(() => "session_" + Math.random().toString(36).substring(2, 9));
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hi! I am your AI Return Assistant. Please provide your **Order Number** and **Email** to get started.",
      options: []
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
    
    // Disable any options on previous messages
    setMessages((prev) => {
      const copy = prev.map((m, i) => {
        if (i === prev.length - 1 && m.role === "assistant") {
          return { ...m, optionsDisabled: true };
        }
        return m;
      });
      return [...copy, userMsg];
    });
    
    setInput("");
    setLoading(true);

    try {
      // Fetch response from API
      const result = await chatWithAgent(sessionId, messages, userMsg.content);
      setMessages((prev) => [
        ...prev,
        { 
          role: "assistant", 
          content: result.reply,
          options: result.options || [],
          optionsDisabled: false
        }
      ]);
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

  const handleOptionClick = (msgIdx, option) => {
    setMessages((prev) => {
      const copy = [...prev];
      copy[msgIdx] = { ...copy[msgIdx], optionsDisabled: true };
      return copy;
    });
    handleSend(null, option);
  };

  const handleReset = async () => {
    setLoading(true);
    try {
      await clearAgentSession(sessionId);
      setMessages([
        {
          role: "assistant",
          content: "Hi! I am your AI Return Assistant. Please provide your **Order Number** and **Email** to get started.",
          options: []
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

  return (
    <div className="card chat-card anim-fade-in">
      <div className="chat-header">
        <div className="chat-avatar" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent-color)" }}>
            <rect x="3" y="11" width="18" height="10" rx="2" />
            <circle cx="12" cy="5" r="2" />
            <path d="M12 7v4" />
            <line x1="8" y1="16" x2="8.01" y2="16" />
            <line x1="16" y1="16" x2="16.01" y2="16" />
          </svg>
        </div>
        <div style={{ flex: 1, marginLeft: "10px" }}>
          <h3>AI Return Assistant</h3>
          <p className="status-indicator">Online &bull; Powered by Gemini</p>
        </div>
        <button className="btn btn-secondary text-xs" style={{ padding: "6px 12px" }} onClick={handleReset}>
          Reset
        </button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className="chat-message-group" style={{ marginBottom: "12px" }}>
            <div className={`chat-bubble-wrapper ${msg.role}`}>
              <div className={`chat-bubble ${msg.role}`}>
                {String(msg.content || "").split("\n").map((line, lIdx) => (
                  <p key={lIdx} style={{ margin: "4px 0" }}>
                    {line}
                  </p>
                ))}
              </div>
            </div>
            
            {msg.role === "assistant" && msg.options && msg.options.length > 0 && (
              <div className="chat-options-container" style={{ display: "flex", flexWrap: "wrap", gap: "8px", margin: "8px 0 4px 12px" }}>
                {msg.options.map((opt, oIdx) => (
                  <button
                    key={oIdx}
                    className="btn btn-secondary text-xs"
                    style={{ borderRadius: "16px", padding: "6px 12px", border: "1px solid var(--border-color)", cursor: "pointer" }}
                    onClick={() => handleOptionClick(idx, opt)}
                    disabled={loading || msg.optionsDisabled || idx !== messages.length - 1}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            )}
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
