"""
resume_engine.py — Standalone resume/cover-letter pipeline using GPT-4o via OpenRouter + ReportLab.
Drop-in replacement for ai_functions.py (no streamlit dependency).
"""
import json, re, sys, tempfile, unicodedata
from pathlib import Path
from openai import OpenAI

# ── DeepSeek V3 (fast, structured JSON, cost-effective) ─────────────────────
def _get_key():
    import json as _json
    cfg = _json.loads(Path("/home/rachit/.openclaw/openclaw.json").read_text())
    providers = cfg.get("models", {}).get("providers", {})
    key = providers.get("custom-api-deepseek-com", {}).get("apiKey", "")
    if key:
        return key
    # fallback to .env
    env = Path("/home/rachit/.openclaw/.env")
    for line in env.read_text().splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""

_client = OpenAI(
    api_key=_get_key(),
    base_url="https://api.deepseek.com"
)
MODEL = "deepseek-chat"


def _ai(system: str, user: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
    try:
        resp = _client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  [resume_engine] AI call failed: {e}")
        return ""


def _parse_json(text: str) -> dict | list:
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text)
    m = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


# Characters ReportLab/Helvetica can't render → safe ASCII replacements
_UNICODE_MAP = str.maketrans({
    # dashes
    '\u2014': '-',   # em dash
    '\u2013': '-',   # en dash
    '\u2011': '-',   # non-breaking hyphen  ← the ? culprit
    '\u2010': '-',   # hyphen
    '\u2012': '-',   # figure dash
    '\u2015': '-',   # horizontal bar
    '\u2212': '-',   # minus sign
    # quotes
    '\u2018': "'",   # left single quote
    '\u2019': "'",   # right single quote
    '\u201a': "'",   # single low quote
    '\u201b': "'",   # single high reversed quote
    '\u201c': '"',   # left double quote
    '\u201d': '"',   # right double quote
    '\u201e': '"',   # double low quote
    '\u00ab': '"',   # left angle quote
    '\u00bb': '"',   # right angle quote
    # bullets / symbols
    '\u2022': '-',   # bullet
    '\u2023': '-',   # triangle bullet
    '\u25aa': '-',   # small square
    '\u25cf': '-',   # black circle
    '\u2024': '.',   # one dot leader
    '\u2026': '...',  # ellipsis
    '\u2192': '->',  # right arrow
    '\u2190': '<-',  # left arrow
    '\u2713': 'v',   # check mark
    '\u2714': 'v',   # heavy check mark
    '\u2718': 'x',   # heavy ballot x
    # spaces
    '\u00a0': ' ',   # non-breaking space
    '\u202f': ' ',   # narrow no-break space
    '\u2009': ' ',   # thin space
    '\u200b': '',    # zero-width space
    '\u200c': '',    # zero-width non-joiner
    '\u200d': '',    # zero-width joiner
    '\ufeff': '',    # BOM
    # misc
    '\u00b7': '-',   # middle dot
    '\u2217': '*',   # asterisk operator
    '\u00ae': '(R)', # registered
    '\u00a9': '(C)', # copyright
    '\u2122': '(TM)',# trademark
})

def _sanitise(val: str) -> str:
    # 1. Apply explicit map
    val = val.translate(_UNICODE_MAP)
    # 2. NFKD decompose — converts accented chars to base + combining (e.g. é → e + ́)
    val = unicodedata.normalize('NFKD', val)
    # 3. Drop anything still outside ASCII printable range
    val = val.encode('ascii', errors='ignore').decode('ascii')
    return val

def _sanitise_json(obj):
    """Recursively sanitise all strings in a JSON-like structure."""
    if isinstance(obj, dict):
        return {k: _sanitise_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitise_json(i) for i in obj]
    if isinstance(obj, str):
        return _sanitise(obj)
    return obj


# ── Base resume JSON (loaded once from repo) ─────────────────────────────────
BASE_RESUME = json.loads((Path(__file__).parent / "resume_data.json").read_text(encoding="utf-8"))


# ── AI functions ─────────────────────────────────────────────────────────────

