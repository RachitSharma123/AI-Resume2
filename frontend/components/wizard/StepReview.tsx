"use client";
import { useState } from "react";

type Experience = { company: string; role_line: string; bullets: string[] };
type Education = { degree: string; details: string };
type Skill = { label: string; value: string };

export default function StepReview({
  resume,
  onChange,
  onNext,
  onBack,
}: {
  resume: Record<string, unknown>;
  onChange: (data: Record<string, unknown>) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const [showRaw, setShowRaw] = useState(false);
  const [rawText, setRawText] = useState(JSON.stringify(resume, null, 2));
  const [rawError, setRawError] = useState("");

  const name = (resume.name as string) || "";
  const contact = (resume.contact as string) || "";
  const objective = (resume.career_objective as string) || "";
  const skills = (resume.skills_snapshot as Skill[]) || [];
  const experience = (resume.experience as Experience[]) || [];
  const education = (resume.education as Education[]) || [];

  function update(patch: Partial<Record<string, unknown>>) {
    const updated = { ...resume, ...patch };
    onChange(updated);
    setRawText(JSON.stringify(updated, null, 2));
  }

  function updateExp(i: number, patch: Partial<Experience>) {
    const exp = [...experience];
    exp[i] = { ...exp[i], ...patch };
    update({ experience: exp });
  }

  function updateExpBullet(ei: number, bi: number, val: string) {
    const exp = [...experience];
    const bullets = [...exp[ei].bullets];
    bullets[bi] = val;
    exp[ei] = { ...exp[ei], bullets };
    update({ experience: exp });
  }

  function updateSkill(i: number, patch: Partial<Skill>) {
    const s = [...skills];
    s[i] = { ...s[i], ...patch };
    update({ skills_snapshot: s });
  }

  function saveRaw() {
    setRawError("");
    try {
      const parsed = JSON.parse(rawText);
      onChange(parsed);
      setShowRaw(false);
    } catch {
      setRawError("Invalid JSON — check your syntax.");
    }
  }

  return (
    <div>
      <div className="page-title">Review Extracted Data</div>
      <div className="page-sub">Check what was extracted from your PDF. Edit any fields before continuing.</div>

      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", alignItems: "center" }}>
        <button
          className={`btn ${showRaw ? "btn-primary" : "btn-ghost"}`}
          style={{ fontSize: "0.82rem" }}
          onClick={() => { setShowRaw(!showRaw); setRawText(JSON.stringify(resume, null, 2)); setRawError(""); }}
        >
          {showRaw ? "← Back to Form" : "View / Edit Raw JSON"}
        </button>
      </div>

      {showRaw ? (
        <div className="card">
          <div className="card-title">// resume.json</div>
          {rawError && <div className="alert alert-error">{rawError}</div>}
          <textarea
            value={rawText}
            onChange={e => setRawText(e.target.value)}
            style={{ minHeight: "400px", fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}
            spellCheck={false}
          />
          <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem" }}>
            <button className="btn btn-primary" onClick={saveRaw}>Save JSON</button>
          </div>
        </div>
      ) : (
        <>
          {/* Basic Info */}
          <div className="card">
            <div className="card-title">// basic_info</div>
            <div style={{ display: "grid", gap: "0.75rem" }}>
              <div>
                <label>Name</label>
                <input value={name} onChange={e => update({ name: e.target.value })} />
              </div>
              <div>
                <label>Contact</label>
                <input value={contact} onChange={e => update({ contact: e.target.value })} />
              </div>
              <div>
                <label>Career Objective</label>
                <textarea
                  value={objective}
                  onChange={e => update({ career_objective: e.target.value })}
                  style={{ minHeight: "100px" }}
                />
              </div>
            </div>
          </div>

          {/* Skills */}
          <div className="card">
            <div className="card-title">// skills_snapshot</div>
            {skills.map((s, i) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: "0.5rem", marginBottom: "0.5rem" }}>
                <input
                  value={s.label}
                  onChange={e => updateSkill(i, { label: e.target.value })}
                  placeholder="Category"
                />
                <input
                  value={s.value}
                  onChange={e => updateSkill(i, { value: e.target.value })}
                  placeholder="Skills (comma separated)"
                />
              </div>
            ))}
          </div>

          {/* Experience */}
          <div className="card">
            <div className="card-title">// experience</div>
            {experience.map((exp, ei) => (
              <div key={ei} style={{ marginBottom: "1.5rem", borderBottom: "1px solid var(--border)", paddingBottom: "1.25rem" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.75rem" }}>
                  <input
                    value={exp.company}
                    onChange={e => updateExp(ei, { company: e.target.value })}
                    placeholder="Company"
                  />
                  <input
                    value={exp.role_line}
                    onChange={e => updateExp(ei, { role_line: e.target.value })}
                    placeholder="Job Title | Start – End"
                  />
                </div>
                <div style={{ display: "grid", gap: "0.4rem" }}>
                  {exp.bullets.map((b, bi) => (
                    <textarea
                      key={bi}
                      value={b}
                      onChange={e => updateExpBullet(ei, bi, e.target.value)}
                      style={{ minHeight: "48px", fontSize: "0.85rem", resize: "vertical" }}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Education */}
          <div className="card">
            <div className="card-title">// education</div>
            {education.map((ed, i) => (
              <div key={i} style={{ display: "grid", gap: "0.5rem", marginBottom: "0.75rem" }}>
                <input
                  value={ed.degree}
                  onChange={e => {
                    const edu = [...education];
                    edu[i] = { ...edu[i], degree: e.target.value };
                    update({ education: edu });
                  }}
                  placeholder="Degree"
                />
                <input
                  value={ed.details}
                  onChange={e => {
                    const edu = [...education];
                    edu[i] = { ...edu[i], details: e.target.value };
                    update({ education: edu });
                  }}
                  placeholder="University | Year"
                />
              </div>
            ))}
          </div>
        </>
      )}

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1.5rem" }}>
        <button className="btn btn-ghost" onClick={onBack}>← Back</button>
        <button className="btn btn-primary" onClick={onNext}>Looks Good — Add Job Description →</button>
      </div>
    </div>
  );
}
