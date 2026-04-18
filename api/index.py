import sys
import os
import io
import base64

# Add repo root to path so we can import existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from mangum import Mangum

import pypdf

from ai_functions import (
    call_ai_tailor_resume,
    call_ai_generate_cover_letter,
    call_ai_ats_score,
    call_ai_improve_bullets,
    call_ai_extract_keywords,
    call_ai_rewrite_objective,
    call_ai_compress_resume,
    call_ai_improve_from_ats,
    call_ai_extract_resume_from_text,
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


# ── Resume extraction ──────────────────────────────────────────────────────────


@app.post("/api/extract-resume")
async def extract_resume(file: UploadFile = File(...)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    contents = await file.read()
    if len(contents) > 10_000_000:
        raise HTTPException(
            status_code=413, detail="File too large. Maximum size is 10MB."
        )

    try:
        reader = pypdf.PdfReader(io.BytesIO(contents))
        raw_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read PDF: {str(e)}")

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Could not extract text from this PDF. It may be a scanned image. Please use a text-based PDF or paste your resume text manually.",
        )

    try:
        result = call_ai_extract_resume_from_text(raw_text)
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── AI endpoints ──────────────────────────────────────────────────────────────


class TailorRequest(BaseModel):
    resume: dict
    job_description: str
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


@app.post("/api/tailor")
def tailor_resume(body: TailorRequest):
    try:
        result = call_ai_tailor_resume(
            body.resume, body.job_description, model=body.model
        )
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoverLetterRequest(BaseModel):
    resume: dict
    job_description: str
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


@app.post("/api/cover-letter")
def cover_letter(body: CoverLetterRequest):
    try:
        result = call_ai_generate_cover_letter(
            body.resume, body.job_description, model=body.model
        )
        return {"cover_letter": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ATSRequest(BaseModel):
    resume: dict
    job_description: str
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


@app.post("/api/ats-score")
def ats_score(body: ATSRequest):
    try:
        result = call_ai_ats_score(body.resume, body.job_description, model=body.model)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImproveBulletsRequest(BaseModel):
    bullets: List[str]
    job_description: str
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


@app.post("/api/improve-bullets")
def improve_bullets(body: ImproveBulletsRequest):
    try:
        result = call_ai_improve_bullets(
            body.bullets, body.job_description, model=body.model
        )
        return {"bullets": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CompressRequest(BaseModel):
    resume: dict
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


class ImproveFromATSRequest(BaseModel):
    resume: dict
    ats_results: dict
    job_description: str
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


class ExtractKeywordsRequest(BaseModel):
    job_description: str
    model: str = "nvidia/nemotron-3-super-120b-a12b:free"


@app.post("/api/compress")
def compress_resume(body: CompressRequest):
    try:
        result = call_ai_compress_resume(body.resume, model=body.model)
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ImproveFromATSRequest(BaseModel):
    resume: dict
    ats_results: dict
    job_description: str
    model: str = "deepseek-chat"


@app.post("/api/improve-from-ats")
def improve_from_ats(body: ImproveFromATSRequest):
    try:
        result = call_ai_improve_from_ats(
            body.resume, body.ats_results, body.job_description, model=body.model
        )
        return {"resume": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ExtractKeywordsRequest(BaseModel):
    job_description: str
    model: str = "deepseek-chat"


@app.post("/api/extract-keywords")
def extract_keywords(body: ExtractKeywordsRequest):
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
def pdf_resume(body: ResumePDFRequest):
    try:
        pdf_bytes = create_resume_pdf_bytes(
            body.resume, body.font_scale, body.font_family
        )
        b64 = base64.b64encode(pdf_bytes).decode()
        return {"pdf_base64": b64, "filename": "resume.pdf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CoverLetterPDFRequest(BaseModel):
    resume: dict
    font_scale: float = 1.0
    font_family: str = "Helvetica"


@app.post("/api/pdf/cover-letter")
def pdf_cover_letter(body: CoverLetterPDFRequest):
    try:
        pdf_bytes = create_cover_letter_pdf_bytes(
            body.resume, body.font_scale, body.font_family
        )
        b64 = base64.b64encode(pdf_bytes).decode()
        return {"pdf_base64": b64, "filename": "cover_letter.pdf"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Health ────────────────────────────────────────────────────────────────────


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/debug")
def debug():
    from ai_functions import _resolve_provider_config
    try:
        cfg = _resolve_provider_config()
        return {"provider": cfg["provider"], "key": cfg["api_key"][:12]+"...", "base_url": cfg["base_url"], "model": cfg["default_model"]}
    except Exception as e:
        return {"error": str(e), "raw_provider": os.getenv("AI_PROVIDER"), "raw_or_key": (os.getenv("OPENROUTER_API_KEY") or "")[:12]}


# Vercel handler
handler = Mangum(app, lifespan="off")
