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
  { n: 1, label: "Your Resume" },
  { n: 2, label: "Looks Good?" },
  { n: 3, label: "Target Role" },
  { n: 4, label: "AI Magic" },
  { n: 5, label: "You're Ready!" },
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
        background: "linear-gradient(135deg, #fff8ee 0%, #fffdf9 100%)",
        borderBottom: "1px solid var(--border)",
        padding: "0 2rem",
        position: "sticky",
        top: 0,
        zIndex: 10,
        boxShadow: "0 1px 8px rgba(180,90,0,0.07)",
      }}>
        <div style={{ maxWidth: 860, margin: "0 auto", display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.85rem 0" }}>
          <button
            onClick={handleStartOver}
            title="Start a new session"
            className="wizard-logo"
            style={{ marginRight: "1.5rem", flexShrink: 0, background: "none", border: "none", padding: 0, cursor: "pointer", textAlign: "left" }}
          >
            <div style={{ fontSize: "0.95rem", fontWeight: 800, color: "var(--accent2)", letterSpacing: "-0.01em", lineHeight: 1.1, whiteSpace: "nowrap" }}>
              ✨ Resume Builder
            </div>
            <div className="logo-sub" style={{ fontSize: "0.65rem", color: "var(--muted)", fontWeight: 600, letterSpacing: "0.05em", textTransform: "uppercase" }}>
              Free · Powered by AI
            </div>
          </button>
          <div className="wizard-header-steps" style={{ display: "flex", gap: "0.25rem", flex: 1, minWidth: 0 }}>
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
                    fontSize: "0.72rem",
                    fontWeight: active ? 700 : 500,
                    background: "none",
                    border: "none",
                    borderBottom: active ? "2.5px solid var(--accent)" : done ? "2.5px solid var(--green)" : "2.5px solid var(--border)",
                    color: active ? "var(--accent2)" : done ? "var(--green)" : "var(--muted)",
                    cursor: done ? "pointer" : "default",
                    transition: "all 0.15s",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                  }}
                >
                  <span className="step-dot" style={{ display: "none" }}>
                    {done ? "✓" : active ? "●" : "○"}
                  </span>
                  <span className="step-label">
                    {done ? "✓ " : ""}{s.label}
                  </span>
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
          <span style={{ color: "var(--muted)" }}>Welcome back! You have a resume saved from last time.</span>
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
      <main style={{ maxWidth: 860, margin: "0 auto", padding: "2rem", paddingBottom: "5rem" }}>
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
      {/* Footer */}
      <div style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 20,
        textAlign: "center",
        padding: "10px 1rem 12px",
        background: "linear-gradient(to top, var(--bg2) 80%, transparent)",
        pointerEvents: "none",
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "var(--accent2)", letterSpacing: "1.5px", textTransform: "uppercase", marginBottom: 5 }}>
          Crafted by Rachit Sharma
        </div>
        <div style={{ fontSize: 11, display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", alignItems: "center" }}>
          {[
            { label: "GitHub", url: "https://github.com/RachitSharma123" },
            { label: "LinkedIn", url: "https://www.linkedin.com/in/rachit-sharma-0b9b44117/" },
            { label: "Instagram", url: "https://www.instagram.com/rachitsharma_a/" },
            { label: "mode3.au", url: "https://mode3.au" },
            { label: "aussieai.shop", url: "https://www.aussieai.shop" },
            { label: "rachitsharma.space", url: "https://www.rachitsharma.space" },
            { label: "rsharma.cv", url: "https://www.rsharma.cv" },
          ].map((link, i, arr) => (
            <span key={link.url} style={{ display: "flex", alignItems: "center", gap: 12, pointerEvents: "auto" }}>
              <a href={link.url} target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent2)", textDecoration: "none", fontWeight: 600 }}>
                {link.label}
              </a>
              {i < arr.length - 1 && <span style={{ color: "var(--border)" }}>·</span>}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
