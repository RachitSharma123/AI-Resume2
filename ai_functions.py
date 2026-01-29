# ai_functions.py
import ast
import json
import os
import re
from functools import lru_cache
from typing import Optional

from openai import OpenAI
import streamlit as st
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def _parse_ai_json(text: str) -> dict:
    """Parse AI response with robust JSON extraction."""
    cleaned = text.strip()
    
    # Remove markdown code blocks
    cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\s*```$', '', cleaned, flags=re.MULTILINE)
    
    # Try to find the JSON object with balanced braces
    # This is more robust for large JSON responses
    try:
        # Find the first opening brace
        start_idx = cleaned.find('{')
        if start_idx == -1:
            raise ValueError("No JSON object found in response")
        
        # Count braces to find matching closing brace
        brace_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(cleaned)):
            if cleaned[i] == '{':
                brace_count += 1
            elif cleaned[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break
        
        if end_idx == -1:
            raise ValueError("Unbalanced JSON braces")
        
        json_str = cleaned[start_idx:end_idx]
        
    except Exception:
        # Fallback to regex method
        m = re.search(r'\{.*\}', cleaned, flags=re.DOTALL)
        if m:
            json_str = m.group(0)
        else:
            raise ValueError("Could not extract JSON from response")
    
    # Clean up smart quotes
    json_str = json_str.replace(""", "\"").replace(""", "\"").replace("'", "'")
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Try Python literal_eval as fallback
        pythonish = re.sub(r"\btrue\b", "True", json_str, flags=re.IGNORECASE)
        pythonish = re.sub(r"\bfalse\b", "False", pythonish, flags=re.IGNORECASE)
        pythonish = re.sub(r"\bnull\b", "None", pythonish, flags=re.IGNORECASE)
        data = ast.literal_eval(pythonish)
        if not isinstance(data, dict):
            raise ValueError("Parsed AI response is not a JSON object.")
        return data

@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    """Create an OpenAI client without hard-failing if secrets are missing."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("OPENAI_API_KEY")
        except Exception:
            api_key = None
    return OpenAI(api_key=api_key or "")

def call_ai_tailor_resume(base_resume_json: dict, job_description: str, model: str = "gpt-4o-mini") -> dict:
    """Tailor resume to match job description with ATS optimization."""
    system_prompt = (
          "You are an elite ATS-optimization and hiring strategist.\n"
        "Your ONLY goal is to modify my resume JSON so that it maximizes shortlisting and interview chances for the given Job Description.\n\n"
        "STRICT RULES (DO NOT BREAK):\n"
        "1. My NAME must NEVER change.\n"
        "2. My EDUCATION must NEVER be removed.\n"
        " - You MAY add relevant education, certifications, coursework, or micro-credentials.\n"
        "3. Output MUST be valid JSON only. No explanations, no markdown, no extra text before or after.\n"
        "4. You ARE ALLOWED to:\n"
        " - Rewrite my career_objective aggressively for alignment\n"
        " - Modify job titles to be closer to the target role\n"
        " - Rewrite experience bullet points using STAR + impact + metrics\n"
        " - Add or tweak or change SKILLS and CERTIFICATIONS (basic to intermediate only)\n"
        "5. You MUST:\n"
        " - Optimize for ATS keywords\n"
        " - Mirror language from the Job Description\n"
        " - Prioritize business impact, tools, and outcomes as metrics\n"
        "6. Do NOT invent fake companies or degrees.\n"
        "7. Do NOT downgrade my experience.\n"
        " Modify it to be closer to the target role or a level up\n\n"
        "OUTPUT REQUIREMENTS:\n"
        "- Return ONLY the JSON object, nothing else\n"
        "- Keep structure identical to my original resume JSON\n"
        "- Make it sound like a strong mid–senior candidate, not a fresher\n"
        "- NO explanations, NO markdown code blocks, NO text before or after JSON\n"
    )

    user_prompt = json.dumps({
        "resume_json": base_resume_json,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        text = resp.choices[0].message.content.strip()
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"AI Tailor failed: {str(e)}")


def call_ai_generate_cover_letter(resume_json: dict, job_description: str, model: str = "gpt-4o-mini") -> dict:
    """Generate cover letter JSON from resume and job description."""
    system_prompt = (
        "You write concise, high-converting cover letters for professional roles.\n"
        "Return ONLY valid JSON (no markdown, no backticks, no extra text).\n\n"
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
        "Use resume + job description for alignment. Mirror JD language but sound like a human.\n"
        "Keep it professional, 350 words, and focused on value proposition + willingness to grow as an employee."
        "Return ONLY the JSON object. NO markdown, NO explanations.\n"
        
    )

    user_prompt = json.dumps({
        "resume_json": resume_json,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        text = resp.choices[0].message.content.strip()
        out = _parse_ai_json(text)
        return out.get("cover_letter", out)
    except Exception as e:
        raise Exception(f"Cover letter generation failed: {str(e)}")


def call_ai_ats_score(resume_json: dict, job_description: str, model: str = "gpt-4o-mini") -> dict:
    """Analyze resume against job description and provide ATS score."""
    system_prompt = (
        "You are an ATS (Applicant Tracking System) analyzer.\n"
        "Analyze the resume against the job description and provide:\n\n"
        "Return ONLY valid JSON with this exact structure:\n"
        "{\n"
        '  "ats_score": 75,\n'
        '  "keyword_match": 80,\n'
        '  "experience_match": 70,\n'
        '  "skills_match": 85,\n'
        '  "strengths": ["strength1", "strength2", "strength3"],\n'
        '  "weaknesses": ["weakness1", "weakness2", "weakness3"],\n'
        '  "missing_keywords": ["keyword1", "keyword2"],\n'
        '  "suggestions": ["suggestion1", "suggestion2", "suggestion3"]\n'
        "}\n\n"
        "IMPORTANT: Numbers must be integers without quotes. Arrays must have at least one item.\n"
        "Be honest but constructive. Focus on actionable improvements.\n"
        "Return ONLY the JSON object, no markdown, no explanations, no code blocks, no extra text."
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
        result = _parse_ai_json(text)
        
        # Validate structure
        required_keys = ["ats_score", "keyword_match", "experience_match", "skills_match", 
                        "strengths", "weaknesses", "missing_keywords", "suggestions"]
        for key in required_keys:
            if key not in result:
                result[key] = 0 if "score" in key or "match" in key else []
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON Parse Error: {e}")
        print(f"Response text: {text}")
        # Return default structure on error
        return {
            "ats_score": 0,
            "keyword_match": 0,
            "experience_match": 0,
            "skills_match": 0,
            "strengths": ["Unable to analyze - JSON parse error"],
            "weaknesses": ["Please try again"],
            "missing_keywords": [],
            "suggestions": ["Retry the analysis"]
        }
    except Exception as e:
        raise Exception(f"ATS analysis failed: {str(e)}")


def call_ai_improve_bullets(experience_bullets: list, job_description: str, model: str = "gpt-4o-mini") -> list:
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
        "Keep each bullet concise (1-2 lines). No markdown, no explanations, no extra text."
    )

    user_prompt = json.dumps({
        "bullets": experience_bullets,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        
        text = resp.choices[0].message.content.strip()
        
        # Remove markdown
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        # Extract array
        m = re.search(r'\[.*\]', text, flags=re.DOTALL)
        if m:
            text = m.group(0)
        
        return json.loads(text)
    except Exception as e:
        raise Exception(f"Bullet improvement failed: {str(e)}")


def call_ai_extract_keywords(job_description: str, model: str = "gpt-4o-mini") -> dict:
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
        "Focus on ATS-relevant keywords. NO markdown, NO extra text."
    )

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": job_description}
            ],
            temperature=0.3
        )
        
        text = resp.choices[0].message.content
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"Keyword extraction failed: {str(e)}")


def call_ai_rewrite_objective(current_objective: str, job_description: str, model: str = "gpt-4o-mini") -> str:
    """Rewrite career objective for specific role."""
    system_prompt = (
        "Rewrite the career objective to be highly targeted to the job description.\n"
        "Requirements:\n"
        "- 3-6 sentences maximum\n"
        "- Use keywords from job description\n"
        "- Show clear value proposition\n"
        "- Sound confident but not arrogant\n"
        "- Focus on what you bring, not what you want\n\n"
        "Return ONLY the rewritten objective text (no JSON, no quotes, no explanations)."
    )

    user_prompt = f"Current objective: {current_objective}\n\nJob description: {job_description}"

    try:
        client = get_openai_client()
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


def call_ai_compress_resume(resume_json: dict, model: str = "gpt-4o-mini") -> dict:
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
        "Return ONLY valid JSON (no markdown, no explanations, no extra text)."
    )

    user_prompt = json.dumps({"resume_json": resume_json}, ensure_ascii=False)

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5
        )
        
        text = resp.choices[0].message.content
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"Resume compression failed: {str(e)}")


def call_ai_improve_from_ats(resume_json: dict, ats_results: dict, job_description: str, model: str = "gpt-4o-mini") -> dict:
    """Improve resume based on ATS analysis results."""
    system_prompt = (
        "You are a resume optimization expert. Based on the ATS analysis, improve the resume.\n\n"
        "You will receive:\n"
        "1. Current resume JSON\n"
        "2. ATS analysis with scores, strengths, weaknesses, missing keywords\n"
        "3. Job description\n\n"
        "Your task:\n"
        "- Address ALL weaknesses mentioned in ATS analysis\n"
        "- Add ALL missing keywords naturally into relevant sections\n"
        "- Improve sections with low scores\n"
        "- Maintain truthfulness - enhance, don't fabricate\n"
        "- Keep JSON structure identical\n"
        "- Focus on maximizing ATS score while keeping content authentic\n\n"
        "Return ONLY the improved resume JSON (no markdown, no explanations, no extra text)."
    )

    user_prompt = json.dumps({
        "resume_json": resume_json,
        "ats_analysis": ats_results,
        "job_description": job_description
    }, ensure_ascii=False)

    try:
        client = get_openai_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6
        )
        
        text = resp.choices[0].message.content
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"ATS-based improvement failed: {str(e)}")
