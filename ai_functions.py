# ai_functions.py
import ast
import json
import os
import re

from openai import OpenAI
import requests


PROVIDER_DEFAULTS = {
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "key_names": ["DEEPSEEK_API_KEY", "AI_API_KEY"],
        "default_model": "deepseek-chat",
    },
    "openai": {
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "key_names": ["OPENAI_API_KEY", "AI_API_KEY"],
        "default_model": "gpt-4o-mini",
    },
    "openrouter": {
        "label": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "key_names": ["OPENROUTER_API_KEY", "AI_API_KEY"],
        "default_model": "google/gemini-2.0-flash-exp:free",
    },
    "grok": {
        "label": "Grok / xAI",
        "base_url": "https://api.x.ai/v1",
        "key_names": ["GROK_API_KEY", "XAI_API_KEY", "AI_API_KEY"],
        "default_model": "grok-2-latest",
    },
    "kimi": {
        "label": "Kimi / Moonshot",
        "base_url": "https://api.moonshot.ai/v1",
        "key_names": ["KIMI_API_KEY", "MOONSHOT_API_KEY", "AI_API_KEY"],
        "default_model": "moonshot-v1-8k",
    },
    "zai": {
        "label": "ZAI",
        "base_url": "https://api.z.ai/api/paas/v4",
        "key_names": ["ZAI_API_KEY", "AI_API_KEY"],
        "default_model": "glm-4-plus",
    },
    "blackbox": {
        "label": "Blackbox",
        "base_url": "https://api.blackbox.ai/v1",
        "key_names": ["BLACKBOX_API_KEY", "AI_API_KEY"],
        "default_model": "blackboxai/openai/gpt-4o-mini",
    },
    "custom": {
        "label": "Custom OpenAI-Compatible",
        "base_url": "https://api.openai.com/v1",
        "key_names": ["AI_API_KEY"],
        "default_model": "gpt-4o-mini",
    },
}


