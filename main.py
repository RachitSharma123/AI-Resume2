# main.py
import streamlit as st
import json
import base64
import re
from pathlib import Path
from datetime import datetime

from pdf_generator import create_resume_pdf, create_cover_letter_pdf
from utils import safe_filename, open_pdf_in_new_tab
from ai_functions import (
    call_ai_tailor_resume,
    call_ai_generate_cover_letter,
    call_ai_ats_score,
    call_ai_improve_bullets,
    call_ai_extract_keywords,
    call_ai_rewrite_objective,
    call_ai_compress_resume
)

def main():
    """Main Streamlit application with AI features"""
    st.set_page_config(page_title="AI Resume Generator", page_icon="📄", layout="wide")
    
    st.title("🤖 AI-Powered Resume Generator")
    st.caption("Edit JSON → Use AI Features → Generate PDF → Download")
    
    # Load JSON data
    JSON_PATH = Path("resume_data.json")
    if not JSON_PATH.exists():
        st.error("❌ resume_data.json not found in root directory")
        st.stop()
    
    json_text = JSON_PATH.read_text(encoding="utf-8")
    
    # Session state initialization
    if "edited_json" not in st.session_state:
        st.session_state["edited_json"] = json_text
    if "job_desc" not in st.session_state:
        st.session_state["job_desc"] = ""
    if "ats_results" not in st.session_state:
        st.session_state["ats_results"] = None
    if "extracted_keywords" not in st.session_state:
        st.session_state["extracted_keywords"] = None
    
    # Layout: Two columns
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📝 Resume JSON Editor")
        # Use a unique key that changes when content updates
        editor_key = f"json_editor_{hash(st.session_state['edited_json'])}"
        edited_json = st.text_area(
            "Edit your resume data",
            value=st.session_state["edited_json"],
            height=400,
            key=editor_key
        )
        # Only update if user manually edited (not from AI)
        if edited_json != st.session_state["edited_json"]:
            st.session_state["edited_json"] = edited_json
        
        # Debug info / Character counter
        char_count = len(st.session_state["edited_json"])
        word_count = len(st.session_state["edited_json"].split())
        line_count = st.session_state["edited_json"].count('\n') + 1
        
        debug_col1, debug_col2, debug_col3 = st.columns(3)
        with debug_col1:
            st.caption(f"📊 Characters: **{char_count:,}**")
        with debug_col2:
            st.caption(f"📝 Words: **{word_count:,}**")
        with debug_col3:
            st.caption(f"📄 Lines: **{line_count}**")
        
        # JSON validation indicator
        try:
            parsed_data = json.loads(st.session_state["edited_json"])
            st.success("✅ Valid JSON", icon="✅")
            
            # Show key fields for debugging
            with st.expander("🔍 Quick Preview"):
                st.write("**Name:**", parsed_data.get("name", "❌ NOT FOUND"))
                st.write("**Contact:**", parsed_data.get("contact", "❌ NOT FOUND"))
                st.write("**Career Objective:**", parsed_data.get("career_objective", "❌ NOT FOUND")[:100] + "...")
                st.write("**Experience entries:**", len(parsed_data.get("experience", [])))
                st.write("**Education entries:**", len(parsed_data.get("education", [])))
                st.write("**Skills entries:**", len(parsed_data.get("skills_snapshot", [])))
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {str(e)}", icon="❌")
        
        st.divider()
        
        # File naming
        default_name = f"Resume_{datetime.now().strftime('%Y%m%d_%H%M')}"
        out_name = st.text_input("📁 Output filename (no .pdf needed)", value=default_name)
        output_pdf = f"{safe_filename(out_name)}.pdf"
        cover_pdf = f"{safe_filename(out_name)}_CoverLetter.pdf"
    
    with col_right:
        st.subheader("🎯 Job Description (for AI)")
        job_desc = st.text_area(
            "Paste the job description here",
            height=400,
            key="job_desc_input",
            placeholder="Paste the full job description here for AI tailoring..."
        )
        st.session_state["job_desc"] = job_desc
        
        if job_desc.strip():
            st.success(f"✅ Job description loaded ({len(job_desc.split())} words)")
    
    st.divider()
    
    # ============== AI FEATURES SECTION ==============
    st.header("🤖 AI Features")
    
    # Row 1: Main AI Actions
    ai_col1, ai_col2, ai_col3 = st.columns(3)
    
    with ai_col1:
        if st.button("✨ AI: Tailor Resume to JD", use_container_width=True):
            if not st.session_state.get("job_desc", "").strip():
                st.warning("⚠️ Please paste a job description first!")
            else:
                with st.spinner("🧠 Tailoring resume to job description..."):
                    try:
                        base = json.loads(st.session_state["edited_json"])
                        tailored = call_ai_tailor_resume(base, st.session_state["job_desc"])
                        
                        st.session_state["edited_json"] = json.dumps(tailored, indent=2, ensure_ascii=False)
                        JSON_PATH.write_text(st.session_state["edited_json"], encoding="utf-8")
                        
                        st.success("✅ Resume tailored successfully! Check the editor.")
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON in editor. Please fix syntax errors.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with ai_col2:
        if st.button("✍️ AI: Generate Cover Letter", use_container_width=True):
            if not st.session_state.get("job_desc", "").strip():
                st.warning("⚠️ Please paste a job description first!")
            else:
                with st.spinner("✍️ Generating cover letter..."):
                    try:
                        data = json.loads(st.session_state["edited_json"])
                        cl = call_ai_generate_cover_letter(data, st.session_state["job_desc"])
                        
                        # Fallbacks
                        if not cl.get("phone_number"):
                            contact = data.get("contact", "")
                            m = re.search(r"(\+?\d[\d\s]{7,}\d)", contact)
                            if m:
                                cl["phone_number"] = m.group(1).strip()
                        
                        if not cl.get("signature_name"):
                            cl["signature_name"] = data.get("name", "")
                        
                        data["cover_letter"] = cl
                        st.session_state["edited_json"] = json.dumps(data, indent=2, ensure_ascii=False)
                        JSON_PATH.write_text(st.session_state["edited_json"], encoding="utf-8")
                        
                        st.success("✅ Cover letter generated! Check JSON editor.")
                        st.rerun()
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON in editor.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with ai_col3:
        if st.button("📏 AI: Compress to 1 Page", use_container_width=True):
            with st.spinner("🗜️ Compressing resume intelligently..."):
                try:
                    data = json.loads(st.session_state["edited_json"])
                    compressed = call_ai_compress_resume(data)
                    
                    st.session_state["edited_json"] = json.dumps(compressed, indent=2, ensure_ascii=False)
                    JSON_PATH.write_text(st.session_state["edited_json"], encoding="utf-8")
                    
                    st.success("✅ Resume compressed! Content reduced while maintaining impact.")
                    st.rerun()
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in editor.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    # Row 2: Analysis Tools
    st.subheader("🔍 Analysis & Improvement Tools")
    analysis_col1, analysis_col2, analysis_col3 = st.columns(3)
    
    with analysis_col1:
        if st.button("🎯 AI: ATS Score Analysis", use_container_width=True):
            if not st.session_state.get("job_desc", "").strip():
                st.warning("⚠️ Please paste a job description first!")
            else:
                with st.spinner("📊 Analyzing resume against job description..."):
                    try:
                        data = json.loads(st.session_state["edited_json"])
                        results = call_ai_ats_score(data, st.session_state["job_desc"])
                        st.session_state["ats_results"] = results
                        st.success("✅ ATS analysis complete! See results below.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with analysis_col2:
        if st.button("🔍 AI: Extract JD Keywords", use_container_width=True):
            if not st.session_state.get("job_desc", "").strip():
                st.warning("⚠️ Please paste a job description first!")
            else:
                with st.spinner("🔎 Extracting keywords..."):
                    try:
                        keywords = call_ai_extract_keywords(st.session_state["job_desc"])
                        st.session_state["extracted_keywords"] = keywords
                        st.success("✅ Keywords extracted! See results below.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    with analysis_col3:
        if st.button("✏️ AI: Rewrite Objective", use_container_width=True):
            if not st.session_state.get("job_desc", "").strip():
                st.warning("⚠️ Please paste a job description first!")
            else:
                with st.spinner("✏️ Rewriting career objective..."):
                    try:
                        data = json.loads(st.session_state["edited_json"])
                        current_obj = data.get("career_objective", "")
                        new_obj = call_ai_rewrite_objective(current_obj, st.session_state["job_desc"])
                        
                        data["career_objective"] = new_obj
                        st.session_state["edited_json"] = json.dumps(data, indent=2, ensure_ascii=False)
                        JSON_PATH.write_text(st.session_state["edited_json"], encoding="utf-8")
                        
                        st.success("✅ Career objective rewritten! Check editor.")
                        st.info(f"**New Objective:** {new_obj}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # Display ATS Results
    if st.session_state.get("ats_results"):
        st.divider()
        st.subheader("📊 ATS Analysis Results")
        results = st.session_state["ats_results"]
        
        # Score metrics
        score_col1, score_col2, score_col3, score_col4 = st.columns(4)
        with score_col1:
            st.metric("Overall ATS Score", f"{results.get('ats_score', 0)}%")
        with score_col2:
            st.metric("Keyword Match", f"{results.get('keyword_match', 0)}%")
        with score_col3:
            st.metric("Experience Match", f"{results.get('experience_match', 0)}%")
        with score_col4:
            st.metric("Skills Match", f"{results.get('skills_match', 0)}%")
        
        # Strengths and Weaknesses
        strength_col, weakness_col = st.columns(2)
        
        with strength_col:
            st.success("**✅ Strengths:**")
            for s in results.get("strengths", []):
                st.write(f"• {s}")
        
        with weakness_col:
            st.warning("**⚠️ Areas to Improve:**")
            for w in results.get("weaknesses", []):
                st.write(f"• {w}")
        
        # Missing keywords
        if results.get("missing_keywords"):
            st.error("**🔴 Missing Keywords:**")
            st.write(", ".join(results["missing_keywords"]))
        
        # Suggestions
        st.info("**💡 Suggestions:**")
        for sug in results.get("suggestions", []):
            st.write(f"• {sug}")
    
    # Display Extracted Keywords
    if st.session_state.get("extracted_keywords"):
        st.divider()
        st.subheader("🔑 Extracted Keywords from Job Description")
        kw = st.session_state["extracted_keywords"]
        
        kw_col1, kw_col2 = st.columns(2)
        
        with kw_col1:
            st.write("**Role:**", kw.get("role_title", "N/A"))
            st.write("**Experience Level:**", kw.get("experience_level", "N/A"))
            
            st.write("**Required Skills:**")
            for skill in kw.get("required_skills", []):
                st.write(f"• {skill}")
        
        with kw_col2:
            st.write("**Key Technologies:**")
            for tech in kw.get("key_technologies", []):
                st.write(f"• {tech}")
            
            st.write("**Preferred Skills:**")
            for skill in kw.get("preferred_skills", []):
                st.write(f"• {skill}")
    
    st.divider()
    
    # ============== PDF GENERATION SECTION ==============
    st.header("📄 Generate PDFs")
    
    pdf_col1, pdf_col2 = st.columns(2)
    
    with pdf_col1:
        if st.button("⚙️ Generate Resume PDF", use_container_width=True):
            with st.spinner("📄 Generating resume PDF..."):
                try:
                    data = json.loads(st.session_state["edited_json"])
                    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    
                    create_resume_pdf(json_path=str(JSON_PATH), output_path=output_pdf)
                    
                    st.success("✅ Resume PDF generated successfully!")
                    
                    # Show download button
                    if Path(output_pdf).exists():
                        with open(output_pdf, "rb") as f:
                            st.download_button(
                                "⬇️ Download Resume PDF",
                                data=f,
                                file_name=output_pdf,
                                mime="application/pdf",
                                use_container_width=True
                            )
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON. Please fix syntax errors in editor.")
                except Exception as e:
                    st.error(f"❌ Error generating PDF: {str(e)}")
    
    with pdf_col2:
        if st.button("📝 Generate Cover Letter PDF", use_container_width=True):
            with st.spinner("📝 Generating cover letter PDF..."):
                try:
                    data = json.loads(st.session_state["edited_json"])
                    
                    if "cover_letter" not in data:
                        st.warning("⚠️ No cover letter found in JSON. Use 'AI: Generate Cover Letter' first!")
                    else:
                        JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                        
                        create_cover_letter_pdf(json_path=str(JSON_PATH), output_path=cover_pdf)
                        
                        st.success("✅ Cover letter PDF generated!")
                        
                        # Show download button
                        if Path(cover_pdf).exists():
                            with open(cover_pdf, "rb") as f:
                                st.download_button(
                                    "⬇️ Download Cover Letter PDF",
                                    data=f,
                                    file_name=cover_pdf,
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                except json.JSONDecodeError:
                    st.error("❌ Invalid JSON in editor.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    main()
