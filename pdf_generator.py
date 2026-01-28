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

# ============== FONT CONFIGURATION ==============
# Adjust this single scale factor to change ALL fonts proportionally
# 1.0 = normal size, 0.9 = 10% smaller, 0.8 = 20% smaller
FONT_SCALE = 1.0


class FontConfig:
    """Centralized font configuration - change FONT_SCALE to adjust all fonts"""
    NAME = 14 * FONT_SCALE
    CONTACT = 8.5 * FONT_SCALE
    SECTION_TITLE = 10 * FONT_SCALE
    OBJECTIVE = 9.5 * FONT_SCALE
    SKILLS_LABEL = 9.5 * FONT_SCALE
    SKILLS_VALUE = 9.5 * FONT_SCALE
    COMPANY = 10 * FONT_SCALE
    ROLE = 9.5 * FONT_SCALE
    BULLET = 9 * FONT_SCALE
    EDUCATION = 8 * FONT_SCALE
    CERTIFICATION = 9 * FONT_SCALE
    REFERENCE = 7.5 * FONT_SCALE


class SpacingConfig:
    """Centralized spacing configuration"""
    AFTER_NAME = 14 * FONT_SCALE
    AFTER_CONTACT = 7 * FONT_SCALE
    AFTER_OBJECTIVE = 8 * FONT_SCALE
    AFTER_SKILLS_SECTION = 8 * FONT_SCALE
    SKILLS_LINE = 11 * FONT_SCALE
    AFTER_COMPANY = 12 * FONT_SCALE
    AFTER_ROLE = 12 * FONT_SCALE
    BULLET_LINE = 10 * FONT_SCALE
    AFTER_EXP_BLOCK = 5 * FONT_SCALE
    EDU_LINE = 10 * FONT_SCALE
    EDU_BLOCK = 12 * FONT_SCALE
    CERT_LINE = 10 * FONT_SCALE
    REF_LINE = 9 * FONT_SCALE