def _parse_ai_json(text: str) -> dict:
    """Parse AI response with robust JSON extraction."""
    cleaned = text.strip()

    # Remove markdown code blocks
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)

    # Try to find the JSON object with balanced braces
    # This is more robust for large JSON responses
    try:
        # Find the first opening brace
        start_idx = cleaned.find("{")
        if start_idx == -1:
            raise ValueError("No JSON object found in response")

        # Count braces to find matching closing brace
        brace_count = 0
        end_idx = -1

        for i in range(start_idx, len(cleaned)):
            if cleaned[i] == "{":
                brace_count += 1
            elif cleaned[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

        if end_idx == -1:
            raise ValueError("Unbalanced JSON braces")

        json_str = cleaned[start_idx:end_idx]

    except Exception:
        # Fallback to regex method
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if m:
            json_str = m.group(0)
        else:
            raise ValueError("Could not extract JSON from response")

    # Clean up smart quotes
    json_str = json_str.replace(""", "\"").replace(""", '"').replace("'", "'")

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try Python literal_eval as fallback
        pythonish = re.sub(r"\btrue\b", "True", json_str, flags=re.IGNORECASE)
        pythonish = re.sub(r"\bfalse\b", "False", pythonish, flags=re.IGNORECASE)
        pythonish = re.sub(r"\bnull\b", "None", pythonish, flags=re.IGNORECASE)
        data = ast.literal_eval(pythonish)
        if not isinstance(data, dict):
            raise ValueError("Parsed AI response is not a JSON object.")
        return data


def _get_secret_or_env(*keys: str) -> str | None:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return None


def _normalize_provider(provider: str | None) -> str:
    p = (provider or "openai").strip().lower()
    aliases = {
        "xai": "grok",
        "moonshot": "kimi",
    }
    return aliases.get(p, p)


def get_provider_choices() -> dict[str, str]:
    return {provider: config["label"] for provider, config in PROVIDER_DEFAULTS.items()}


def _get_runtime_provider_config() -> dict:
    return {}


def _resolve_provider_config(runtime_overrides: dict | None = None) -> dict:
    runtime_cfg = _get_runtime_provider_config()
    if runtime_overrides:
        runtime_cfg = {**runtime_cfg, **runtime_overrides}

    provider = _normalize_provider(
        runtime_cfg.get("provider") or _get_secret_or_env("AI_PROVIDER") or "deepseek"
    )

    defaults = PROVIDER_DEFAULTS.get(
        provider,
        {
            "label": "Custom OpenAI-Compatible",
            "base_url": _get_secret_or_env("AI_BASE_URL")
            or "https://api.openai.com/v1",
            "key_names": ["AI_API_KEY"],
            "default_model": "gpt-4o-mini",
        },
    )

    api_key = (runtime_cfg.get("api_key") or "").strip() or _get_secret_or_env(
        *defaults["key_names"]
    )
    if not api_key:
        raise ValueError(
            f"No API key configured for provider '{provider}'. "
            f"Set one of: {', '.join(defaults['key_names'])} or enter it in AI Provider Settings."
        )

    base_url = (
        (runtime_cfg.get("base_url") or "").strip()
        or _get_secret_or_env("AI_BASE_URL")
        or defaults["base_url"]
    )
    default_model = (
        (runtime_cfg.get("model") or "").strip()
        or _get_secret_or_env("AI_MODEL")
        or defaults["default_model"]
    )

    return {
        "provider": provider,
        "label": defaults.get("label", provider.title()),
        "api_key": api_key,
        "base_url": base_url.rstrip("/"),
        "default_model": default_model,
        "key_names": defaults["key_names"],
    }


def get_ai_client(runtime_overrides: dict | None = None) -> OpenAI:
    cfg = _resolve_provider_config(runtime_overrides)
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def _chat_completion(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.7,
) -> str:
    cfg = _resolve_provider_config()
    chosen_model = model or cfg["default_model"]
    client = get_ai_client()

    resp = client.chat.completions.create(
        model=chosen_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )

    return (resp.choices[0].message.content or "").strip()


def list_models(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> list[str]:
    """Fetch available model IDs from an OpenAI-compatible provider."""
    overrides = {
        "provider": provider,
        "api_key": api_key,
        "base_url": base_url,
    }
    overrides = {key: value for key, value in overrides.items() if value}
    cfg = _resolve_provider_config(overrides)

    try:
        client = get_ai_client(overrides)
        response = client.models.list()
        models = [
            getattr(item, "id", None)
            for item in getattr(response, "data", [])
            if getattr(item, "id", None)
        ]
    except Exception:
        url = f"{cfg['base_url']}/models"
        headers = {"Authorization": f"Bearer {cfg['api_key']}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data", payload if isinstance(payload, list) else [])
        models = []
        for item in data:
            if isinstance(item, dict) and item.get("id"):
                models.append(item["id"])

    normalized = sorted(
        {model for model in models if isinstance(model, str) and model.strip()}
    )
    if not normalized:
        raise ValueError(f"No models returned by provider '{cfg['provider']}'.")
    return normalized


def call_ai_tailor_resume(
    base_resume_json: dict, job_description: str, model: str | None = None
) -> dict:
    """Tailor resume to match job description with ATS optimization."""
    system_prompt = (
        "You are an elite ATS-optimization and hiring strategist.\n"
        "Your ONLY goal is to modify my resume JSON so that it maximizes shortlisting and interview chances for the given Job Description.\n\n"
        "STRICT RULES (DO NOT BREAK):\n"
        "1. My NAME must NEVER change.\n"
        "2. My EDUCATION must NEVER be removed or changed.\n"
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

    user_prompt = json.dumps(
        {
            "resume_json": base_resume_json,
            "job_description": job_description,
        },
        ensure_ascii=False,
    )

    try:
        text = _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.7
        )
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"AI Tailor failed: {str(e)}")


def call_ai_generate_cover_letter(
    resume_json: dict, job_description: str, model: str | None = None
) -> dict:
    """Generate a cover_letter object from resume and job description."""
    system_prompt = (
        "You are a professional career coach helping someone write an authentic, human cover letter.\n\n"
        "CRITICAL: Return ONLY a JSON object for the `cover_letter` section.\n"
        "Do NOT return full resume JSON. Do NOT wrap in `resume_json`.\n\n"
        "Cover letter requirements:\n"
        "- Write like a real person having a professional conversation\n"
        "- Be warm, genuine, and conversational - imagine writing to someone you respect\n"
        "- Show authentic enthusiasm about the role and company (research-based if possible)\n"
        "- NO corporate jargon: avoid 'leverage', 'synergy', 'dynamic', 'passionate', 'game-changer'\n"
        "- Use natural language: 'I've worked on...' instead of 'I have leveraged...'\n"
        "- Total body length: 500-600 words (the body_points combined, excluding header/footer)\n"
        "- 4-5 paragraphs in body_points, each 4-6 sentences (100-130 words each)\n"
        "- Tell a story: connect your experience to their needs naturally\n\n"
        "Paragraph structure:\n"
        "1. Opening hook: Why this specific role excited you + brief introduction (4-5 sentences)\n"
        "2. Relevant experience: What you've done that relates to this role (5-6 sentences with concrete examples)\n"
        "3. Key achievements: Specific wins that demonstrate your capability (4-5 sentences with metrics if possible)\n"
        "4. Company fit: Why you're interested in THIS company specifically (4-5 sentences, research-based)\n"
        "5. Closing: Next steps, availability, thank you (3-4 sentences)\n\n"
        "Writing style examples:\n"
        "❌ BAD: 'I am writing to express my interest in leveraging my dynamic skillset...'\n"
        "✅ GOOD: 'When I saw your Data Analyst opening, it immediately caught my attention because...'\n\n"
        "❌ BAD: 'My proven track record of synergizing cross-functional deliverables...'\n"
        "✅ GOOD: 'In my current role, I work with teams across IT, operations, and management to turn data into decisions.'\n\n"
        "❌ BAD: 'I am passionate about utilizing cutting-edge technologies to drive results'\n"
        "✅ GOOD: 'I've spent the past two years learning how Python and SQL can solve real business problems, not just create reports'\n\n"
        "Structure to return:\n"
        "{\n"
        '  "date": "AUTO",\n'
        '  "recipient": "Hiring Manager",\n'
        '  "company": "[extract from JD or leave blank]",\n'
        '  "role_title": "[extract from JD]",\n'
        '  "company_address": "",\n'
        '  "subject": "Re: Application for [Role Title]",\n'
        '  "opening": "Dear Hiring Manager,",\n'
        '  "body_points": [\n'
        '    "Opening paragraph: 100-130 words",\n'
        '    "Experience paragraph: 100-130 words",\n'
        '    "Achievement paragraph: 100-130 words",\n'
        '    "Company fit paragraph: 100-130 words",\n'
        '    "Closing paragraph: 80-100 words"\n'
        "  ],\n"
        '  "closing": "Best regards,",\n'
        '  "signature_name": "[from resume name]",\n'
        '  "phone_number": "[from resume contact]",\n'
        '  "email": "[from resume contact]"\n'
        "}\n\n"
        "IMPORTANT: Each paragraph in body_points should read naturally, like sentences in an email.\n"
        "Aim for 500-600 total words in the body_points combined.\n"
        "Return ONLY the cover_letter JSON object. NO markdown, NO explanations, NO extra text.\n"
    )

    user_prompt = json.dumps(
        {
            "resume_json": resume_json,
            "job_description": job_description,
        },
        ensure_ascii=False,
    )

    try:
        text = _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.8
        )
        result = _parse_ai_json(text)

        # Normalize possible response shapes into a plain cover_letter object.
        if isinstance(result.get("cover_letter"), dict):
            return result["cover_letter"]

        if isinstance(result.get("resume_json"), dict):
            nested = result["resume_json"].get("cover_letter")
            if isinstance(nested, dict):
                return nested

        cover_letter_keys = {
            "date",
            "recipient",
            "company",
            "role_title",
            "subject",
            "opening",
            "body_points",
            "closing",
        }
        if cover_letter_keys.intersection(result.keys()):
            return result

        raise ValueError("AI response did not contain a valid cover_letter object")
    except Exception as e:
        raise Exception(f"Cover letter generation failed: {str(e)}")


