"use client";
import { Section } from "./App";

const NAV = [
  { id: "resume" as Section, label: "Resume Data", icon: "📄" },
  { id: "ai" as Section, label: "AI Tools", icon: "✦" },
  { id: "pdf" as Section, label: "PDF Export", icon: "⬇" },
];

export default function Sidebar({
  active,
  onChange,
  onLogout,
}: {
  active: Section;
  onChange: (s: Section) => void;
  onLogout: () => void;
}) {
  return (
    <nav className="sidebar">
      <div className="sidebar-logo">AI Resume Gen</div>
      {NAV.map(item => (
        <button
          key={item.id}
          className={`nav-item${active === item.id ? " active" : ""}`}
          onClick={() => onChange(item.id)}
        >
          <span>{item.icon}</span>
          {item.label}
        </button>
      ))}
      <div style={{ flex: 1 }} />
      <button className="nav-item" onClick={onLogout} style={{ marginTop: "auto" }}>
        <span>↩</span> Logout
      </button>
    </nav>
  );
}
