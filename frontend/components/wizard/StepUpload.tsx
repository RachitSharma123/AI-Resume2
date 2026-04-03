"use client";
import { useState, useRef } from "react";
import { api } from "@/lib/api";

const DEFAULT_RESUME = {
  name: "Your Name",
  contact: "Melbourne, VIC | +61 4XX XXX XXX | email@example.com",
  career_objective: "Write your career objective here.",
  skills_snapshot: [
    { label: "Technical Skills", value: "Python, SQL, Excel, Tableau" },
    { label: "Soft Skills", value: "Communication, Problem Solving, Leadership" },
  ],
  experience: [
    {
      company: "Company Name",
      role_line: "Job Title | Jan 2023 – Present",
      bullets: [
        "Describe your key achievement here with metrics.",
        "Another achievement using STAR method.",
      ],
    },
  ],
  education: [
    { degree: "Bachelor of Science in Computer Science", details: "University Name | 2019 – 2022" },
  ],
  certifications: [],
  additional_information: {},
  references: [],
};

export default function StepUpload({
  onComplete,
}: {
  onComplete: (resume: Record<string, unknown>) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [showJsonPaste, setShowJsonPaste] = useState(false);
  const [jsonText, setJsonText] = useState("");
  const [jsonError, setJsonError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF file.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await api.extractResume(file);
      onComplete(res.resume);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Extraction failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleJsonSave() {
    setJsonError("");
    try {
      const parsed = JSON.parse(jsonText);
      onComplete(parsed);
    } catch {
      setJsonError("Invalid JSON — check your syntax.");
    }
  }

  return (
    <div>
      <div className="page-title">Upload Your Resume</div>
      <div className="page-sub">Upload a PDF and we'll extract your resume data automatically using AI.</div>

      {error && <div className="alert alert-error">{error}</div>}

      {!showJsonPaste ? (
        <>
          <div
            className={`card upload-zone${dragging ? " dragging" : ""}`}
            onClick={() => !loading && fileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            style={{ cursor: loading ? "default" : "pointer", textAlign: "center", padding: "3rem 2rem" }}
          >
            {loading ? (
              <div>
                <div className="spinner" style={{ width: 32, height: 32, margin: "0 auto 1rem" }} />
                <div style={{ color: "var(--muted)", fontSize: "0.9rem" }}>Extracting resume data with AI…</div>
                <div style={{ color: "var(--muted)", fontSize: "0.8rem", marginTop: "0.5rem" }}>This may take 5–15 seconds</div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}>⬆</div>
                <div style={{ fontWeight: 600, marginBottom: "0.4rem" }}>Drop your PDF here, or click to browse</div>
                <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Text-based PDFs only — scanned images won't work</div>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              style={{ display: "none" }}
              onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
            />
          </div>

          <div style={{ textAlign: "center", marginTop: "1rem" }}>
            <button
              className="btn btn-ghost"
              style={{ fontSize: "0.82rem" }}
              onClick={() => setShowJsonPaste(true)}
            >
              Already have resume JSON? Paste it manually →
            </button>
          </div>
        </>
      ) : (
        <div className="card">
          <div className="card-title">// paste_resume_json</div>
          {jsonError && <div className="alert alert-error">{jsonError}</div>}
          <textarea
            value={jsonText}
            onChange={e => setJsonText(e.target.value)}
            placeholder={JSON.stringify(DEFAULT_RESUME, null, 2)}
            style={{ minHeight: "300px", fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
            spellCheck={false}
          />
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={handleJsonSave}>Use This Resume →</button>
            <button
              className="btn btn-ghost"
              onClick={() => { setJsonText(JSON.stringify(DEFAULT_RESUME, null, 2)); }}
            >
              Load Template
            </button>
            <button className="btn btn-ghost" onClick={() => setShowJsonPaste(false)}>
              ← Back to PDF Upload
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
