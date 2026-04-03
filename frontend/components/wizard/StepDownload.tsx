"use client";
import { useState } from "react";
import { api, downloadPdf } from "@/lib/api";

export default function StepDownload({
  resume,
  onResumeChange,
  onBack,
  onStartOver,
}: {
  resume: Record<string, unknown>;
  onResumeChange: (data: Record<string, unknown>) => void;
  onBack: () => void;
  onStartOver: () => void;
}) {
  const [loadingResume, setLoadingResume] = useState(false);
  const [loadingCover, setLoadingCover] = useState(false);
  const [loadingCompress, setLoadingCompress] = useState(false);
  const [error, setError] = useState("");
  const [fontScale, setFontScale] = useState(1.0);
  const [fontFamily, setFontFamily] = useState("Helvetica");

  const hasCoverLetter = !!(resume?.cover_letter);

  async function handleResumePDF() {
    setLoadingResume(true); setError("");
    try {
      const res = await api.pdfResume(resume, fontScale, fontFamily);
      downloadPdf(res.pdf_base64, res.filename);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "PDF generation failed");
    } finally { setLoadingResume(false); }
  }

  async function handleCoverPDF() {
    setLoadingCover(true); setError("");
    try {
      const res = await api.pdfCoverLetter(resume, fontScale, fontFamily);
      downloadPdf(res.pdf_base64, res.filename);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "PDF generation failed");
    } finally { setLoadingCover(false); }
  }

  async function handleCompress() {
    setLoadingCompress(true); setError("");
    try {
      const res = await api.compress(resume);
      onResumeChange(res.resume);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Compress failed");
    } finally { setLoadingCompress(false); }
  }

  function exportJson() {
    const blob = new Blob([JSON.stringify(resume, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "resume_data.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <div className="page-title">Download</div>
      <div className="page-sub">Your tailored resume and cover letter are ready.</div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Customisation */}
      <div className="card">
        <div className="card-title">// pdf_settings</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
          <div>
            <label>Font Family</label>
            <select value={fontFamily} onChange={e => setFontFamily(e.target.value)}>
              <option value="Helvetica">Helvetica</option>
              <option value="Times-Roman">Times Roman</option>
              <option value="Courier">Courier</option>
            </select>
          </div>
          <div>
            <label>Font Scale ({fontScale.toFixed(1)}x)</label>
            <input
              type="range"
              min={0.8}
              max={1.2}
              step={0.05}
              value={fontScale}
              onChange={e => setFontScale(parseFloat(e.target.value))}
            />
          </div>
        </div>
      </div>

      {/* Downloads */}
      <div className="grid-2">
        <div className="card">
          <div className="card-title">// resume.pdf</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1.25rem" }}>
            Clean A4 resume PDF, formatted with your selected font settings.
          </p>
          <button className="btn btn-primary" onClick={handleResumePDF} disabled={loadingResume}>
            {loadingResume ? <span className="spinner" /> : "⬇ "}
            {loadingResume ? "Generating…" : "Download Resume PDF"}
          </button>
        </div>

        <div className="card" style={{ opacity: hasCoverLetter ? 1 : 0.6 }}>
          <div className="card-title">// cover_letter.pdf</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1.25rem" }}>
            {hasCoverLetter ? "Cover letter ready for download." : "No cover letter — go back to Generate to create one."}
          </p>
          <button className="btn btn-primary" onClick={handleCoverPDF} disabled={loadingCover || !hasCoverLetter}>
            {loadingCover ? <span className="spinner" /> : "⬇ "}
            {loadingCover ? "Generating…" : "Download Cover Letter PDF"}
          </button>
        </div>
      </div>

      {/* Optional tools */}
      <div className="card">
        <div className="card-title">// compress_to_one_page</div>
        <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
          Trims bullet points and shortens content so your resume fits neatly on one page.
        </p>
        <button className="btn btn-ghost" onClick={handleCompress} disabled={loadingCompress}>
          {loadingCompress ? <span className="spinner" /> : null}
          {loadingCompress ? "Compressing…" : "Compress to 1 Page"}
        </button>
      </div>

      <div className="card">
        <div className="card-title">// export_json</div>
        <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
          Download your resume data as JSON — useful as a backup or to re-import next time.
        </p>
        <button className="btn btn-ghost" onClick={exportJson}>⬇ Export resume_data.json</button>
      </div>

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-ghost" onClick={onStartOver} style={{ marginLeft: "auto" }}>
          Start Over
        </button>
      </div>
    </div>
  );
}
