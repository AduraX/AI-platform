import "./globals.css";
import Link from "next/link";
import { ReactNode } from "react";

export const metadata = {
  title: "Private Enterprise AI Platform",
  description: "Enterprise chat, RAG, OCR, and evaluation platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div style={{ display: "flex", height: "100vh" }}>
          <nav style={{
            width: "220px",
            borderRight: "1px solid var(--border)",
            padding: "1rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.25rem",
            background: "var(--bg-secondary)",
          }}>
            <div style={{ fontWeight: 700, fontSize: "0.875rem", marginBottom: "1rem", color: "var(--accent)" }}>
              Enterprise AI
            </div>
            <Link href="/" style={{ padding: "0.5rem 0.75rem", borderRadius: "var(--radius)", fontSize: "0.875rem" }}>Chat</Link>
            <Link href="/documents" style={{ padding: "0.5rem 0.75rem", borderRadius: "var(--radius)", fontSize: "0.875rem" }}>Documents</Link>
            <div style={{ marginTop: "auto", fontSize: "0.75rem", color: "var(--fg-tertiary)" }}>
              v0.1.0
            </div>
          </nav>
          <main style={{ flex: 1, overflow: "auto" }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
