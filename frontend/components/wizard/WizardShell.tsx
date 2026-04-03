"use client";
import { useState, useEffect } from "react";
import { getResume, saveResume, clearResume } from "@/lib/api";
import StepUpload from "./StepUpload";
import StepReview from "./StepReview";
import StepJobDescription from "./StepJobDescription";
import StepGenerate from "./StepGenerate";
import StepDownload from "./StepDownload";

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

const STEPS = [
  { n: 1, label: "Upload" },
  { n: 2, label: "Review" },
  { n: 3, label: "Job Description" },
  { n: 4, label: "Generate" },
  { n: 5, label: "Download" },
];

export default function WizardShell() {
  const [step, setStep] = useState(1);
  const [resume, setResume] = useState<Record<string, unknown> | null>(null);
  const [jobDescription, setJobDescription] = useState("");
  const [atsResult, setAtsResult] = useState<ATSResult | null>(null);
  const [coverLetter, setCoverLetter] = useState<Record<string, unknown> | null>(null);
  const [showRecovery, setShowRecovery] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = getResume();
    if (saved) setShowRecovery(true);
    setReady(true);
  }, []);

  function handleResumeChange(data: Record<string, unknown>) {
    setResume(data);
    saveResume(data);
  }

  function handleStartOver() {
    clearResume();
    setResume(null);
    setJobDescription("");
    setAtsResult(null);
    setCoverLetter(null);
    setStep(1);
    setShowRecovery(false);
  }

  if (!ready) return <div style={{ background: "var(--bg)", minHeight: "100vh" }} />;

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      {/* Top bar */}
      <header style={{
        background: "var(--bg2)",
        borderBottom: "1px solid var(--border)",
        padding: "0 2rem",
        position: "sticky",
        top: 0,
        zIndex: 10,
      }}>
        <div style={{ maxWidth: 860, margin: "0 auto", display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.9rem 0" }}>
          <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--accent)", letterSpacing: "0.1em", marginRight: "1.5rem" }}>
            AI RESUME
          </span>
          <div style={{ display: "flex", gap: "0.25rem", flex: 1 }}>
            {STEPS.map(s => {
              const done = step > s.n;
              const active = step === s.n;
              return (
                <button
                  key={s.n}
                  onClick={() => done && setStep(s.n)}
                  style={{
                    flex: 1,
                    padding: "0.35rem 0.25rem",
                    fontSize: "0.75rem",
                    background: "none",
                    border: "none",
                    borderBottom: active ? "2px solid var(--accent)" : done ? "2px solid var(--green)" : "2px solid var(--border)",
                    color: active ? "var(--accent)" : done ? "var(--green)" : "var(--muted)",
                    cursor: done ? "pointer" : "default",
                    transition: "all 0.15s",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {done ? "✓ " : `${s.n}. `}{s.label}
                </button>
              );
            })}
          </div>
        </div>
      </header>

      {/* Session recovery banner */}
      {showRecovery && step === 1 && (
        <div style={{
          background: "rgba(245,166,35,0.08)",
          borderBottom: "1px solid rgba(245,166,35,0.25)",
          padding: "0.75rem 2rem",
          display: "flex",
          alignItems: "center",
          gap: "1rem",
          justifyContent: "center",
          fontSize: "0.88rem",
        }}>
          <span style={{ color: "var(--muted)" }}>You have a saved resume from a previous session.</span>
          <button
            className="btn btn-primary"
            style={{ padding: "0.3rem 0.85rem", fontSize: "0.82rem" }}
            onClick={() => { setResume(getResume()); setStep(2); setShowRecovery(false); }}
          >
            Continue
          </button>
          <button
            className="btn btn-ghost"
            style={{ padding: "0.3rem 0.85rem", fontSize: "0.82rem" }}
            onClick={handleStartOver}
          >
            Start fresh
          </button>
        </div>
      )}

      {/* Content */}
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "2rem" }}>
        {step === 1 && (
          <StepUpload
            onComplete={data => { handleResumeChange(data); setStep(2); }}
          />
        )}
        {step === 2 && resume && (
          <StepReview
            resume={resume}
            onChange={handleResumeChange}
            onNext={() => setStep(3)}
            onBack={() => setStep(1)}
          />
        )}
        {step === 3 && (
          <StepJobDescription
            jobDescription={jobDescription}
            onChange={setJobDescription}
            onNext={() => setStep(4)}
            onBack={() => setStep(2)}
          />
        )}
        {step === 4 && resume && (
          <StepGenerate
            resume={resume}
            jobDescription={jobDescription}
            onResumeChange={handleResumeChange}
            onAtsResult={setAtsResult}
            onCoverLetterChange={cl => { setCoverLetter(cl); }}
            atsResult={atsResult}
            coverLetter={coverLetter}
            onNext={() => setStep(5)}
            onBack={() => setStep(3)}
          />
        )}
        {step === 5 && resume && (
          <StepDownload
            resume={resume}
            onResumeChange={handleResumeChange}
            onBack={() => setStep(4)}
            onStartOver={handleStartOver}
          />
        )}
      </main>
    </div>
  );
}
