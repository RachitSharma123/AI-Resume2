# ai_functions.py
import json
import re
from openai import OpenAI
import streamlit as st

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def call_ai_tailor_resume(base_resume_json: dict, job_description: str, model: str = "gpt-4o") -> dict:
    """Tailor resume to match job description with ATS optimization."""
    system_prompt = (
        "You are an elite ATS-optimization and hiring strategist.\n"
        "Your ONLY goal is to modify the resume JSON so that it maximizes shortlisting and interview chances for the given Job Description.\n\n"
        "STRICT RULES (DO NOT BREAK):\n"
        "1. NAME must NEVER change.\n"
        "2. EDUCATION must NEVER be removed (you MAY add relevant certifications/coursework).\n"
        "3. Output MUST be valid JSON only. No explanations, no markdown, no backticks.\n"
        "4. You ARE ALLOWED to:\n"
        "   - Rewrite career_objective aggressively for alignment\n"
        "   - Modify job titles to be closer to the target role\n"
        "   - Rewrite experience bullet points using STAR + impact + metrics\n"
        "   - Add/modify SKILLS and CERTIFICATIONS (realistic ones only)\n"
        "5. You MUST:\n"
        "   - Optimize for ATS keywords from the job description\n"
        "   - Mirror language from the Job Description\n"
        "   - Prioritize business impact, tools, and quantifiable outcomes\n"
        "6. Do NOT invent fake companies or degrees.\n"
        "7. Do NOT downgrade experience - enhance it to match the target level.\n\n"
        "OUTPUT: Return the FULL resume JSON with identical structure."
    )

    user_prompt = json.dumps({
        "resume_json": base_resume_json,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        text = resp.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        # Extract JSON if wrapped
        m = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        return json.loads(text)
    except Exception as e:
        raise Exception(f"AI Tailor failed: {str(e)}")


def call_ai_generate_cover_letter(resume_json: dict, job_description: str, model: str = "gpt-4o") -> dict:
    """Generate cover letter JSON from resume and job description."""
    system_prompt = (
        "You write concise, high-converting cover letters for professional roles.\n"
        "Return ONLY valid JSON (no markdown, no backticks).\n\n"
        "Task: Create a 'cover_letter' object with these keys:\n"
        "- date: 'AUTO'\n"
        "- recipient: string (e.g., 'Hiring Manager')\n"
        "- company: string\n"
        "- role_title: string\n"
        "- company_address: string (optional)\n"
        "- subject: string (e.g., 'Re: Application for [Role Title]')\n"
        "- opening: string (first paragraph after greeting)\n"
        "- body_points: list of 3-4 paragraphs (NOT bullet points)\n"
        "- closing: string (e.g., 'Kind regards,')\n"
        "- signature_name: string (from resume)\n"
        "- phone_number: string (phone only, no email)\n"
        "- email: string\n\n"
        "Use resume + job description for alignment. Mirror JD language.\n"
        "Keep it professional, 1 page, and focused on value proposition."
    )

    user_prompt = json.dumps({
        "resume_json": resume_json,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        text = resp.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        m = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        out = json.loads(text)
        return out.get("cover_letter", out)
    except Exception as e:
        raise Exception(f"Cover letter generation failed: {str(e)}")


def call_ai_ats_score(resume_json: dict, job_description: str, model: str = "gpt-4o") -> dict:
    """Analyze resume against job description and provide ATS score."""
    system_prompt = (
        "You are an ATS (Applicant Tracking System) analyzer.\n"
        "Analyze the resume against the job description and provide:\n\n"
        "Return ONLY valid JSON with:\n"
        "{\n"
        '  "ats_score": 0-100,\n'
        '  "keyword_match": 0-100,\n'
        '  "experience_match": 0-100,\n'
        '  "skills_match": 0-100,\n'
        '  "strengths": ["strength1", "strength2", "strength3"],\n'
        '  "weaknesses": ["weakness1", "weakness2", "weakness3"],\n'
        '  "missing_keywords": ["keyword1", "keyword2"],\n'
        '  "suggestions": ["suggestion1", "suggestion2", "suggestion3"]\n'
        "}\n\n"
        "Be honest but constructive. Focus on actionable improvements."
    )

    user_prompt = json.dumps({
        "resume_json": resume_json,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        
        text = resp.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        m = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        return json.loads(text)
    except Exception as e:
        raise Exception(f"ATS analysis failed: {str(e)}")


def call_ai_improve_bullets(experience_bullets: list, job_description: str, model: str = "gpt-4o") -> list:
    """Improve bullet points with STAR method and metrics."""
    system_prompt = (
        "You are an expert resume writer specializing in impactful bullet points.\n"
        "Rewrite the provided bullet points to be more powerful using:\n"
        "- STAR method (Situation, Task, Action, Result)\n"
        "- Quantifiable metrics where possible\n"
        "- Action verbs\n"
        "- Relevant keywords from the job description\n\n"
        "Return ONLY a JSON array of improved bullets:\n"
        '["bullet1", "bullet2", "bullet3"]\n\n'
        "Keep each bullet concise (1-2 lines). No markdown, no explanations."
    )

    user_prompt = json.dumps({
        "bullets": experience_bullets,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        text = resp.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        m = re.search(r'\[.*\]', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        return json.loads(text)
    except Exception as e:
        raise Exception(f"Bullet improvement failed: {str(e)}")


def call_ai_extract_keywords(job_description: str, model: str = "gpt-4o") -> dict:
    """Extract important keywords from job description."""
    system_prompt = (
        "Extract key information from the job description.\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        '  "role_title": "string",\n'
        '  "required_skills": ["skill1", "skill2", ...],\n'
        '  "preferred_skills": ["skill1", "skill2", ...],\n'
        '  "key_technologies": ["tech1", "tech2", ...],\n'
        '  "key_responsibilities": ["resp1", "resp2", ...],\n'
        '  "experience_level": "Junior/Mid/Senior",\n'
        '  "industry_keywords": ["keyword1", "keyword2", ...]\n'
        "}\n\n"
        "Focus on ATS-relevant keywords."
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": job_description}
            ],
            temperature=0.3
        )
        
        text = resp.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        m = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        return json.loads(text)
    except Exception as e:
        raise Exception(f"Keyword extraction failed: {str(e)}")


def call_ai_rewrite_objective(current_objective: str, job_description: str, model: str = "gpt-4o") -> str:
    """Rewrite career objective for specific role."""
    system_prompt = (
        "Rewrite the career objective to be highly targeted to the job description.\n"
        "Requirements:\n"
        "- 2-3 sentences maximum\n"
        "- Use keywords from job description\n"
        "- Show clear value proposition\n"
        "- Sound confident but not arrogant\n"
        "- Focus on what you bring, not what you want\n\n"
        "Return ONLY the rewritten objective text (no JSON, no quotes, no explanations)."
    )

    user_prompt = f"Current objective: {current_objective}\n\nJob description: {job_description}"

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        return resp.choices[0].message.content.strip()
    except Exception as e:
        raise Exception(f"Objective rewrite failed: {str(e)}")


def call_ai_compress_resume(resume_json: dict, model: str = "gpt-4o") -> dict:
    """Intelligently compress resume to fit one page while maintaining impact."""
    system_prompt = (
        "You are an expert at condensing resumes to fit one page while maintaining maximum impact.\n\n"
        "Your task:\n"
        "1. Reduce bullet points to 3-4 per job (keep most impactful ones)\n"
        "2. Make bullet points more concise (1 line each when possible)\n"
        "3. Reduce career objective to 2 sentences\n"
        "4. Keep all jobs but condense descriptions\n"
        "5. Maintain all education entries\n"
        "6. Keep key skills and certifications\n"
        "7. Remove any fluff or redundancy\n"
        "8. Preserve all quantifiable metrics and achievements\n\n"
        "IMPORTANT: Keep the JSON structure identical. Only reduce content length.\n"
        "Return ONLY valid JSON (no markdown, no explanations)."
    )

    user_prompt = json.dumps({"resume_json": resume_json}, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )
        
        text = resp.choices[0].message.content.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        m = re.search(r'\{.*\}', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        return json.loads(text)
    except Exception as e:
        raise Exception(f"Resume compression failed: {str(e)}")
