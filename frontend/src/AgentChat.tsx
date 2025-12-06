import React, { useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;


type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export default function AgentChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hi! I’m your ZyQ quantum assistant. Ask me about the option pricer, the quantum walk, or how the site works.",
    },
  ]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 🔥 NEW: one-time bounce state
  const [shouldBounce, setShouldBounce] = useState(false);

  // 🔥 NEW: start bounce after delay (no bounce during loading animation)
  React.useEffect(() => {
    const timer = setTimeout(() => {
      setShouldBounce(true);
    }, 1000);
    return () => clearTimeout(timer);
  }, []);

  async function sendMessage(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;

    const newMessage: ChatMessage = { role: "user", content: input.trim() };
    const updated = [...messages, newMessage];
    setMessages(updated);
    setInput("");
    setSending(true);
    setError(null);

    try {
        const API_URL = import.meta.env.VITE_API_URL;

        const res = await fetch(`${API_URL}/assistant`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: newMessage.content }),
        });


      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error ${res.status}`);
      }

      const data: { answer: string } = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);
    } catch (err: any) {
      console.error(err);
      setError(err.message ?? "Something went wrong talking to the agent.");
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {/* Toggle button with bounce */}
      <button
        className={`agent-toggle ${shouldBounce ? "agent-button-bounce-once" : ""}`}
        type="button"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "×" : "Ask ZyQ"}
      </button>

      {open && (
        <div className="agent-chat-window">
          <div className="agent-header">
            <span>🔭 ZyQ Quantum Agent</span>
          </div>

          <div className="agent-messages">
            {messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "agent-message agent-user"
                    : "agent-message agent-assistant"
                }
              >
                {m.content}
              </div>
            ))}
          </div>

          {error && <div className="agent-error">⚠️ {error}</div>}

          <form onSubmit={sendMessage} className="agent-input-row">
            <input
              type="text"
              placeholder="Ask about pricing, quantum walk, etc..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={sending}
            />
            <button type="submit" disabled={sending}>
              {sending ? "…" : "Send"}
            </button>
          </form>
        </div>
      )}
    </>
  );
}
