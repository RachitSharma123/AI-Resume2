"use client";
import { useState } from "react";
import { api, downloadPdf } from "@/lib/api";

export default function PDFSection({ resume }: { resume: Record<string, unknown> | null }) {
  const [loading, setLoading] = useState<"resume" | "cover" | null>(null);
  const [error, setError] = useState("");

  async function handleResumePDF() {
    if (!resume) { setError("No resume loaded."); return; }
    setLoading("resume"); setError("");
    try {
      const res = await api.pdfResume(resume);
      downloadPdf(res.pdf_base64, res.filename);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "PDF generation failed");
    } finally { setLoading(null); }
  }

  async function handleCoverPDF() {
    if (!resume) { setError("No resume loaded."); return; }
    if (!resume.cover_letter) {
      setError("No cover letter found. Use AI Tools → Cover Letter to generate one first.");
      return;
    }
    setLoading("cover"); setError("");
    try {
      const res = await api.pdfCoverLetter(resume);
      downloadPdf(res.pdf_base64, res.filename);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "PDF generation failed");
    } finally { setLoading(null); }
  }

  const hasCoverLetter = !!(resume?.cover_letter);

  return (
    <div>
      <div className="page-title">PDF Export</div>
      <div className="page-sub">Download your resume and cover letter as professionally formatted PDFs.</div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="grid-2">
        <div className="card">
          <div className="card-title">// resume.pdf</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.6, marginBottom: "1.25rem" }}>
            Generates a clean A4 resume PDF from your current resume data. Uses ReportLab for precise layout.
          </p>
          <button className="btn btn-primary" onClick={handleResumePDF} disabled={loading === "resume"}>
            {loading === "resume" ? <span className="spinner" /> : "⬇"}
            {loading === "resume" ? "Generating…" : "Download Resume PDF"}
          </button>
        </div>

        <div className="card" style={{ opacity: hasCoverLetter ? 1 : 0.6 }}>
          <div className="card-title">// cover_letter.pdf</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.6, marginBottom: "1.25rem" }}>
            {hasCoverLetter
              ? "Cover letter is ready. Download as PDF."
              : "No cover letter yet. Generate one in AI Tools first."}
          </p>
          <button
            className="btn btn-primary"
            onClick={handleCoverPDF}
            disabled={loading === "cover" || !hasCoverLetter}
          >
            {loading === "cover" ? <span className="spinner" /> : "⬇"}
            {loading === "cover" ? "Generating…" : "Download Cover Letter PDF"}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="card-title">// export_json</div>
        <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
          Download your current resume data as JSON for backup or re-upload.
        </p>
        <button
          className="btn btn-ghost"
          onClick={() => {
            if (!resume) return;
            const blob = new Blob([JSON.stringify(resume, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "resume_data.json";
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          ⬇ Export resume_data.json
        </button>
      </div>
    </div>
  );
}
