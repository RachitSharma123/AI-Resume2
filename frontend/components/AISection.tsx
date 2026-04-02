"use client";
import { useState } from "react";
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

export default function AISection({
  resume,
  onChange,
}: {
  resume: Record<string, unknown> | null;
  onChange: (data: Record<string, unknown>) => void;
}) {
  const [tab, setTab] = useState<"tailor" | "ats" | "cover" | "improve" | "compress">("tailor");
  const [jd, setJd] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [atsResult, setAtsResult] = useState<ATSResult | null>(null);
  const [coverLetter, setCoverLetter] = useState<Record<string, unknown> | null>(null);
  const [improvedBullets, setImprovedBullets] = useState<string[] | null>(null);
  const [bulletInput, setBulletInput] = useState("");

  function requireResume() {
    if (!resume) {
      setError("No resume loaded. Go to Resume Data and save your resume first.");
      return false;
    }
    if (!jd.trim() && tab !== "compress" && tab !== "improve") {
      setError("Paste a job description first.");
      return false;
    }
    return true;
  }

  async function handleTailor() {
    if (!requireResume()) return;
    setLoading(true); setError(""); setSuccess("");
    try {
      const res = await api.tailor(resume!, jd);
      onChange(res.resume);
      setSuccess("Resume tailored! Your resume data has been updated.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Tailor failed");
    } finally { setLoading(false); }
  }

  async function handleATS() {
    if (!requireResume()) return;
    setLoading(true); setError(""); setAtsResult(null);
    try {
      const res = await api.atsScore(resume!, jd);
      setAtsResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "ATS analysis failed");
    } finally { setLoading(false); }
  }

  async function handleCoverLetter() {
    if (!requireResume()) return;
    setLoading(true); setError(""); setCoverLetter(null);
    try {
      const res = await api.coverLetter(resume!, jd);
      setCoverLetter(res.cover_letter);
      // Merge cover_letter into resume
      onChange({ ...resume!, cover_letter: res.cover_letter });
      setSuccess("Cover letter generated and merged into resume data.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Cover letter generation failed");
    } finally { setLoading(false); }
  }

  async function handleImprove() {
    if (!resume) { setError("No resume loaded."); return; }
    if (!bulletInput.trim()) { setError("Enter bullet points (one per line)."); return; }
    if (!jd.trim()) { setError("Paste a job description."); return; }
    setLoading(true); setError(""); setImprovedBullets(null);
    const bullets = bulletInput.split("\n").map(b => b.trim()).filter(Boolean);
    try {
      const res = await api.improveBullets(bullets, jd);
      setImprovedBullets(res.bullets);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Improve failed");
    } finally { setLoading(false); }
  }

  async function handleCompress() {
    if (!resume) { setError("No resume loaded."); return; }
    setLoading(true); setError(""); setSuccess("");
    try {
      const res = await api.compress(resume);
      onChange(res.resume);
      setSuccess("Resume compressed to 1-page layout.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Compress failed");
    } finally { setLoading(false); }
  }

  async function handleImproveFromATS() {
    if (!resume || !atsResult) { setError("Run ATS analysis first."); return; }
    setLoading(true); setError(""); setSuccess("");
    try {
      const res = await api.improveFromAts(resume, atsResult, jd);
      onChange(res.resume);
      setSuccess("Resume improved based on ATS gaps.");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Improve from ATS failed");
    } finally { setLoading(false); }
  }

  const TABS = [
    { id: "tailor", label: "Tailor" },
    { id: "ats", label: "ATS Score" },
    { id: "cover", label: "Cover Letter" },
    { id: "improve", label: "Bullets" },
    { id: "compress", label: "Compress" },
  ] as const;

  return (
    <div>
      <div className="page-title">AI Tools</div>
      <div className="page-sub">Powered by OpenAI. All changes update your resume session data.</div>

      {/* Tab bar */}
      <div style={{ display: "flex", gap: "0.25rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`btn ${tab === t.id ? "btn-primary" : "btn-ghost"}`}
            onClick={() => { setTab(t.id); setError(""); setSuccess(""); }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {/* Job Description (shared) */}
      {tab !== "compress" && (
        <div className="card">
          <div className="card-title">// job_description</div>
          <textarea
            placeholder="Paste the full job description here…"
            value={jd}
            onChange={e => setJd(e.target.value)}
            style={{ minHeight: "180px" }}
          />
        </div>
      )}

      {/* Tailor */}
      {tab === "tailor" && (
        <div className="card">
          <div className="card-title">// tailor_resume</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
            AI rewrites your resume to match the job description — ATS keywords, bullet points, objective, skills.
          </p>
          <button className="btn btn-primary" onClick={handleTailor} disabled={loading}>
            {loading ? <span className="spinner" /> : null}
            {loading ? "Tailoring…" : "Tailor Resume →"}
          </button>
        </div>
      )}

      {/* ATS Score */}
      {tab === "ats" && (
        <div className="card">
          <div className="card-title">// ats_analysis</div>
          <div style={{ display: "flex", gap: "0.75rem", marginBottom: atsResult ? "1.5rem" : 0 }}>
            <button className="btn btn-primary" onClick={handleATS} disabled={loading}>
              {loading ? <span className="spinner" /> : null}
              {loading ? "Analysing…" : "Analyse ATS Score →"}
            </button>
            {atsResult && (
              <button className="btn btn-ghost" onClick={handleImproveFromATS} disabled={loading}>
                Improve from ATS
              </button>
            )}
          </div>
          {atsResult && (
            <div style={{ marginTop: "1.5rem" }}>
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
              {atsResult.suggestions.length > 0 && (
                <div style={{ marginTop: "1rem" }}>
                  <div className="card-title">Suggestions</div>
                  {atsResult.suggestions.map((s, i) => (
                    <div key={i} style={{ color: "var(--accent)", fontSize: "0.85rem", marginBottom: "0.3rem" }}>→ {s}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Cover Letter */}
      {tab === "cover" && (
        <div className="card">
          <div className="card-title">// cover_letter_generator</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
            Generates a human-sounding cover letter. Result is merged into your resume data for PDF export.
          </p>
          <button className="btn btn-primary" onClick={handleCoverLetter} disabled={loading}>
            {loading ? <span className="spinner" /> : null}
            {loading ? "Generating…" : "Generate Cover Letter →"}
          </button>
          {coverLetter && (
            <div style={{ marginTop: "1.5rem", border: "1px solid var(--border)", borderRadius: 4, padding: "1.25rem" }}>
              <div className="card-title">Generated Cover Letter</div>
              {typeof coverLetter.subject === "string" && (
                <div style={{ fontWeight: 600, marginBottom: "0.75rem" }}>{coverLetter.subject as string}</div>
              )}
              {Array.isArray(coverLetter.body_points) && (coverLetter.body_points as string[]).map((p, i) => (
                <p key={i} style={{ color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.7, marginBottom: "0.75rem" }}>{p}</p>
              ))}
              {typeof coverLetter.closing === "string" && (
                <div style={{ color: "var(--muted)", fontSize: "0.88rem" }}>{coverLetter.closing as string}</div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Improve Bullets */}
      {tab === "improve" && (
        <div className="card">
          <div className="card-title">// improve_bullets</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
            Paste bullet points (one per line). AI rewrites them using STAR method + metrics.
          </p>
          <div style={{ marginBottom: "1rem" }}>
            <label>Bullet Points (one per line)</label>
            <textarea
              placeholder={"Managed a team of developers\nReduced load time by optimizing queries"}
              value={bulletInput}
              onChange={e => setBulletInput(e.target.value)}
              style={{ minHeight: "140px" }}
            />
          </div>
          <button className="btn btn-primary" onClick={handleImprove} disabled={loading}>
            {loading ? <span className="spinner" /> : null}
            {loading ? "Improving…" : "Improve Bullets →"}
          </button>
          {improvedBullets && (
            <div style={{ marginTop: "1.5rem" }}>
              <div className="card-title">Improved Bullets</div>
              {improvedBullets.map((b, i) => (
                <div key={i} style={{ color: "var(--green)", fontSize: "0.88rem", marginBottom: "0.5rem", lineHeight: 1.6 }}>
                  • {b}
                </div>
              ))}
              <button
                className="btn btn-ghost"
                style={{ marginTop: "0.75rem" }}
                onClick={() => {
                  setBulletInput(improvedBullets.join("\n"));
                  setImprovedBullets(null);
                }}
              >
                ← Copy back to input
              </button>
            </div>
          )}
        </div>
      )}

      {/* Compress */}
      {tab === "compress" && (
        <div className="card">
          <div className="card-title">// compress_to_one_page</div>
          <p style={{ color: "var(--muted)", fontSize: "0.88rem", marginBottom: "1rem" }}>
            Trims bullet points, shortens objective, removes redundancy — fits your resume to one page.
          </p>
          <button className="btn btn-primary" onClick={handleCompress} disabled={loading}>
            {loading ? <span className="spinner" /> : null}
            {loading ? "Compressing…" : "Compress Resume →"}
          </button>
        </div>
      )}
    </div>
  );
}