def tailor_resume(base_resume_json: dict, job_description: str) -> dict:
    system = (
        "You are a senior recruiter who reviews 200 resumes a day. You know instantly what gets shortlisted and what gets binned.\n"
        "Rewrite this resume JSON specifically for the given role and company.\n\n"
        "MANDATORY RULES:\n"
        "1. Name must NEVER change. Education must NEVER be removed.\n"
        "2. Output MUST be valid JSON only — no explanations, no markdown fences.\n"
        "3. REPLACE every responsibility bullet with a measurable achievement. Use numbers, percentages, timeframes, scale.\n"
        "   BAD: 'Managed stakeholder relationships'\n"
        "   GOOD: 'Aligned 12 cross-functional stakeholders across 3 departments, reducing requirement sign-off time by 40%'\n"
        "4. ELIMINATE every generic phrase: 'responsible for', 'assisted with', 'helped to', 'worked on', 'involved in'.\n"
        "5. Mirror the EXACT language and keywords from the job description — ATS must score this as a near-perfect match.\n"
        "6. Rewrite career_objective as a 2-sentence punchy value proposition targeted at this specific role and company.\n"
        "7. Adjust job titles to be closer to the target role where truthful.\n"
        "8. Make the candidate sound like a strong mid-senior professional whose value is impossible to ignore.\n"
        "9. DO NOT invent fake companies, degrees, or certifications.\n"
        "10. Keep JSON structure IDENTICAL to input. Return ONLY valid JSON."
    )
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"RESUME JSON TO REWRITE:\n{json.dumps(base_resume_json, ensure_ascii=False)}"
    )
    raw = _ai(system, user, max_tokens=3500)
    try:
        result = _parse_json(raw)
        # Unwrap if model wrapped in extra key
        if isinstance(result, dict) and "name" not in result:
            for v in result.values():
                if isinstance(v, dict) and "name" in v:
                    result = v
                    break
        return result
    except Exception as e:
        print(f"  [resume_engine] tailor_resume parse error: {e} — returning base")
        return base_resume_json


def compress_resume(resume_json: dict) -> dict:
    system = (
        "Compress this resume to fit one page while keeping maximum impact.\n"
        "1. Reduce bullets to 3-4 per job (keep most impactful).\n"
        "2. Make bullets concise (1 line each).\n"
        "3. Reduce career_objective to 2 sentences.\n"
        "4. Keep ALL jobs, education, key skills, certs.\n"
        "5. Remove fluff. Preserve metrics.\n"
        "Keep JSON structure IDENTICAL. Return ONLY valid JSON."
    )
    user = f"RESUME JSON TO COMPRESS:\n{json.dumps(resume_json, ensure_ascii=False)}"
    raw = _ai(system, user, max_tokens=2000, temperature=0.5)
    try:
        result = _parse_json(raw)
        if isinstance(result, dict) and "name" not in result:
            for v in result.values():
                if isinstance(v, dict) and "name" in v:
                    result = v
                    break
        return result
    except Exception as e:
        print(f"  [resume_engine] compress_resume parse error: {e} — returning input")
        return resume_json


def generate_cover_letter_json(resume_json: dict, job_description: str) -> dict:
    system = (
        "You write high-converting cover letters that get callbacks.\n"
        "Return ONLY valid JSON (no markdown, no backticks).\n\n"
        "RULES:\n"
        "1. NEVER start with 'I am applying for' or 'I am writing to apply'. Open with a powerful, specific insight or statement that immediately shows you understand the company's core challenge or mission.\n"
        "2. The letter must connect the candidate's specific experience directly to the company's core need — not generic skills, but real alignment.\n"
        "3. Build trust through specificity: reference the company by name, reference real achievements from the resume, show you've done your homework.\n"
        "4. Total word count MUST be under 250 words. Tight, punchy, no filler.\n"
        "5. Tone: confident, direct, professional — not desperate or sycophantic.\n\n"
        "Return a JSON object with key 'cover_letter' containing:\n"
        "- date: 'AUTO'\n"
        "- recipient: string (e.g. 'Hiring Manager')\n"
        "- company: string\n"
        "- role_title: string\n"
        "- company_address: string\n"
        "- subject: string\n"
        "- opening: string — MUST start with 'Dear [Recipient],'\n"
        "- body_points: list of exactly 3 paragraphs. First: powerful hook + value proposition (NOT 'I am applying'). Second: specific experience aligned to company's core need with a measurable result. Third: why this company specifically + call to action.\n"
        "- closing: 'Kind regards,'\n"
        "- signature_name: string\n"
        "- phone_number: string\n"
        "- email: string\n\n"
        "Return ONLY valid JSON."
    )
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"CANDIDATE RESUME:\n{json.dumps(resume_json, ensure_ascii=False)}"
    )
    raw = _ai(system, user, max_tokens=2000)
    try:
        out = _parse_json(raw)
        return out.get("cover_letter", out)
    except Exception as e:
        print(f"  [resume_engine] cover_letter parse error: {e}")
        return {}


