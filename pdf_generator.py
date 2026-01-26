# app/pdf_generator.py
import json
import re
from pathlib import Path
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from drawing_utils import (
    PAGE_W, PAGE_H, MIN_LINE_GAP,
    wrap_lines, draw_boxed_block, draw_wrapped_text,
    draw_section_title, draw_bullets, draw_divider,
    draw_page_border
)

def create_resume_pdf(json_path="resume_data.json", 
                     output_path="Rachit_Sharma_Resume_Generated.pdf"):
    """Generate resume PDF from JSON data."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    
    c = canvas.Canvas(output_path, pagesize=A4)
    draw_page_border(c, PAGE_W, PAGE_H)
    
    # Layout constants
    left = 0.5 * cm
    right = 0.5 * cm
    top = 0.75 * cm
    bottom = 0 * cm
    content_w = PAGE_W - left - right
    y = PAGE_H - top
    
    def new_page_if_needed(ypos):
        if ypos < bottom + 2 * cm:
            c.showPage()
            draw_page_border(c, PAGE_W, PAGE_H)
            return PAGE_H - top
        return ypos
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(left, y, data.get("name", "YOUR NAME"))
    y -= 15
    
    c.setFont("Helvetica", 9)
    c.drawString(left, y, data.get("contact", "Location | Phone | Email"))
    y -= 8
    
    # Career Objective
    y = draw_divider(c, left, left + content_w, y)
    y -= 3
    y = new_page_if_needed(y)
    y = draw_section_title(c, "CAREER OBJECTIVE", left, y, size=11)
    
    objective = data.get("career_objective", "")
    y = draw_wrapped_text(c, objective, left, y, content_w, 
                         font="Helvetica", size=10, leading=12)
    y -= 10
    
    # Skills Snapshot
    y = new_page_if_needed(y)
    y = draw_section_title(c, "SKILLS SNAPSHOT", left, y, size=11)
    
    label_w = 4.2 * cm
    gap = 0.6 * cm
    value_x = left + label_w + gap
    value_w = content_w - label_w - gap
    
    for item in (data.get("skills_snapshot") or []):
        y = new_page_if_needed(y)
        label = item.get("label", "")
        value = item.get("value", "")
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, label)
        
        y = draw_wrapped_text(c, value, value_x, y, value_w, 
                             font="Helvetica", size=10, leading=12)
        y -= 2
    
    y -= 10
    
    # Experience
    y = new_page_if_needed(y)
    y = draw_section_title(c, "EXPERIENCE", left, y, size=11)
    
    def exp_block(company, role_line, bullets):
        nonlocal y
        y = new_page_if_needed(y)
        
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(left, y, company)
        y -= 13
        
        c.setFont("Helvetica-Bold", 10)
        y = draw_wrapped_text(c, role_line, left, y, content_w, 
                             font="Helvetica-Bold", size=10, leading=12)
        y -= 2
        
        y = draw_bullets(c, bullets, left, y, content_w, 
                        font="Helvetica", size=10, leading=12)
        y -= 6
    
    for exp in (data.get("experience") or []):
        exp_block(
            exp.get("company", ""),
            exp.get("role_line", ""),
            exp.get("bullets", [])
        )
    
    # Education
    y = draw_section_title(c, "EDUCATION", left, y, size=11)
    y += 15
    
    col_gap = 0.6 * cm
    col_w = (content_w - col_gap) / 2
    x1 = left
    x2 = left + col_w + col_gap
    
    card_padding = 6
    font = "Helvetica"
    size = 8.5
    leading = 11
    edu_items = data.get("education", []) or []
    
    i = 0
    while i < len(edu_items):
        if y < bottom + 4 * cm:
            c.showPage()
            draw_page_border(c, PAGE_W, PAGE_H)
            y = PAGE_H - top
        
        left_item = edu_items[i]
        right_item = edu_items[i + 1] if (i + 1) < len(edu_items) else None
        
        # Left card
        left_lines = []
        deg = left_item.get("degree", "")
        det = left_item.get("details", "")
        left_lines += wrap_lines(deg, col_w - 2 * card_padding, font=font, size=size)
        left_lines += wrap_lines(det, col_w - 2 * card_padding, font=font, size=size)
        
        # Right card
        right_lines = []
        if right_item:
            deg2 = right_item.get("degree", "")
            det2 = right_item.get("details", "")
            right_lines += wrap_lines(deg2, col_w - 2 * card_padding, font=font, size=size)
            right_lines += wrap_lines(det2, col_w - 2 * card_padding, font=font, size=size)
        
        # Make cards same height
        max_lines = max(len(left_lines), len(right_lines) if right_item else 0)
        if len(left_lines) < max_lines:
            left_lines += [""] * (max_lines - len(left_lines))
        if right_item and len(right_lines) < max_lines:
            right_lines += [""] * (max_lines - len(right_lines))
        
        # Draw cards
        y_after_left, h_left = draw_boxed_block(
            c, x1, y, col_w, left_lines,
            padding=card_padding, font=font, size=size, leading=leading
        )
        
        if right_item:
            y_after_right, h_right = draw_boxed_block(
                c, x2, y, col_w, right_lines,
                padding=card_padding, font=font, size=size, leading=leading
            )
            row_height = max(h_left, h_right)
        else:
            row_height = h_left
        
        y = y - row_height - 10
        i += 2
    
    # Certifications
    certs = data.get("certifications") or []
    if certs:
        y = new_page_if_needed(y)
        y = draw_section_title(c, "CERTIFICATIONS", left, y, size=11)
        y = draw_bullets(c, certs, left, y, content_w)
        y = draw_divider(c, left, left + content_w, y)
        y -= 0
    
    # References
    refs = data.get("references") or []
    if refs:
        y = new_page_if_needed(y)
        y = draw_section_title(c, "REFERENCE", left, y-2, size=11)
        for r in refs:
            y = new_page_if_needed(y)
            y = draw_wrapped_text(c, r, left, y, content_w, 
                                 font="Helvetica", size=8, leading=6)
            y -= 4
    
    c.save()
    print(f"✅ Created resume: {output_path}")

def create_cover_letter_pdf(json_path="resume_data.json", 
                           output_path="Cover_Letter.pdf"):
    """Generate cover letter PDF from JSON data."""
    data = json.loads(Path(json_path).read_text(encoding="utf-8"))
    cl = data.get("cover_letter", {})
    
    c = canvas.Canvas(output_path, pagesize=A4)
    draw_page_border(c, PAGE_W, PAGE_H)
    
    left = 0.6 * cm
    right = 0.6 * cm
    top = 1.2 * cm
    bottom = 1.2 * cm
    content_w = PAGE_W - left - right
    y = PAGE_H - top
    
    def new_page_if_needed(ypos):
        if ypos < bottom + 2 * cm:
            c.showPage()
            draw_page_border(c, PAGE_W, PAGE_H)
            return PAGE_H - top
        return ypos
    
    # Date
    date_val = cl.get("date", "AUTO")
    if str(date_val).strip().upper() == "AUTO" or not str(date_val).strip():
        date_val = datetime.now().strftime("%d %B %Y")
    
    c.setFont("Helvetica", 10)
    c.drawString(left, y, str(date_val))
    y -= 18
    
    # Recipient block
    recipient = str(cl.get("recipient", "Hiring Manager")).strip()
    company = str(cl.get("company", "")).strip()
    company_address = str(cl.get("company_address", "")).strip()
    
    c.setFont("Helvetica", 10)
    if recipient:
        c.drawString(left, y, recipient)
        y -= 12
    if company:
        c.drawString(left, y, company)
        y -= 12
    if company_address:
        y = draw_wrapped_text(c, company_address, left, y, content_w, 
                             font="Helvetica", size=10, leading=12)
        y -= 2
    
    y -= 8
    y = new_page_if_needed(y)
    
    # Subject
    role_title = str(cl.get("role_title", "")).strip()
    subject = str(cl.get("subject", "")).strip()
    if role_title and "[Role Title]" in subject:
        subject = subject.replace("[Role Title]", role_title)
    
    if subject:
        c.setFont("Helvetica-Bold", 10.5)
        y = draw_wrapped_text(c, subject, left, y, content_w, 
                             font="Helvetica-Bold", size=10.5, leading=13)
        y -= 6
    
    y = new_page_if_needed(y)
    
    # Greeting
    opening = str(cl.get("opening", "")).strip()
    if opening.lower().startswith("dear"):
        greeting = opening
        opening_for_body = ""
    else:
        greeting = f"Dear {recipient or 'Hiring Manager'},"
        opening_for_body = opening
    
    c.setFont("Helvetica", 10.5)
    c.drawString(left, y, greeting)
    y -= 20
    y = new_page_if_needed(y)
    
    # Main letter body
    body_points = cl.get("body_points", [])
    
    def draw_paragraphs_and_bullets(opening_text, body_list):
        nonlocal y
        c.setFont("Helvetica", 10.5)
        
        def draw_para(text, y_pos):
            return draw_wrapped_text(c, text, left, y_pos, content_w,
                                   font="Helvetica", size=10.5, leading=14)
        
        if opening_text:
            y = draw_para(opening_text, y)
            y -= 8
        
        for p in body_list or []:
            y = draw_para(p, y)
            y -= 8
        
        return y
    
    y = draw_paragraphs_and_bullets(opening_for_body, body_points)
    
    y = new_page_if_needed(y)
    
    # Closing
    closing = str(cl.get("closing", "Kind regards,")).strip()
    y -= 2
    c.setFont("Helvetica", 10.5)
    c.drawString(left, y, closing)
    y -= 22
    
    # Signature + contact
    signature_name = str(cl.get("signature_name", data.get("name", ""))).strip()
    phone_number = str(cl.get("phone_number", "")).strip()
    email = str(cl.get("email", "")).strip()
    
    c.setFont("Helvetica-Bold", 10.5)
    if signature_name:
        c.drawString(left, y, signature_name)
        y -= 14
    
    c.setFont("Helvetica", 10)
    if phone_number:
        c.drawString(left, y, phone_number)
        y -= 12
    if email:
        c.drawString(left, y, email)
        y -= 12
    
    # Word count calculation
    def wc_count(text: str) -> int:
        return len(re.findall(r"\b[\w']+\b", text or ""))
    
    wc_text = " ".join([
        str(date_val),
        recipient, company, company_address,
        subject, greeting,
        opening_for_body,
        " ".join([str(p) for p in body_points]),
        closing,
        signature_name, phone_number, email
    ])
    cl["word_count"] = wc_count(wc_text)
    data["cover_letter"] = cl
    
    # Save updated word_count back to file
    try:
        Path(json_path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    
    c.save()
    print(f"✅ Created cover letter: {output_path}")
