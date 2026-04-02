const BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("ar_token") || "";
}

export function setToken(token: string) {
  localStorage.setItem("ar_token", token);
}

export function clearToken() {
  localStorage.removeItem("ar_token");
  localStorage.removeItem("ar_resume");
}

export function getResume(): Record<string, unknown> | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("ar_resume");
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

export function saveResume(data: Record<string, unknown>) {
  localStorage.setItem("ar_resume", JSON.stringify(data));
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "x-token": token,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

export const api = {
  login: (password: string) =>
    apiFetch("/login", { method: "POST", body: JSON.stringify({ password }) }),

  tailor: (resume: object, job_description: string) =>
    apiFetch("/tailor", { method: "POST", body: JSON.stringify({ resume, job_description }) }),

  coverLetter: (resume: object, job_description: string) =>
    apiFetch("/cover-letter", { method: "POST", body: JSON.stringify({ resume, job_description }) }),

  atsScore: (resume: object, job_description: string) =>
    apiFetch("/ats-score", { method: "POST", body: JSON.stringify({ resume, job_description }) }),

  improveBullets: (bullets: string[], job_description: string) =>
    apiFetch("/improve-bullets", { method: "POST", body: JSON.stringify({ bullets, job_description }) }),

  compress: (resume: object) =>
    apiFetch("/compress", { method: "POST", body: JSON.stringify({ resume }) }),

  improveFromAts: (resume: object, ats_results: object, job_description: string) =>
    apiFetch("/improve-from-ats", { method: "POST", body: JSON.stringify({ resume, ats_results, job_description }) }),

  pdfResume: (resume: object) =>
    apiFetch("/pdf/resume", { method: "POST", body: JSON.stringify({ resume }) }),

  pdfCoverLetter: (resume: object) =>
    apiFetch("/pdf/cover-letter", { method: "POST", body: JSON.stringify({ resume }) }),

  health: () => apiFetch("/health"),
};

export function downloadPdf(b64: string, filename: string) {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  const blob = new Blob([arr], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
