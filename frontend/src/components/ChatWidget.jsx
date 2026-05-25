import React, { useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { api } from "../api";

export default function ChatWidget({ onDashboardRefresh }) {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Ask me about MXN rates, forecasts, model comparisons, training, or BNR updates."
    }
  ]);

  async function sendMessage(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || loading) {
      return;
    }
    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setMessage("");
    setLoading(true);
    try {
      const response = await api.chat(trimmed);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          provider: response.provider,
          toolCalls: response.tool_calls || []
        }
      ]);
      if ((response.tool_calls || []).some((call) => ["scrape_bnr_data", "train_models"].includes(call.tool))) {
        onDashboardRefresh?.();
      }
    } catch (err) {
      setMessages((current) => [
        ...current,
        { role: "assistant", content: `Chat request failed: ${err.message}` }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-widget">
      {open ? (
        <section className="chat-panel" aria-label="MXN chatbot">
          <header className="chat-header">
            <div>
              <strong>MXN Assistant</strong>
              <span>Tool-enabled chatbot</span>
            </div>
            <button type="button" className="chat-icon-button" title="Close chat" onClick={() => setOpen(false)}>
              <X size={18} />
            </button>
          </header>
          <div className="chat-messages">
            {messages.map((item, index) => (
              <div className={`chat-message chat-message--${item.role}`} key={`${item.role}-${index}`}>
                <p>{item.content}</p>
                {item.provider ? <span className="chat-meta">{item.provider}</span> : null}
                {item.toolCalls?.length ? (
                  <span className="chat-meta">{item.toolCalls.map((call) => call.tool).join(", ")}</span>
                ) : null}
              </div>
            ))}
            {loading ? <div className="chat-message chat-message--assistant"><p>Working...</p></div> : null}
          </div>
          <form className="chat-form" onSubmit={sendMessage}>
            <input
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask about MXN..."
              aria-label="Chat message"
            />
            <button type="submit" title="Send message" disabled={loading || !message.trim()}>
              <Send size={17} />
            </button>
          </form>
        </section>
      ) : null}

      <button
        type="button"
        className="chat-launcher"
        title="Open MXN assistant"
        onClick={() => setOpen((value) => !value)}
      >
        <MessageCircle size={24} />
      </button>
    </div>
  );
}
