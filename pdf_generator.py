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
                     output_path="Rachit_Sharma_Resume_Generated.pdf"):
    """Generate resume PDF from JSON data."""
    # Read and parse JSON
    try:
        raw_data = json.loads(Path(json_path).read_text(encoding="utf-8"))
        
        # Handle nested structure: {"resume_json": {...}} or direct {...}
        if "resume_json" in raw_data:
            data = raw_data["resume_json"]
            print("✅ Found nested 'resume_json' structure")
        else:
            data = raw_data
            print("✅ Using direct JSON structure")
        
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
    
    # Header - reduced font sizes
    name = data.get("name", "YOUR NAME")
    contact = data.get("contact", "Location | Phone | Email")
    print(f"📝 Drawing Name: {name}")
    print(f"📝 Drawing Contact: {contact}")
    print(f"📝 Starting Y position: {y}")
    
    c.setFont("Helvetica-Bold", 14)  # Reduced from 16
    c.drawString(left, y, name)
    y -= 14  # Reduced spacing
    
    c.setFont("Helvetica", 8.5)  # Reduced from 9
    c.drawString(left, y, contact)
    y -= 7
    print(f"📝 Y after header: {y}")
    
    # Career Objective - ONLY section that can wrap
    y = draw_divider(c, left, left + content_w, y)
    y -= 3
    y = new_page_if_needed(y)
    
    y = draw_section_title(c, "CAREER OBJECTIVE", left, y, size=10)  # Reduced from 11
    
    objective = data.get("career_objective", "")
    print(f"📝 Career Objective length: {len(objective)} chars")
    y = draw_wrapped_text(c, objective, left, y, content_w, font="Helvetica", size=9.5, leading=11)  # Reduced sizes
    y -= 8  # Reduced spacing
    print(f"📝 Y after objective: {y}")
    
    # Skills Snapshot - Fixed width, no wrapping for labels
    y = new_page_if_needed(y)
    y = draw_section_title(c, "SKILLS SNAPSHOT", left, y, size=10)  # Reduced from 11
    
    label_w = 5.5 * cm  # Increased to fit longer labels on one line
    gap = 0.4 * cm
    value_x = left + label_w + gap
    value_w = content_w - label_w - gap
    
    skills_count = 0
    for item in (data.get("skills_snapshot") or []):
        y = new_page_if_needed(y)
        label = item.get("label", "")
        value = item.get("value", "")
        
        # Draw label - NO WRAPPING, truncate if too long
        c.setFont("Helvetica-Bold", 9.5)  # Reduced from 10
        c.drawString(left, y, label)
        
        # Draw value on SAME LINE (no wrapping)
        c.setFont("Helvetica", 9.5)  # Reduced from 10
        c.drawString(value_x, y, value)
        
        y -= 11  # Reduced spacing
        skills_count += 1
    
    print(f"📝 Drew {skills_count} skills entries")
    y -= 8  # Reduced spacing
    
    # Experience
    y = new_page_if_needed(y)
    y = draw_section_title(c, "EXPERIENCE", left, y, size=10)  # Reduced from 11
    
    def exp_block(company, role_line, bullets):
        nonlocal y
        y = new_page_if_needed(y)
        
        # Company name - single line, no wrapping
        c.setFont("Helvetica-Bold", 10)  # Reduced from 10.5
        c.drawString(left, y, company)
        y -= 12  # Reduced spacing
        
        # Role line - single line, no wrapping
        c.setFont("Helvetica-Bold", 9.5)  # Reduced from 10
        c.drawString(left, y, role_line)
        y -= 12  # Reduced spacing
        
        # Bullets - NO WRAPPING, each bullet is single line
        c.setFont("Helvetica", 9)  # Reduced from 9.5
        for bullet in bullets:
            c.drawString(left, y, "•")
            c.drawString(left + 10, y, bullet)
            y -= 10  # Reduced spacing
        
        y -= 5  # Reduced spacing
    
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
    y = draw_section_title(c, "EDUCATION", left, y, size=10)  # Reduced from 11
    y += .5
                         # Reduced spacing
    
    col_gap = 0.6 * cm
    col_w = (content_w - col_gap) / 2
    x1 = left
    x2 = left + col_w + col_gap
    
    font = "Helvetica"
    size = 8  # Reduced from 8.5
    leading = 10  # Reduced from 11
    edu_items = data.get("education", []) or []
    
    print(f"📝 Drawing {len(edu_items)} education entries")
    
    i = 0
    while i < len(edu_items):
        if y < bottom + 4 * cm:
            c.showPage()
            #draw_page_border(c, PAGE_W, PAGE_H)
            y = PAGE_H - top
        
        left_item = edu_items[i]
        right_item = edu_items[i + 1] if (i + 1) < len(edu_items) else None
        
        # Left card - NO WRAPPING, just single lines
        c.setFont(font, size)
        deg = left_item.get("degree", "")
        det = left_item.get("details", "")
        
        # Draw left education (no box, just text)
        c.drawString(x1, y, deg)
        y_temp = y - leading
        c.drawString(x1, y_temp, det)
        
        # Right card if exists
        if right_item:
            deg2 = right_item.get("degree", "")
            det2 = right_item.get("details", "")
            c.drawString(x2, y, deg2)
            c.drawString(x2, y_temp, det2)
        
        y = y_temp - 12  # Reduced spacing
        i += 2
    
    # Certifications
    certs = data.get("certifications") or []
    if certs:
        y = new_page_if_needed(y)
        y = draw_section_title(c, "CERTIFICATIONS", left, y, size=10)  # Reduced from 11
        
        # Draw certifications as single lines (no wrapping)
        c.setFont("Helvetica", 9)
        for cert in certs:
            c.drawString(left, y, "•")
            c.drawString(left + 10, y, cert)
            y -= 10
        
        y = draw_divider(c, left, left + content_w, y)
        y -= 0
        print(f"📝 Drew {len(certs)} certifications")
    
    # References
    refs = data.get("references") or []
    if refs:
        y = new_page_if_needed(y)
        y = draw_section_title(c, "REFERENCE", left, y-2, size=10)  # Reduced from 11
        for r in refs:
            y = new_page_if_needed(y)
            # Single line reference, no wrapping
            c.setFont("Helvetica", 7.5)  # Reduced from 8
            c.drawString(left, y, r)
            y -= 9  # Reduced spacing
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
        if "resume_json" in raw_data:
            raw_data["resume_json"] = data
        else:
            raw_data = data
        Path(json_path).write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    
    c.save()
    print(f"✅ Created cover letter: {output_path}")
