"use client";
import { useState, useEffect } from "react";
import Login from "./Login";
import Sidebar from "./Sidebar";
import ResumeSection from "./ResumeSection";
import AISection from "./AISection";
import PDFSection from "./PDFSection";
import { getToken, getResume, saveResume, clearToken } from "@/lib/api";

export type Section = "resume" | "ai" | "pdf";

export default function App() {
  const [authed, setAuthed] = useState(false);
  const [section, setSection] = useState<Section>("resume");
  const [resume, setResume] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (token) setAuthed(true);
    const saved = getResume();
    if (saved) setResume(saved);
    setLoading(false);
  }, []);

  function handleResumeChange(data: Record<string, unknown>) {
    setResume(data);
    saveResume(data);
  }

  function handleLogout() {
    clearToken();
    setAuthed(false);
  }

  if (loading) return <div style={{ background: "var(--bg)", minHeight: "100vh" }} />;

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  return (
    <div className="app-shell">
      <Sidebar active={section} onChange={setSection} onLogout={handleLogout} />
      <main className="main-content">
        {section === "resume" && (
          <ResumeSection resume={resume} onChange={handleResumeChange} />
        )}
        {section === "ai" && (
          <AISection resume={resume} onChange={handleResumeChange} />
        )}
        {section === "pdf" && (
          <PDFSection resume={resume} />
        )}
      </main>
    </div>
  );
}
