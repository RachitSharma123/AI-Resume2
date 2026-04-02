import sys
import os
import base64
import hashlib
import secrets

# Add repo root to path so we can import existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Any
from mangum import Mangum

from ai_functions import (
    call_ai_tailor_resume,
    call_ai_generate_cover_letter,
    call_ai_ats_score,
    call_ai_improve_bullets,
    call_ai_extract_keywords,
    call_ai_rewrite_objective,
    call_ai_compress_resume,
    call_ai_improve_from_ats,
)
from pdf_generator import create_resume_pdf_bytes, create_cover_letter_pdf_bytes

app = FastAPI(title="AI Resume Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
# Simple token: sha256(APP_PASSWORD + SECRET_SALT)
SECRET_SALT = os.getenv("SECRET_SALT", "ai-resume-salt-2024")


def _make_token(password: str) -> str:
    return hashlib.sha256(f"{password}{SECRET_SALT}".encode()).hexdigest()


def _verify_token(token: str) -> bool:
    if not APP_PASSWORD:
        return True  # No password set — open access
    expected = _make_token(APP_PASSWORD)
    return secrets.compare_digest(token, expected)


def require_auth(x_token: Optional[str] = Header(None)):
    if not _verify_token(x_token or ""):
        raise HTTPException(status_code=401, detail="Unauthorized")


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
def login(body: LoginRequest):
    if not APP_PASSWORD:
        return {"token": "no-auth"}
    if body.password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid password")
    return {"token": _make_token(body.password)}


# ── AI endpoints ──────────────────────────────────────────────────────────────

class TailorRequest(BaseModel):
    resume: dict
    job_description: str
    model: str = "gpt-4o-mini"


@app.post("/api/tailor")
def tailor_resume(body: TailorRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_tailor_resume(body.resume, body.job_description, model=body.model)
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoverLetterRequest(BaseModel):
    resume: dict
    job_description: str
    model: str = "gpt-4o-mini"


@app.post("/api/cover-letter")
def cover_letter(body: CoverLetterRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_generate_cover_letter(body.resume, body.job_description, model=body.model)
        return {"cover_letter": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ATSRequest(BaseModel):
    resume: dict
    job_description: str
    model: str = "gpt-4o-mini"


@app.post("/api/ats-score")
def ats_score(body: ATSRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_ats_score(body.resume, body.job_description, model=body.model)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImproveBulletsRequest(BaseModel):
    bullets: List[str]
    job_description: str
    model: str = "gpt-4o-mini"


@app.post("/api/improve-bullets")
def improve_bullets(body: ImproveBulletsRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_improve_bullets(body.bullets, body.job_description, model=body.model)
        return {"bullets": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CompressRequest(BaseModel):
    resume: dict
    model: str = "gpt-4o-mini"


@app.post("/api/compress")
def compress_resume(body: CompressRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_compress_resume(body.resume, model=body.model)
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImproveFromATSRequest(BaseModel):
    resume: dict
    ats_results: dict
    job_description: str
    model: str = "gpt-4o-mini"


@app.post("/api/improve-from-ats")
def improve_from_ats(body: ImproveFromATSRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_improve_from_ats(body.resume, body.ats_results, body.job_description, model=body.model)
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExtractKeywordsRequest(BaseModel):
    job_description: str
    model: str = "gpt-4o-mini"


@app.post("/api/extract-keywords")
def extract_keywords(body: ExtractKeywordsRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        result = call_ai_extract_keywords(body.job_description, model=body.model)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── PDF endpoints ─────────────────────────────────────────────────────────────

class ResumePDFRequest(BaseModel):
    resume: dict
    font_scale: float = 1.0
    font_family: str = "Helvetica"


@app.post("/api/pdf/resume")
def pdf_resume(body: ResumePDFRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        pdf_bytes = create_resume_pdf_bytes(body.resume, body.font_scale, body.font_family)
        b64 = base64.b64encode(pdf_bytes).decode()
        return {"pdf_base64": b64, "filename": "resume.pdf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoverLetterPDFRequest(BaseModel):
    resume: dict
    font_scale: float = 1.0
    font_family: str = "Helvetica"


@app.post("/api/pdf/cover-letter")
def pdf_cover_letter(body: CoverLetterPDFRequest, x_token: Optional[str] = Header(None)):
    require_auth(x_token)
    try:
        # Ensure cover_letter is present in resume dict
        pdf_bytes = create_cover_letter_pdf_bytes(body.resume, body.font_scale, body.font_family)
        b64 = base64.b64encode(pdf_bytes).decode()
        return {"pdf_base64": b64, "filename": "cover_letter.pdf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# Vercel handler
handler = Mangum(app, lifespan="off")
