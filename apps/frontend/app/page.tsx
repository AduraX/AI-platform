"use client";

import { useState, useRef, useEffect, FormEvent } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  streaming?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [tenantId, setTenantId] = useState("default");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    // Add placeholder assistant message
    setMessages((prev) => [...prev, { role: "assistant", content: "", streaming: true }]);

    try {
      const response = await fetch("/api/v1/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-tenant-id": tenantId,
          "x-user-id": "demo-user@example.com",
        },
        body: JSON.stringify({ message: userMessage, stream: true }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullText = "";
      let sources: string[] = [];

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              // Event type will be used with next data line
              continue;
            }
            if (line.startsWith("data: ")) {
              const data = line.slice(6);
              // Try to parse as JSON first
              try {
                const parsed = JSON.parse(data);
                if (parsed.sources) {
                  sources = parsed.sources;
                }
                if (parsed.source) {
                  sources.push(parsed.source);
                }
              } catch {
                // Plain text token
                fullText += data;
                setMessages((prev) => {
                  const updated = [...prev];
                  const last = updated[updated.length - 1];
                  if (last?.role === "assistant") {
                    updated[updated.length - 1] = { ...last, content: fullText };
                  }
                  return updated;
                });
              }
            }
          }
        }
      }

      // Finalize message
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === "assistant") {
          updated[updated.length - 1] = {
            ...last,
            content: fullText || last.content,
            sources,
            streaming: false,
          };
        }
        return updated;
      });
    } catch (error) {
      // Fallback to non-streaming
      try {
        const response = await fetch("/api/v1/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-tenant-id": tenantId,
            "x-user-id": "demo-user@example.com",
          },
          body: JSON.stringify({ message: userMessage }),
        });
        const data = await response.json();
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: data.reply || data.error?.message || "Error occurred",
            sources: data.sources || [],
          };
          return updated;
        });
      } catch {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: "Failed to connect to the API. Make sure backend services are running.",
          };
          return updated;
        });
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{
        padding: "0.75rem 1rem",
        borderBottom: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
      }}>
        <h1 style={{ fontSize: "1rem", fontWeight: 600 }}>Chat</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.75rem", color: "var(--fg-secondary)" }}>Tenant:</label>
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            style={{ width: "140px", fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
          />
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflow: "auto", padding: "1rem" }}>
        {messages.length === 0 && (
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            color: "var(--fg-tertiary)",
            fontSize: "0.875rem",
          }}>
            Send a message to start chatting. Documents you ingest will be used as context.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} style={{
            marginBottom: "1rem",
            display: "flex",
            flexDirection: "column",
            alignItems: msg.role === "user" ? "flex-end" : "flex-start",
          }}>
            <div style={{
              maxWidth: "70%",
              padding: "0.75rem 1rem",
              borderRadius: "var(--radius)",
              background: msg.role === "user" ? "var(--accent)" : "var(--bg-tertiary)",
              color: msg.role === "user" ? "white" : "var(--fg)",
              fontSize: "0.875rem",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
            }}>
              {msg.content || (msg.streaming ? "..." : "")}
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div style={{ marginTop: "0.25rem", fontSize: "0.7rem", color: "var(--fg-tertiary)" }}>
                Sources: {msg.sources.join(", ")}
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} style={{
        padding: "1rem",
        borderTop: "1px solid var(--border)",
        display: "flex",
        gap: "0.5rem",
      }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question..."
          disabled={loading}
          style={{ flex: 1 }}
        />
        <button type="submit" className="btn-primary" disabled={loading || !input.trim()}>
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
