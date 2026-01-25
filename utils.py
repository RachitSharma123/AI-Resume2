# app/utils.py
import re
import base64
import streamlit as st

def safe_filename(name: str) -> str:
    """Convert string to safe filename."""
    name = name.strip()
    name = re.sub(r"[^A-Za-z0-9 _-]+", "", name)
    name = re.sub(r"\s+", "_", name)
    return name or "resume"

def open_pdf_in_new_tab(pdf_bytes: bytes):
    """Open PDF in new browser tab."""
    b64 = base64.b64encode(pdf_bytes).decode()
    pdf_data_url = f"data:application/pdf;base64,{b64}"
    st.markdown(
        f'<script>window.open("{pdf_data_url}", "_blank");</script>',
        unsafe_allow_html=True
    )