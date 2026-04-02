"use client";
import { useState } from "react";

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

export default function ResumeSection({
  resume,
  onChange,
}: {
  resume: Record<string, unknown> | null;
  onChange: (data: Record<string, unknown>) => void;
}) {
  const [raw, setRaw] = useState(() => JSON.stringify(resume || DEFAULT_RESUME, null, 2));
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  function handleSave() {
    setError("");
    try {
      const parsed = JSON.parse(raw);
      onChange(parsed);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Invalid JSON — check your syntax.");
    }
  }

  function handleFileUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const parsed = JSON.parse(ev.target?.result as string);
        setRaw(JSON.stringify(parsed, null, 2));
        onChange(parsed);
      } catch {
        setError("Could not parse uploaded JSON file.");
      }
    };
    reader.readAsText(file);
  }

  return (
    <div>
      <div className="page-title">Resume Data</div>
      <div className="page-sub">Edit your base resume JSON. This data is used by all AI tools.</div>

      <div className="card">
        <div className="card-title">// resume.json</div>
        {error && <div className="alert alert-error">{error}</div>}
        {saved && <div className="alert alert-success">Saved to session.</div>}
        <textarea
          value={raw}
          onChange={e => setRaw(e.target.value)}
          style={{ minHeight: "400px", fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
          spellCheck={false}
        />
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem", alignItems: "center" }}>
          <button className="btn btn-primary" onClick={handleSave}>Save Changes</button>
          <label className="btn btn-ghost" style={{ cursor: "pointer" }}>
            Upload JSON
            <input type="file" accept=".json" onChange={handleFileUpload} style={{ display: "none" }} />
          </label>
          <button
            className="btn btn-ghost"
            onClick={() => {
              setRaw(JSON.stringify(DEFAULT_RESUME, null, 2));
              onChange(DEFAULT_RESUME);
            }}
          >
            Load Template
          </button>
        </div>
      </div>

      {resume && (
        <div className="card">
          <div className="card-title">// preview</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginBottom: "0.75rem" }}>
            {typeof resume.name === "string" && (
              <span style={{ color: "var(--white)", fontWeight: 600 }}>{resume.name}</span>
            )}
            {typeof resume.contact === "string" && (
              <span style={{ color: "var(--muted)", fontSize: "0.85rem" }}>{resume.contact}</span>
            )}
          </div>
          {typeof resume.career_objective === "string" && (
            <p style={{ color: "var(--muted)", fontSize: "0.88rem", lineHeight: 1.6, marginBottom: "1rem" }}>
              {resume.career_objective}
            </p>
          )}
          {Array.isArray(resume.experience) && (
            <div style={{ fontSize: "0.82rem", color: "var(--muted)" }}>
              {(resume.experience as Array<{ company?: string; role_line?: string }>).map((exp, i) => (
                <div key={i} style={{ marginBottom: "0.4rem" }}>
                  <span style={{ color: "var(--white)" }}>{exp.company}</span>
                  {exp.role_line && <span> — {exp.role_line}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
