# -*- coding: utf-8 -*-
# pdf_generator.py
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
                      output_path="Rachit_Sharma_Resume_Generated.pdf",
                      font_scale=1.0,           # ✅ CORRECT - actual value
                      font_family="Helvetica"): # ✅ CORRECT - actual value
    """Generate resume PDF from JSON data with customizable fonts.
    
    Args:
        json_path: Path to JSON file
        output_path: Output PDF path
        font_scale: Scale factor for all fonts (0.5 to 1.5, default 1.0)
        font_family: Font family - 'Helvetica', 'Times', or 'Courier'
    """
    # Font family mapping
    if font_family == "Times":
        font_regular = "Times-Roman"
        font_bold = "Times-Bold"
    elif font_family == "Courier":
        font_regular = "Courier"
        font_bold = "Courier-Bold"
    else:  # Helvetica (default)
        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"
    
    # Apply font scale to all font sizes
    font_name = font_scale * 14
    font_contact = font_scale * 8.5
    font_section_title = font_scale * 10
    font_objective = font_scale * 9.5
    font_skills_label = font_scale * 9.5
    font_skills_value = font_scale * 9.5
    font_company = font_scale * 10
    font_role = font_scale * 9.5
    font_bullet = font_scale * 9
    font_education = font_scale * 8
    font_certification = font_scale * 9
    font_reference = font_scale * 7.5
    
    # Apply spacing scale
    spacing_after_name = font_scale * 14
    spacing_after_contact = font_scale * 7
    spacing_after_objective = font_scale * 8
    spacing_after_skills_section = font_scale * 8
    spacing_skills_line = font_scale * 11
    spacing_after_company = font_scale * 12
    spacing_after_role = font_scale * 12
    spacing_bullet_line = font_scale * 10
    spacing_after_exp_block = font_scale * 5
    spacing_edu_line = font_scale * 10
    spacing_edu_block = font_scale * 12
    spacing_cert_line = font_scale * 10
    spacing_ref_line = font_scale * 9

    # Read and parse JSON
    try:
        raw_data = json.loads(Path(json_path).read_text(encoding="utf-8"))

        # Handle nested structure
        if "resume_json" in raw_data:
            data = raw_data["resume_json"]
            if isinstance(data, dict) and "resume_json" in data:
                data = data["resume_json"]
                print("⚠️ Fixed double-nested resume_json structure")
        else:
            data = raw_data

        print(f"✅ Loaded JSON data with keys: {list(data.keys())}")
        print(f"🎨 Font Scale: {font_scale}")
        print(f"🔤 Font Family: {font_family}")
    except Exception as e:
        print(f"❌ Error loading JSON: {e}")
        raise

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
    name = data.get("name", "YOUR NAME")
    contact = data.get("contact", "Location | Phone | Email")

    c.setFont(font_bold, font_name)
    c.drawString(left, y, name)
    y -= spacing_after_name

    c.setFont(font_regular, font_contact)
    c.drawString(left, y, contact)
    y -= spacing_after_contact

    # Career Objective
    y = draw_divider(c, left, left + content_w, y)
    y -= 3
    y = new_page_if_needed(y)

    c.setFont(font_bold, font_section_title)
    c.drawString(left, y, "CAREER OBJECTIVE")
    y -= (14 * font_scale + MIN_LINE_GAP)

    objective = data.get("career_objective", "")
    c.setFont(font_regular, font_objective)
    obj_lines = wrap_lines(objective, content_w, font=font_regular, size=font_objective)
    for oline in obj_lines:
        c.drawString(left, y, oline)
        y -= 11 * font_scale
    y -= spacing_after_objective

    # Skills Snapshot
    y = new_page_if_needed(y)
    c.setFont(font_bold, font_section_title)
    c.drawString(left, y, "SKILLS SNAPSHOT")
    y -= (14 * font_scale + MIN_LINE_GAP)

    label_w = 5.5 * cm
    gap = 0.4 * cm
    value_x = left + label_w + gap
    value_w = content_w - label_w - gap

    for item in (data.get("skills_snapshot") or []):
        y = new_page_if_needed(y)
        label = item.get("label", "")
        value = item.get("value", "")

        c.setFont(font_bold, font_skills_label)
        c.drawString(left, y, label)

        c.setFont(font_regular, font_skills_value)
        value_lines = wrap_lines(value, value_w, font=font_regular, size=font_skills_value)
        for vline in value_lines:
            c.drawString(value_x, y, vline)
            y -= spacing_skills_line

        if len(value_lines) > 1:
            y -= 2

    y -= spacing_after_skills_section

    # Experience
    y = new_page_if_needed(y)
    c.setFont(font_bold, font_section_title)
    c.drawString(left, y, "EXPERIENCE")
    y -= (14 * font_scale + MIN_LINE_GAP)

    def exp_block(company, role_line, bullets):
        nonlocal y
        y = new_page_if_needed(y)

        c.setFont(font_bold, font_company)
        c.drawString(left, y, company)
        y -= spacing_after_company

        c.setFont(font_bold, font_role)
        role_lines = wrap_lines(role_line, content_w, font=font_bold, size=font_role)
        for rline in role_lines:
            c.drawString(left, y, rline)
            y -= spacing_after_role

        c.setFont(font_regular, font_bullet)
        for bullet in bullets:
            bullet_lines = wrap_lines(bullet, content_w - 10, font=font_regular, size=font_bullet)
            for i, bline in enumerate(bullet_lines):
                if i == 0:
                    c.drawString(left, y, "•")
                    c.drawString(left + 10, y, bline)
                else:
                    c.drawString(left + 10, y, bline)
                y -= spacing_bullet_line

        y -= spacing_after_exp_block

    for exp in (data.get("experience") or []):
        exp_block(
            exp.get("company", ""),
            exp.get("role_line", ""),
            exp.get("bullets", [])
        )

    # Education
    y = new_page_if_needed(y)
    c.setFont(font_bold, font_section_title)
    c.drawString(left, y, "EDUCATION")
    y -= (14 * font_scale + MIN_LINE_GAP)

    edu_items = data.get("education", []) or []
    
    c.setFont(font_regular, font_education)
    for edu in edu_items:
        y = new_page_if_needed(y)
        
        degree = edu.get("degree", "")
        details = edu.get("details", "")
        
        # Degree on first line
        c.setFont(font_bold, font_education)
        c.drawString(left, y, degree)
        y -= spacing_edu_line
        
        # Details on second line
        c.setFont(font_regular, font_education)
        c.drawString(left, y, details)
        y -= spacing_edu_block

    # Certifications
    certs = data.get("certifications") or []
    if certs:
        y = new_page_if_needed(y)
        c.setFont(font_bold, font_section_title)
        c.drawString(left, y, "CERTIFICATIONS")
        y -= (14 * font_scale + MIN_LINE_GAP)

        c.setFont(font_regular, font_certification)
        for cert in certs:
            cert_lines = wrap_lines(cert, content_w - 10, font=font_regular, size=font_certification)
            for i, cline in enumerate(cert_lines):
                if i == 0:
                    c.drawString(left, y, "•")
                    c.drawString(left + 10, y, cline)
                else:
                    c.drawString(left + 10, y, cline)
                y -= spacing_cert_line

        y = draw_divider(c, left, left + content_w, y)

    # Additional Information
    additional_info = data.get("additional_information") or {}
    if isinstance(additional_info, dict) and additional_info:
        y = new_page_if_needed(y)
        c.setFont(font_bold, font_section_title)
        c.drawString(left, y, "ADDITIONAL INFORMATION")
        y -= (14 * font_scale + MIN_LINE_GAP)

        c.setFont(font_regular, font_certification)
        for key, value in additional_info.items():
            label = str(key).replace("_", " ").title()
            line = f"{label}: {value}"
            info_lines = wrap_lines(line, content_w - 10, font=font_regular, size=font_certification)
            for i, iline in enumerate(info_lines):
                if i == 0:
                    c.drawString(left, y, "•")
                    c.drawString(left + 10, y, iline)
                else:
                    c.drawString(left + 10, y, iline)
                y -= spacing_cert_line

        y = draw_divider(c, left, left + content_w, y)

    # References
    refs = data.get("references") or []
    if refs:
        y = new_page_if_needed(y)
        c.setFont(font_bold, font_section_title)
        c.drawString(left, y - 2, "REFERENCE")
        y -= (14 * font_scale + MIN_LINE_GAP)
        
        for r in refs:
            y = new_page_if_needed(y)
            c.setFont(font_regular, font_reference)
            c.drawString(left, y, r)
            y -= spacing_ref_line

    c.save()
    print(f"✅ PDF saved to: {output_path}")

    if Path(output_path).exists():
        file_size = Path(output_path).stat().st_size
        print(f"✅ File created successfully: {file_size} bytes")
    else:
        print(f"❌ WARNING: File not found after save: {output_path}")