def call_ai_ats_score(
    resume_json: dict, job_description: str, model: str | None = None
) -> dict:
    """Analyze resume against job description and provide ATS score."""
    system_prompt = (
        "You are an ATS (Applicant Tracking System) analyzer with deep reasoning capabilities.\n"
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

    user_prompt = json.dumps(
        {
            "resume_json": resume_json,
            "job_description": job_description,
        },
        ensure_ascii=False,
    )

    try:
        text = _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.3
        )
        result = _parse_ai_json(text)

        # Validate structure
        required_keys = [
            "ats_score",
            "keyword_match",
            "experience_match",
            "skills_match",
            "strengths",
            "weaknesses",
            "missing_keywords",
            "suggestions",
        ]
        for key in required_keys:
            if key not in result:
                result[key] = 0 if "score" in key or "match" in key else []

        return result

    except json.JSONDecodeError:
        return {
            "ats_score": 0,
            "keyword_match": 0,
            "experience_match": 0,
            "skills_match": 0,
            "strengths": ["Unable to analyze - JSON parse error"],
            "weaknesses": ["Please try again"],
            "missing_keywords": [],
            "suggestions": ["Retry the analysis"],
        }
    except Exception as e:
        raise Exception(f"ATS analysis failed: {str(e)}")


def call_ai_improve_bullets(
    experience_bullets: list, job_description: str, model: str | None = None
) -> list:
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

    user_prompt = json.dumps(
        {
            "bullets": experience_bullets,
            "job_description": job_description,
        },
        ensure_ascii=False,
    )

    try:
        text = _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.7
        )

        # Remove markdown
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        # Extract array
        m = re.search(r"\[.*\]", text, flags=re.DOTALL)
        if m:
            text = m.group(0)

        return json.loads(text)
    except Exception as e:
        raise Exception(f"Bullet improvement failed: {str(e)}")