# ── PDF generators ────────────────────────────────────────────────────────────

# Add repo to path so pdf_generator can find drawing_utils
_here = str(Path(__file__).parent)
if _here not in sys.path:
    sys.path.insert(0, _here)

from pdf_generator import create_resume_pdf, create_cover_letter_pdf


def _write_tmp_json(data: dict) -> Path:
    tf = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
    json.dump(data, tf, ensure_ascii=False)
    tf.close()
    return Path(tf.name)


FONT_SCALE = 1 / 1.2  # ≈ 0.833 — guarantees 1-page output


def generate_resume_pdf(base_resume_json: dict, job_description: str, output_path: str) -> bool:
    """Tailor + compress resume for the job, then render a sophisticated 1-page PDF."""
    try:
        print("  [resume_engine] Tailoring resume…")
        tailored = tailor_resume(base_resume_json, job_description)
        print("  [resume_engine] Compressing to 1 page…")
        compressed = compress_resume(tailored)
        clean = _sanitise_json(compressed)
        tmp = _write_tmp_json(clean)
        create_resume_pdf(json_path=str(tmp), output_path=str(output_path), font_scale=FONT_SCALE)
        tmp.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"  [resume_engine] generate_resume_pdf error: {e}")
        return False


def generate_ats_score(resume_json: dict, job_description: str) -> dict:
    """Score the tailored resume against the JD. Returns dict with score breakdown."""
    system = (
        "You are an ATS (Applicant Tracking System) engine AND a senior recruiter reviewing the output.\n"
        "Analyse the resume against the job description and return ONLY valid JSON — no markdown, no explanation.\n\n"
        "Return exactly this structure:\n"
        "{\n"
        "  \"overall_score\": 0-100,\n"
        "  \"keyword_match\": 0-100,\n"
        "  \"experience_match\": 0-100,\n"
        "  \"skills_match\": 0-100,\n"
        "  \"matched_keywords\": [\"kw1\", \"kw2\", \"kw3\"],\n"
        "  \"missing_keywords\": [\"kw1\", \"kw2\"],\n"
        "  \"strengths\": [\"strength1\", \"strength2\", \"strength3\"],\n"
        "  \"gaps\": [\"gap1\", \"gap2\"],\n"
        "  \"verdict\": \"one sentence recruiter verdict on this application\"\n"
        "}\n\n"
        "Be honest. A score of 90+ means shortlist-worthy. Below 60 means likely rejected."
    )
    user = (
        f"JOB DESCRIPTION:\n{job_description}\n\n"
        f"RESUME:\n{json.dumps(resume_json, ensure_ascii=False)}"
    )
    raw = _ai(system, user, max_tokens=1200, temperature=0.3)
    try:
        result = _parse_json(raw)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        print(f"  [resume_engine] ats_score parse error: {e}")
        return {}


def generate_cover_letter_pdf(base_resume_json: dict, job_description: str, output_path: str) -> bool:
    """Generate cover letter JSON + render to 1-page PDF."""
    try:
        print("  [resume_engine] Generating cover letter…")
        cl = generate_cover_letter_json(base_resume_json, job_description)
        data = dict(base_resume_json)
        data["cover_letter"] = cl
        clean = _sanitise_json(data)
        tmp = _write_tmp_json(clean)
        create_cover_letter_pdf(json_path=str(tmp), output_path=str(output_path), font_scale=FONT_SCALE)
        tmp.unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"  [resume_engine] generate_cover_letter_pdf error: {e}")
        return False
