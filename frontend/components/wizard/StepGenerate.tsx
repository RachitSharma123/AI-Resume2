"use client";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

type ATSResult = {
  ats_score: number;
  keyword_match: number;
  experience_match: number;
  skills_match: number;
  strengths: string[];
  weaknesses: string[];
  missing_keywords: string[];
  suggestions: string[];
};

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="score-bar-wrap">
      <div className="score-bar-label">
        <span>{label}</span>
        <span>{value}%</span>
      </div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export default function StepGenerate({
  resume,
  jobDescription,
  onResumeChange,
  onAtsResult,
  onCoverLetterChange,
  atsResult,
  coverLetter,
  onNext,
  onBack,
}: {
  resume: Record<string, unknown>;
  jobDescription: string;
  onResumeChange: (data: Record<string, unknown>) => void;
  onAtsResult: (r: ATSResult) => void;
  onCoverLetterChange: (cl: Record<string, unknown>) => void;
  atsResult: ATSResult | null;
  coverLetter: Record<string, unknown> | null;
  onNext: () => void;
  onBack: () => void;
}) {
  const [phase, setPhase] = useState<"idle" | "tailoring" | "ats" | "cover" | "done">("idle");
  const [error, setError] = useState("");
  const [tailored, setTailored] = useState(false);
  const [loadingCover, setLoadingCover] = useState(false);
  const [loadingAts, setLoadingAts] = useState(false);
  const [preResume] = useState<Record<string, unknown>>(resume);

  async function runAll() {
    setError("");
    setPhase("tailoring");
    try {
      const tailorRes = await api.tailor(resume, jobDescription);
      onResumeChange(tailorRes.resume);
      setTailored(true);

      setPhase("ats");
      const atsRes = await api.atsScore(tailorRes.resume, jobDescription);
      onAtsResult(atsRes);

      setPhase("cover");
      const clRes = await api.coverLetter(tailorRes.resume, jobDescription);
      onCoverLetterChange(clRes.cover_letter);
      onResumeChange({ ...tailorRes.resume, cover_letter: clRes.cover_letter });

      setPhase("done");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Something failed. Try again.");
      setPhase("idle");
    }
  }

  async function handleRegenerateAts() {
    setLoadingAts(true);
    try {
      const res = await api.atsScore(resume, jobDescription);
      onAtsResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "ATS failed");
    } finally { setLoadingAts(false); }
  }

  async function handleRegenerateCover() {
    setLoadingCover(true);
    try {
      const res = await api.coverLetter(resume, jobDescription);
      onCoverLetterChange(res.cover_letter);
      onResumeChange({ ...resume, cover_letter: res.cover_letter });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Cover letter failed");
    } finally { setLoadingCover(false); }
  }

  async function handleImproveFromAts() {
    if (!atsResult) return;
    setLoadingAts(true);
    try {
      const res = await api.improveFromAts(resume, atsResult, jobDescription);
      onResumeChange(res.resume);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Improve failed");
    } finally { setLoadingAts(false); }
  }

  const phaseLabel = {
    tailoring: "Tailoring resume to job description…",
    ats: "Analysing ATS score…",
    cover: "Generating cover letter…",
    done: "",
    idle: "",
  }[phase];

  const isRunning = phase !== "idle" && phase !== "done";

  return (
    <div>
      <div className="page-title">Generate</div>
      <div className="page-sub">Tailor your resume, score it, and generate a cover letter.</div>

      {error && <div className="alert alert-error">{error}</div>}

      {phase === "idle" && !tailored && (
        <div className="card" style={{ textAlign: "center", padding: "2.5rem" }}>
          <p style={{ color: "var(--muted)", marginBottom: "1.5rem" }}>
            This will run three AI steps in sequence: tailor your resume to the job, score it against ATS criteria, and generate a human-sounding cover letter.
          </p>
          <button className="btn btn-primary" style={{ fontSize: "1rem", padding: "0.75rem 2rem" }} onClick={runAll}>
            Do Everything →
          </button>
        </div>
      )}

      {isRunning && (
        <div className="card" style={{ textAlign: "center", padding: "2.5rem" }}>
          <div className="spinner" style={{ width: 36, height: 36, margin: "0 auto 1rem" }} />
          <div style={{ color: "var(--muted)" }}>{phaseLabel}</div>
          <div style={{ marginTop: "1.25rem", display: "flex", justifyContent: "center", gap: "0.5rem" }}>
            {(["tailoring", "ats", "cover"] as const).map(p => (
              <div key={p} style={{
                width: 8, height: 8, borderRadius: "50%",
                background: phase === p ? "var(--accent)" : "var(--border)",
                transition: "background 0.3s"
              }} />
            ))}
          </div>
        </div>
      )}

      {tailored && phase !== "tailoring" && (
        <div className="card">
          <div className="card-title" style={{ color: "var(--green)" }}>✓ resume_tailored</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", margin: 0 }}>
            Career objective, experience bullets, and skills have been rewritten for this role.
          </p>
          <button
            className="btn btn-ghost"
            style={{ marginTop: "0.75rem", fontSize: "0.82rem" }}
            onClick={() => { onResumeChange(preResume); setTailored(false); setPhase("idle"); }}
          >
            Revert to original
          </button>
        </div>
      )}

      {atsResult && (
        <div className="card">
          <div className="card-title">// ats_score</div>
          <div className="grid-2" style={{ marginBottom: "1.5rem" }}>
            <div className="stat-box">
              <div className="stat-val">{atsResult.ats_score}</div>
              <div className="stat-label">ATS Score</div>
            </div>
            <div className="stat-box">
              <div className="stat-val">{atsResult.keyword_match}</div>
              <div className="stat-label">Keyword Match</div>
            </div>
          </div>
          <ScoreBar label="Experience Match" value={atsResult.experience_match} />
          <ScoreBar label="Skills Match" value={atsResult.skills_match} />
          <div className="grid-2">
            <div>
              <div className="card-title" style={{ marginTop: "1rem" }}>Strengths</div>
              {atsResult.strengths.map((s, i) => (
                <div key={i} style={{ color: "var(--green)", fontSize: "0.85rem", marginBottom: "0.3rem" }}>✓ {s}</div>
              ))}
            </div>
            <div>
              <div className="card-title" style={{ marginTop: "1rem" }}>Weaknesses</div>
              {atsResult.weaknesses.map((w, i) => (
                <div key={i} style={{ color: "var(--red)", fontSize: "0.85rem", marginBottom: "0.3rem" }}>✗ {w}</div>
              ))}
            </div>
          </div>
          {atsResult.missing_keywords.length > 0 && (
            <div style={{ marginTop: "1rem" }}>
              <div className="card-title">Missing Keywords</div>
              <div>{atsResult.missing_keywords.map((k, i) => <span key={i} className="tag">{k}</span>)}</div>
            </div>
          )}
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
            <button className="btn btn-ghost" onClick={handleRegenerateAts} disabled={loadingAts}>
              {loadingAts ? <span className="spinner" /> : null}
              Re-score
            </button>
            {atsResult.ats_score < 75 && (
              <button className="btn btn-ghost" onClick={handleImproveFromAts} disabled={loadingAts}>
                Improve from ATS gaps
              </button>
            )}
          </div>
        </div>
      )}

      {coverLetter && (
        <div className="card">
          <div className="card-title">// cover_letter</div>
          {typeof coverLetter.subject === "string" && (
            <div style={{ fontWeight: 600, marginBottom: "0.75rem" }}>{coverLetter.subject as string}</div>
          )}
          {Array.isArray(coverLetter.body_points) && (coverLetter.body_points as string[]).map((p, i) => (
            <p key={i} style={{ color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.7, marginBottom: "0.75rem" }}>{p}</p>
          ))}
          <button className="btn btn-ghost" style={{ marginTop: "0.5rem" }} onClick={handleRegenerateCover} disabled={loadingCover}>
            {loadingCover ? <span className="spinner" /> : null}
            Regenerate cover letter
          </button>
        </div>
      )}

      {phase === "done" && (
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
          <button className="btn btn-ghost" onClick={onBack}>← Back</button>
          <button className="btn btn-primary" onClick={onNext}>Download PDFs →</button>
        </div>
      )}
      {phase === "idle" && tailored && (
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
          <button className="btn btn-ghost" onClick={onBack}>← Back</button>
          <button className="btn btn-primary" onClick={onNext}>Download PDFs →</button>
        </div>
      )}
    </div>
  );
}
