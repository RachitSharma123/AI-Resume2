import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Resume Builder — Land Your Dream Job",
  description: "Free AI-powered resume tailoring. Upload your resume, paste any job description, and get an ATS-optimised resume + cover letter in seconds.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
