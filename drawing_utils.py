# app/drawing_utils.py
from reportlab.lib.units import cm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.pagesizes import A4

PAGE_W, PAGE_H = A4
MIN_LINE_GAP = 0.8

def wrap_lines(text, max_width, font="Helvetica", size=9.5):
    """Return wrapped lines (list[str]) without drawing."""
    words = str(text).split()
    if not words:
        return []
    
    line = ""
    lines = []
    for w in words:
        test = (line + " " + w).strip()
        if stringWidth(test, font, size) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def draw_boxed_block(c, x, y, width, lines, padding=6, font="Helvetica", 
                     size=9.5, leading=11, line_gap=0):
    """
    Draws a thin bordered box with wrapped text lines.
    (x,y) is top-left of the box.
    Returns (new_y, box_height)
    """
    text_lines = []
    for ln in lines:
        text_lines.append(str(ln))
    
    box_height = padding * 2 + (len(text_lines) * leading) + \
                (max(0, len(text_lines) - 1) * line_gap)
    
    # Border
    c.setLineWidth(0.5)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(x, y - box_height, width, box_height, stroke=1, fill=0)
    
    # Text
    c.setFont(font, size)
    ty = y - padding - size
    for ln in text_lines:
        c.drawString(x + padding, ty, ln)
        ty -= leading + line_gap
    
    return y, box_height

def draw_wrapped_text(c, text, x, y, max_width, font="Helvetica", 
                      size=9.5, leading=11, min_gap=MIN_LINE_GAP):
    """Draw wrapped text on canvas."""
    c.setFont(font, size)
    words = str(text).split()
    line = ""
    lines = []
    
    for w in words:
        test = (line + " " + w).strip()
        if stringWidth(test, font, size) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    
    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading
    
    y -= min_gap
    return y

def draw_section_title(c, title, x, y, size=11):
    """Draw section title in bold uppercase."""
    c.setFont("Helvetica-Bold", size)
    c.drawString(x, y, str(title).upper())
    return y - (14 + MIN_LINE_GAP)

def draw_bullets(c, bullets, x, y, max_width, font="Helvetica", 
                 size=10, leading=12, bullet_indent=10):
    """Draw bullet points."""
    c.setFont(font, size)
    for b in (bullets or []):
        c.drawString(x, y, "•")
        y = draw_wrapped_text(
            c,
            b,
            x + bullet_indent,
            y,
            max_width - bullet_indent,
            font=font,
            size=size,
            leading=leading
        )
        y -= MIN_LINE_GAP
    return y

def draw_divider(c, x_start, x_end, y, thickness=0.7):
    """Draw horizontal divider line."""
    c.setLineWidth(thickness)
    c.line(x_start, y, x_end, y)
    return y - 8

def draw_page_border(c, page_w, page_h, margin=0.2*cm, thickness=0.5):
    """Draws a thin black border around the page."""
    c.setLineWidth(thickness)
    c.setStrokeColorRGB(0, 0, 0)
    c.rect(
        margin,
        margin,
        page_w - 1.85 * margin,
        page_h - 2 * margin,
        stroke=1,
        fill=0
    )