def call_ai_extract_keywords(job_description: str, model: str | None = None) -> dict:
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
        text = _chat_completion(
            system_prompt, job_description, model=model, temperature=0.3
        )
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"Keyword extraction failed: {str(e)}")


def call_ai_rewrite_objective(
    current_objective: str, job_description: str, model: str | None = None
) -> str:
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

    user_prompt = (
        f"Current objective: {current_objective}\n\nJob description: {job_description}"
    )

    try:
        return _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.7
        )
    except Exception as e:
        raise Exception(f"Objective rewrite failed: {str(e)}")


def call_ai_compress_resume(resume_json: dict, model: str | None = None) -> dict:
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
        text = _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.5
        )
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"Resume compression failed: {str(e)}")


def call_ai_extract_resume_from_text(raw_text: str, model: str | None = None) -> dict:
    """Parse unstructured resume text (from PDF) into the standard resume JSON schema."""
    system_prompt = (
        "You are an expert resume parser. Extract information from the raw resume text and return a JSON object "
        "that EXACTLY matches this schema (use empty strings or empty arrays for missing fields — never omit keys):\n\n"
        "{\n"
        '  "name": "string",\n'
        '  "contact": "string (location | phone | email on one line)",\n'
        '  "career_objective": "string",\n'
        '  "skills_snapshot": [{"label": "string", "value": "string"}],\n'
        '  "experience": [\n'
        '    {"company": "string", "role_line": "Job Title | Start – End", "bullets": ["string"]}\n'
        "  ],\n"
        '  "education": [{"degree": "string", "details": "string"}],\n'
        '  "certifications": ["string"],\n'
        '  "additional_information": {},\n'
        '  "references": []\n'
        "}\n\n"
        "IMPORTANT:\n"
        "- Handle garbled text, merged lines, and bullet character artifacts from PDF extraction\n"
        "- For skills_snapshot: group skills into logical categories (Technical Skills, Soft Skills, Tools, etc.)\n"
        "- For experience bullets: each bullet should be a separate string in the array\n"
        "- Return ONLY the JSON object — no markdown, no explanations, no extra text\n"
    )

    try:
        text = _chat_completion(system_prompt, raw_text, model=model, temperature=0.3)
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"Resume extraction failed: {str(e)}")


def call_ai_improve_from_ats(
    resume_json: dict,
    ats_results: dict,
    job_description: str,
    model: str | None = None,
) -> dict:
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

    user_prompt = json.dumps(
        {
            "resume_json": resume_json,
            "ats_analysis": ats_results,
            "job_description": job_description,
        },
        ensure_ascii=False,
    )

    try:
        text = _chat_completion(
            system_prompt, user_prompt, model=model, temperature=0.6
        )
        return _parse_ai_json(text)
    except Exception as e:
        raise Exception(f"ATS-based improvement failed: {str(e)}")