def create_resume_pdf(json_path="resume_data.json",
                      output_path="Rachit_Sharma_Resume_Generated.pdf"):
    """Generate resume PDF from JSON data."""
    # Read and parse JSON
    try:
        raw_data = json.loads(Path(json_path).read_text(encoding="utf-8"))

        # Handle nested structure: {"resume_json": {...}} or direct {...}
        # Also handle double-nested: {"resume_json": {"resume_json": {...}}}
        if "resume_json" in raw_data:
            data = raw_data["resume_json"]
            # Check for double nesting
            if isinstance(data, dict) and "resume_json" in data:
                data = data["resume_json"]
                print("⚠️ Fixed double-nested resume_json structure")
        else:
            data = raw_data

        print(f"✅ Loaded JSON data with keys: {list(data.keys())}")
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
    print(f"📝 Drawing Name: {name}")
    print(f"📝 Drawing Contact: {contact}")
    print(f"📝 Starting Y position: {y}")
    print(f"📝 Font Scale: {FONT_SCALE}")

    c.setFont("Helvetica-Bold", FontConfig.NAME)
    c.drawString(left, y, name)
    y -= SpacingConfig.AFTER_NAME

    c.setFont("Helvetica", FontConfig.CONTACT)
    c.drawString(left, y, contact)
    y -= SpacingConfig.AFTER_CONTACT
    print(f"📝 Y after header: {y}")

    # Career Objective - ONLY section that can wrap
    y = draw_divider(c, left, left + content_w, y)
    y -= 3
    y = new_page_if_needed(y)

    y = draw_section_title(c, "CAREER OBJECTIVE", left, y, size=FontConfig.SECTION_TITLE)

    objective = data.get("career_objective", "")
    print(f"📝 Career Objective length: {len(objective)} chars")
    y = draw_wrapped_text(
        c,
        objective,
        left,
        y,
        content_w,
        font="Helvetica",
        size=FontConfig.OBJECTIVE,
        leading=11 * FONT_SCALE
    )
    y -= SpacingConfig.AFTER_OBJECTIVE
    print(f"📝 Y after objective: {y}")

    # Skills Snapshot - NOW WITH WRAPPING
    y = new_page_if_needed(y)
    y = draw_section_title(c, "SKILLS SNAPSHOT", left, y, size=FontConfig.SECTION_TITLE)

    label_w = 5.5 * cm
    gap = 0.4 * cm
    value_x = left + label_w + gap
    value_w = content_w - label_w - gap

    skills_count = 0
    for item in (data.get("skills_snapshot") or []):
        y = new_page_if_needed(y)
        label = item.get("label", "")
        value = item.get("value", "")

        c.setFont("Helvetica-Bold", FontConfig.SKILLS_LABEL)
        c.drawString(left, y, label)

        # Wrap the value text instead of single line
        c.setFont("Helvetica", FontConfig.SKILLS_VALUE)
        value_lines = wrap_lines(value, value_w, font="Helvetica", size=FontConfig.SKILLS_VALUE)
        for vline in value_lines:
            c.drawString(value_x, y, vline)
            y -= SpacingConfig.SKILLS_LINE

        # Add small gap if wrapped multiple lines
        if len(value_lines) > 1:
            y -= 2

        skills_count += 1

    print(f"📝 Drew {skills_count} skills entries")
    y -= SpacingConfig.AFTER_SKILLS_SECTION

    # Experience - WITH WRAPPING
    y = new_page_if_needed(y)
    y = draw_section_title(c, "EXPERIENCE", left, y, size=FontConfig.SECTION_TITLE)

    def exp_block(company, role_line, bullets):
        nonlocal y
        y = new_page_if_needed(y)

        c.setFont("Helvetica-Bold", FontConfig.COMPANY)
        c.drawString(left, y, company)
        y -= SpacingConfig.AFTER_COMPANY

        # Wrap role line
        c.setFont("Helvetica-Bold", FontConfig.ROLE)
        role_lines = wrap_lines(role_line, content_w, font="Helvetica-Bold", size=FontConfig.ROLE)
        for rline in role_lines:
            c.drawString(left, y, rline)
            y -= SpacingConfig.AFTER_ROLE

        # Wrap bullets
        c.setFont("Helvetica", FontConfig.BULLET)
        for bullet in bullets:
            bullet_lines = wrap_lines(bullet, content_w - 10, font="Helvetica", size=FontConfig.BULLET)
            for i, bline in enumerate(bullet_lines):
                if i == 0:
                    c.drawString(left, y, "•")
                    c.drawString(left + 10, y, bline)
                else:
                    c.drawString(left + 10, y, bline)
                y -= SpacingConfig.BULLET_LINE

        y -= SpacingConfig.AFTER_EXP_BLOCK

    exp_count = 0
    for exp in (data.get("experience") or []):
        exp_block(
            exp.get("company", ""),
            exp.get("role_line", ""),
            exp.get("bullets", [])
        )
        exp_count += 1

    print(f"📝 Drew {exp_count} experience entries")

    # Education
    y = new_page_if_needed(y)
    y = draw_section_title(c, "EDUCATION", left, y, size=FontConfig.SECTION_TITLE)
    y -= 3

    col_gap = 0.6 * cm
    col_w = (content_w - col_gap) / 2
    x1 = left
    x2 = left + col_w + col_gap

    edu_items = data.get("education", []) or []
    print(f"📝 Drawing {len(edu_items)} education entries")

    i = 0
    while i < len(edu_items):
        if y < bottom + 4 * cm:
            c.showPage()
            draw_page_border(c, PAGE_W, PAGE_H)
            y = PAGE_H - top

        left_item = edu_items[i]
        right_item = edu_items[i + 1] if (i + 1) < len(edu_items) else None

        c.setFont("Helvetica", FontConfig.EDUCATION)
        deg = left_item.get("degree", "")
        det = left_item.get("details", "")

        c.drawString(x1, y, deg)
        y_temp = y - SpacingConfig.EDU_LINE
        c.drawString(x1, y_temp, det)

        if right_item:
            deg2 = right_item.get("degree", "")
            det2 = right_item.get("details", "")
            c.drawString(x2, y, deg2)
            c.drawString(x2, y_temp, det2)

        y = y_temp - SpacingConfig.EDU_BLOCK
        i += 2

    # Certifications - WITH WRAPPING
    certs = data.get("certifications") or []
    if certs:
        y = new_page_if_needed(y)
        y = draw_section_title(c, "CERTIFICATIONS", left, y, size=FontConfig.SECTION_TITLE)

        c.setFont("Helvetica", FontConfig.CERTIFICATION)
        for cert in certs:
            cert_lines = wrap_lines(cert, content_w - 10, font="Helvetica", size=FontConfig.CERTIFICATION)
            for i, cline in enumerate(cert_lines):
                if i == 0:
                    c.drawString(left, y, "•")
                    c.drawString(left + 10, y, cline)
                else:
                    c.drawString(left + 10, y, cline)
                y -= SpacingConfig.CERT_LINE

        y = draw_divider(c, left, left + content_w, y)
        print(f"📝 Drew {len(certs)} certifications")

    # References
    refs = data.get("references") or []
    if refs:
        y = new_page_if_needed(y)
        y = draw_section_title(c, "REFERENCE", left, y - 2, size=FontConfig.SECTION_TITLE)
        for r in refs:
            y = new_page_if_needed(y)
            c.setFont("Helvetica", FontConfig.REFERENCE)
            c.drawString(left, y, r)
            y -= SpacingConfig.REF_LINE
        print(f"📝 Drew {len(refs)} references")

    c.save()
    print(f"✅ PDF saved to: {output_path}")

    # Verify file was created
    if Path(output_path).exists():
        file_size = Path(output_path).stat().st_size
        print(f"✅ File created successfully: {file_size} bytes")
    else:
        print(f"❌ WARNING: File not found after save: {output_path}")


def create_cover_letter_pdf(json_path="resume_data.json",
                            output_path="Cover_Letter.pdf"):
    """Generate cover letter PDF from JSON data."""
    raw_data = json.loads(Path(json_path).read_text(encoding="utf-8"))

    # Handle nested structure
    if "resume_json" in raw_data:
        data = raw_data["resume_json"]
        if isinstance(data, dict) and "resume_json" in data:
            data = data["resume_json"]
    else:
        data = raw_data

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
        y = draw_wrapped_text(
            c,
            company_address,
            left,
            y,
            content_w,
            font="Helvetica",
            size=10,
            leading=12
        )
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
        y = draw_wrapped_text(
            c,
            subject,
            left,
            y,
            content_w,
            font="Helvetica-Bold",
            size=10.5,
            leading=13
        )
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
            return draw_wrapped_text(
                c,
                text,
                left,
                y_pos,
                content_w,
                font="Helvetica",
                size=10.5,
                leading=14
            )

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
        return len(re.findall(r"\\b[\\w']+\\b", text or ""))

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
        if "resume_json" in raw_data:
            raw_data["resume_json"] = data
        else:
            raw_data = data
        Path(json_path).write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    c.save()
    print(f"✅ Created cover letter: {output_path}")