def create_cover_letter_pdf(json_path="resume_data.json",
                            output_path="Cover_Letter.pdf",
                            font_scale=1.0,
                            font_family="Helvetica"):
    """Generate cover letter PDF from JSON data with customizable fonts.
    
    Args:
        json_path: Path to JSON file
        output_path: Output PDF path
        font_scale: Scale factor for all fonts (0.5 to 1.5, default 1.0)
        font_family: Font family - 'Helvetica', 'Times', or 'Courier'
    """
    # Font family mapping
    if font_family == "Times":
        font_regular = "Times-Roman"
        font_bold = "Times-Bold"
    elif font_family == "Courier":
        font_regular = "Courier"
        font_bold = "Courier-Bold"
    else:  # Helvetica (default)
        font_regular = "Helvetica"
        font_bold = "Helvetica-Bold"

    raw_data = json.loads(Path(json_path).read_text(encoding="utf-8"))

    # Handle nested structure
    if "resume_json" in raw_data:
        data = raw_data["resume_json"]
        if isinstance(data, dict) and "resume_json" in data:
            data = data["resume_json"]
    else:
        data = raw_data

    cl = data.get("cover_letter", {})

    # Backward compatibility: recover malformed nested cover_letter shapes.
    for _ in range(4):
        if isinstance(cl, dict) and isinstance(cl.get("cover_letter"), dict):
            cl = cl.get("cover_letter", {})
        else:
            break

    if not isinstance(cl, dict):
        cl = {}

    body_points = cl.get("body_points", [])
    if isinstance(body_points, str):
        body_points = [body_points]
    if not isinstance(body_points, list):
        body_points = []
    cl["body_points"] = [str(p).strip() for p in body_points if str(p).strip()]

    if not cl["body_points"]:
        fallback = str(data.get("career_objective", "")).strip()
        if fallback:
            cl["body_points"] = [fallback]

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

    c.setFont(font_regular, 10 * font_scale)
    c.drawString(left, y, str(date_val))
    y -= 18 * font_scale

    # Recipient block
    recipient = str(cl.get("recipient", "Hiring Manager")).strip()
    company = str(cl.get("company", "")).strip()
    company_address = str(cl.get("company_address", "")).strip()

    c.setFont(font_regular, 10 * font_scale)
    if recipient:
        c.drawString(left, y, recipient)
        y -= 12 * font_scale
    if company:
        c.drawString(left, y, company)
        y -= 12 * font_scale
    if company_address:
        addr_lines = wrap_lines(company_address, content_w, font=font_regular, size=10 * font_scale)
        for addr_line in addr_lines:
            c.drawString(left, y, addr_line)
            y -= 12 * font_scale
        y -= 2

    y -= 8 * font_scale
    y = new_page_if_needed(y)

    # Subject
    role_title = str(cl.get("role_title", "")).strip()
    subject = str(cl.get("subject", "")).strip()
    if role_title and "[Role Title]" in subject:
        subject = subject.replace("[Role Title]", role_title)

    if subject:
        c.setFont(font_bold, 10.5 * font_scale)
        subj_lines = wrap_lines(subject, content_w, font=font_bold, size=10.5 * font_scale)
        for sline in subj_lines:
            c.drawString(left, y, sline)
            y -= 13 * font_scale
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

    c.setFont(font_regular, 10.5 * font_scale)
    c.drawString(left, y, greeting)
    y -= 20 * font_scale
    y = new_page_if_needed(y)

    # Main letter body
    body_points = cl.get("body_points", [])

    if opening_for_body:
        open_lines = wrap_lines(opening_for_body, content_w, font=font_regular, size=10.5 * font_scale)
        for oline in open_lines:
            c.drawString(left, y, oline)
            y -= 14 * font_scale
        y -= 8 * font_scale

    for p in body_points or []:
        para_lines = wrap_lines(p, content_w, font=font_regular, size=10.5 * font_scale)
        for pline in para_lines:
            c.drawString(left, y, pline)
            y -= 14 * font_scale
        y -= 8 * font_scale

    y = new_page_if_needed(y)

    # Closing
    closing = str(cl.get("closing", "Kind regards,")).strip()
    y -= 2
    c.setFont(font_regular, 10.5 * font_scale)
    c.drawString(left, y, closing)
    y -= 22 * font_scale

    # Signature + contact
    signature_name = str(cl.get("signature_name", data.get("name", ""))).strip()
    phone_number = str(cl.get("phone_number", "")).strip()
    email = str(cl.get("email", "")).strip()

    c.setFont(font_bold, 10.5 * font_scale)
    if signature_name:
        c.drawString(left, y, signature_name)
        y -= 14 * font_scale

    c.setFont(font_regular, 10 * font_scale)
    if phone_number:
        c.drawString(left, y, phone_number)
        y -= 12 * font_scale
    if email:
        c.drawString(left, y, email)
        y -= 12 * font_scale

    # Word count calculation
    def wc_count(text: str) -> int:
        return len(re.findall(r"\b[\w']+\b", text or ""))

    # Calculate word count for body only (excluding header/footer)
    body_text = " ".join([str(p) for p in body_points])
    body_word_count = wc_count(body_text)
    
    # Calculate total word count (everything)
    wc_text = " ".join([
        str(date_val),
        recipient, company, company_address,
        subject, greeting,
        opening_for_body,
        " ".join([str(p) for p in body_points]),
        closing,
        signature_name, phone_number, email
    ])
    total_word_count = wc_count(wc_text)
    
    cl["word_count"] = total_word_count
    cl["body_word_count"] = body_word_count
    data["cover_letter"] = cl

    # Save updated word_count back to file
    try:
        if "resume_json" in raw_data:
            raw_data["resume_json"] = data
        else:
            raw_data = data
        Path(json_path).write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    c.save()
    print(f"✅ Created cover letter: {output_path}")
