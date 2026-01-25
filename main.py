# app/main.py
import streamlit as st
import json
import base64
import re
from pathlib import Path
from datetime import datetime
from openai import OpenAI

from pdf_generator import create_resume_pdf, create_cover_letter_pdf
from utils import safe_filename, open_pdf_in_new_tab

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets.get("OPENAI_API_KEY", ""))

def main():
    """Main Streamlit application"""
    st.set_page_config(page_title="Resume Generator", page_icon="📄")
    
    st.title("📄 Resume Generator")
    st.caption("Edit JSON → Generate PDF → Download")
    
    # Test OpenAI key if available
    if client.api_key:
        if st.button("🔑 Test OpenAI Key"):
            try:
                r = client.responses.create(
                    model="gpt-4",
                    input="Say OK"
                )
                st.success("API key works ✅")
            except Exception as e:
                st.error(str(e))
    
    # Load JSON data
    JSON_PATH = Path("app/resume_data.json")
    if not JSON_PATH.exists():
        st.error("resume_data.json not found in app directory")
        st.stop()
    
    json_text = JSON_PATH.read_text(encoding="utf-8")
    
    # JSON editor
    edited_json = st.text_area(
        "Edit resume_data.json",
        value=json_text,
        height=450
    )
    
    # File naming
    default_name = f"Resume_{datetime.now().strftime('%Y%m%d_%H%M')}"
    out_name = st.text_input("Output filename (no .pdf needed)", value=default_name)
    
    output_pdf = f"{safe_filename(out_name)}.pdf"
    cover_pdf = f"{safe_filename(out_name)}_CoverLetter.pdf"
    
    # Generate buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("⚙️ Generate Resume PDF"):
            try:
                data = json.loads(edited_json)
                JSON_PATH.write_text(json.dumps(data, indent=2, encoding="utf-8"))
                
                create_resume_pdf(
                    json_path=str(JSON_PATH),
                    output_path=output_pdf
                )
                
                st.success("Resume PDF generated successfully!")
                pdf_bytes = Path(output_pdf).read_bytes()
                open_pdf_in_new_tab(pdf_bytes)
                
            except Exception as e:
                st.error(f"Error generating resume: {str(e)}")
    
    with col2:
        if st.button("📝 Generate Cover Letter PDF"):
            try:
                data = json.loads(edited_json)
                JSON_PATH.write_text(json.dumps(data, indent=2, encoding="utf-8"))
                
                create_cover_letter_pdf(
                    json_path=str(JSON_PATH),
                    output_path=cover_pdf
                )
                
                st.success("Cover Letter PDF generated!")
                pdf_bytes = Path(cover_pdf).read_bytes()
                open_pdf_in_new_tab(pdf_bytes)
                
            except Exception as e:
                st.error(f"Error generating cover letter: {str(e)}")
    
    # Download buttons
    if Path(output_pdf).exists():
        with open(output_pdf, "rb") as f:
            st.download_button(
                "⬇️ Download Resume PDF",
                data=f,
                file_name=output_pdf,
                mime="application/pdf"
            )
    
    if Path(cover_pdf).exists():
        with open(cover_pdf, "rb") as f:
            st.download_button(
                "⬇️ Download Cover Letter",
                data=f,
                file_name=cover_pdf,
                mime="application/pdf"
            )

if __name__ == "__main__":
    main()
