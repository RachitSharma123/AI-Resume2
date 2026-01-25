# __init__.py
from pdf_generator import create_resume_pdf, create_cover_letter_pdf
from utils import safe_filename, open_pdf_in_new_tab
from drawing_utils import (
    PAGE_W, PAGE_H, MIN_LINE_GAP,
    wrap_lines, draw_boxed_block, draw_wrapped_text,
    draw_section_title, draw_bullets, draw_divider,
    draw_page_border
)
from ai_functions import (
    call_ai_tailor_resume,
    call_ai_generate_cover_letter,
    call_ai_ats_score,
    call_ai_improve_bullets,
    call_ai_extract_keywords,
    call_ai_rewrite_objective,
    call_ai_compress_resume
)

__all__ = [
    'create_resume_pdf',
    'create_cover_letter_pdf',
    'safe_filename',
    'open_pdf_in_new_tab',
    'PAGE_W', 'PAGE_H', 'MIN_LINE_GAP',
    'wrap_lines', 'draw_boxed_block', 'draw_wrapped_text',
    'draw_section_title', 'draw_bullets', 'draw_divider',
    'draw_page_border',
    'call_ai_tailor_resume',
    'call_ai_generate_cover_letter',
    'call_ai_ats_score',
    'call_ai_improve_bullets',
    'call_ai_extract_keywords',
    'call_ai_rewrite_objective',
    'call_ai_compress_resume'
]
