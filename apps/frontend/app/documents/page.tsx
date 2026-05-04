"use client";

import { useState, FormEvent } from "react";

interface IngestionJob {
  document_id: string;
  filename: string;
  job_id: string;
  status: string;
  indexed_chunks: number;
}

export default function DocumentsPage() {
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [tenantId, setTenantId] = useState("default");
  const [loading, setLoading] = useState(false);

  // Inline text ingestion
  const [filename, setFilename] = useState("");
  const [text, setText] = useState("");

  // File upload
  const [file, setFile] = useState<File | null>(null);

  async function handleTextIngest(e: FormEvent) {
    e.preventDefault();
    if (!filename.trim() || !text.trim() || loading) return;
    setLoading(true);

    try {
      const response = await fetch("/api/ingestion/v1/documents", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-tenant-id": tenantId,
          "x-user-id": "demo-user@example.com",
        },
        body: JSON.stringify({
          filename: filename.trim(),
          content_type: "text/plain",
          text: text.trim(),
        }),
      });
      const data = await response.json();
      if (data.job_id) {
        setJobs((prev) => [data, ...prev]);
        setFilename("");
        setText("");
      }
    } catch (error) {
      console.error("Ingestion failed:", error);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileUpload(e: FormEvent) {
    e.preventDefault();
    if (!file || loading) return;
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("content_type", file.type || "application/octet-stream");

      const response = await fetch("/api/ingestion/v1/documents/upload", {
        method: "POST",
        headers: {
          "x-tenant-id": tenantId,
          "x-user-id": "demo-user@example.com",
        },
        body: formData,
      });
      const data = await response.json();
      if (data.job_id) {
        setJobs((prev) => [data, ...prev]);
        setFile(null);
      }
    } catch (error) {
      console.error("Upload failed:", error);
    } finally {
      setLoading(false);
    }
  }

  async function refreshJob(jobId: string) {
    try {
      const response = await fetch(`/api/ingestion/v1/ingestion-jobs/${jobId}`, {
        headers: { "x-tenant-id": tenantId },
      });
      const data = await response.json();
      setJobs((prev) =>
        prev.map((j) => (j.job_id === jobId ? { ...j, status: data.status, indexed_chunks: data.indexed_chunks } : j))
      );
    } catch (error) {
      console.error("Refresh failed:", error);
    }
  }

  const statusBadge = (status: string) => {
    const cls = status === "completed" ? "badge-success" : status === "failed" ? "badge-error" : "badge-pending";
    return <span className={`badge ${cls}`}>{status}</span>;
  };

  return (
    <div style={{ padding: "1rem", maxWidth: "900px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600 }}>Documents</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label style={{ fontSize: "0.75rem", color: "var(--fg-secondary)" }}>Tenant:</label>
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            style={{ width: "140px", fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
          />
        </div>
      </div>

      {/* Text Ingestion */}
      <div style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius)", padding: "1rem", marginBottom: "1rem", border: "1px solid var(--border)" }}>
        <h2 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>Ingest Text</h2>
        <form onSubmit={handleTextIngest} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          <input
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            placeholder="Document name (e.g., refund-policy.md)"
            disabled={loading}
          />
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste document text here..."
            rows={4}
            disabled={loading}
            style={{ resize: "vertical" }}
          />
          <button type="submit" className="btn-primary" disabled={loading || !filename.trim() || !text.trim()} style={{ alignSelf: "flex-end" }}>
            {loading ? "Processing..." : "Ingest"}
          </button>
        </form>
      </div>

      {/* File Upload */}
      <div style={{ background: "var(--bg-secondary)", borderRadius: "var(--radius)", padding: "1rem", marginBottom: "1.5rem", border: "1px solid var(--border)" }}>
        <h2 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>Upload File</h2>
        <form onSubmit={handleFileUpload} style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={loading}
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn-primary" disabled={loading || !file}>
            {loading ? "Uploading..." : "Upload"}
          </button>
        </form>
      </div>

      {/* Jobs Table */}
      {jobs.length > 0 && (
        <div>
          <h2 style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>Ingestion Jobs</h2>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)", color: "var(--fg-secondary)", textAlign: "left" }}>
                <th style={{ padding: "0.5rem" }}>File</th>
                <th style={{ padding: "0.5rem" }}>Job ID</th>
                <th style={{ padding: "0.5rem" }}>Status</th>
                <th style={{ padding: "0.5rem" }}>Chunks</th>
                <th style={{ padding: "0.5rem" }}></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.job_id} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.75rem" }}>{job.filename}</td>
                  <td style={{ padding: "0.5rem", fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--fg-secondary)" }}>{job.job_id}</td>
                  <td style={{ padding: "0.5rem" }}>{statusBadge(job.status)}</td>
                  <td style={{ padding: "0.5rem" }}>{job.indexed_chunks}</td>
                  <td style={{ padding: "0.5rem" }}>
                    {job.status === "pending" && (
                      <button className="btn-secondary" onClick={() => refreshJob(job.job_id)} style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}>
                        Refresh
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
