"use client";
import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";

type Keywords = {
  role_title?: string;
  required_skills?: string[];
  key_technologies?: string[];
  experience_level?: string;
};

export default function StepJobDescription({
  jobDescription,
  onChange,
  onNext,
  onBack,
}: {
  jobDescription: string;
  onChange: (jd: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [keywords, setKeywords] = useState<Keywords | null>(null);
  const [loadingKeywords, setLoadingKeywords] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!jobDescription.trim() || jobDescription.length < 100) {
      setKeywords(null);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoadingKeywords(true);
      try {
        const res = await api.extractKeywords(jobDescription);
        setKeywords(res);
      } catch {
        // silently fail — keyword preview is optional
      } finally {
        setLoadingKeywords(false);
      }
    }, 900);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [jobDescription]);

  const allTags = [
    ...(keywords?.required_skills || []),
    ...(keywords?.key_technologies || []),
  ].slice(0, 12);

  return (
    <div>
      <div className="page-title">Found your dream role? Let's go.</div>
      <div className="page-sub">Paste the job description below — AI will rewrite your resume to match it perfectly and boost your ATS score.</div>

      <div className="card">
        <div className="card-title">// job_description</div>
        <textarea
          value={jobDescription}
          onChange={e => onChange(e.target.value)}
          placeholder="Paste the full job description here…"
          style={{ minHeight: "280px" }}
        />
      </div>

      {/* Keyword preview */}
      {(loadingKeywords || keywords) && (
        <div className="card">
          <div className="card-title">// detected_keywords</div>
          {loadingKeywords ? (
            <div style={{ color: "var(--muted)", fontSize: "0.85rem" }}>Analysing job description…</div>
          ) : keywords && (
            <div>
              {keywords.role_title && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>Role: </span>
                  <span style={{ color: "var(--accent)", fontWeight: 600 }}>{keywords.role_title}</span>
                  {keywords.experience_level && (
                    <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}> · {keywords.experience_level}</span>
                  )}
                </div>
              )}
              {allTags.length > 0 && (
                <div>{allTags.map((k, i) => <span key={i} className="tag">{k}</span>)}</div>
              )}
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button
          className="btn btn-primary"
          onClick={onNext}
          disabled={!jobDescription.trim()}
        >
          Analyse &amp; Tailor →
        </button>
      </div>
    </div>
  );
}
