# main.py
import streamlit as st
import json
import base64
import re
import requests
from pathlib import Path
from datetime import datetime
import time
import threading

from pdf_generator import create_resume_pdf, create_cover_letter_pdf
from utils import safe_filename, open_pdf_in_new_tab
from ai_functions import (
    call_ai_tailor_resume,
    call_ai_generate_cover_letter,
    call_ai_ats_score,
    call_ai_improve_bullets,
    call_ai_extract_keywords,
    call_ai_rewrite_objective,
    call_ai_compress_resume,
    call_ai_improve_from_ats
)

JSON_PATH = Path("resume_data.json")

# Import Google Sheets functions at the top
GOOGLE_SHEETS_AVAILABLE = False
GOOGLE_SHEETS_ERROR = None

try:
    import gspread
    from google.oauth2.service_account import Credentials
    print("✅ gspread and google-auth packages found")
    
    from google_sheets_integration import (
        get_google_sheets_client,
        get_or_create_tracker,
        add_job_application,
        get_all_applications,
        update_application_status,
        get_statistics,
        search_applications
    )
    GOOGLE_SHEETS_AVAILABLE = True
    print("✅ google_sheets_integration.py imported successfully")
except ImportError as e:
    GOOGLE_SHEETS_ERROR = str(e)
    print(f"❌ Import error: {e}")
except Exception as e:
    GOOGLE_SHEETS_ERROR = str(e)
    print(f"❌ Other error: {e}")


def render_job_tracker():
    """Render the automated AI-powered job tracker interface."""
    if not GOOGLE_SHEETS_AVAILABLE:
        st.error("❌ Google Sheets integration not available!")
        if GOOGLE_SHEETS_ERROR:
            st.error(f"Error details: {GOOGLE_SHEETS_ERROR}")
        return
    
    st.header("🤖 AI-Powered Job Application Tracker")
    st.caption("Fill details → AI calculates ATS → Auto-saves to Google Sheets")
    
    # Initialize session state for sheet ID
    if "sheet_id" not in st.session_state:
        st.session_state["sheet_id"] = ""
    if "sheets_connected" not in st.session_state:
        st.session_state["sheets_connected"] = False
    
    # Auto-connect if sheet ID exists and not already connected
    if st.session_state.get("sheet_id") and not st.session_state.get("sheets_connected"):
        try:
            client = get_google_sheets_client()
            if client:
                spreadsheet, worksheet = get_or_create_tracker(client, st.session_state["sheet_id"])
                st.session_state["spreadsheet"] = spreadsheet
                st.session_state["worksheet"] = worksheet
                st.session_state["sheets_connected"] = True
        except:
            pass
    
    # Configuration section
    with st.expander("⚙️ Google Sheets Configuration", expanded=not st.session_state.get("sheets_connected")):
        sheet_id_input = st.text_input(
            "Google Sheet ID (paste from your manually created sheet)",
            value=st.session_state.get("sheet_id", ""),
            help="Create sheet manually at sheets.google.com, share with: job-tracker-service@job-thing-485602.iam.gserviceaccount.com"
        )
        
        if sheet_id_input != st.session_state.get("sheet_id", ""):
            st.session_state["sheet_id"] = sheet_id_input
        
        if st.button("🔗 Connect to Google Sheets"):
            try:
                client = get_google_sheets_client()
                if client:
                    spreadsheet, worksheet = get_or_create_tracker(client, st.session_state.get("sheet_id"))
                    st.session_state["spreadsheet"] = spreadsheet
                    st.session_state["worksheet"] = worksheet
                    st.session_state["sheet_id"] = spreadsheet.id
                    st.session_state["sheets_connected"] = True
                    st.success(f"✅ Connected to tracker!")
                    st.info(f"🔗 Sheet URL: {spreadsheet.url}")
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    # Check if connected
    if "worksheet" not in st.session_state or not st.session_state.get("sheets_connected"):
        st.warning("⚠️ Please connect to Google Sheets first (expand section above)")
        return
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🚀 Quick Add (AI-Powered)", "📋 View Applications", "📈 Statistics"])
    
    # ==================== TAB 1: AI-POWERED QUICK ADD ====================
    with tab1:
        st.subheader("🤖 AI-Powered Application Tracker")
        st.info("Fill details → AI calculates ATS score → Saves to sheet!")
        
        # Get current resume JSON
        try:
            raw_data = json.loads(st.session_state.get("edited_json", "{}"))
            if "resume_json" in raw_data:
                current_resume = raw_data["resume_json"]
                if isinstance(current_resume, dict) and "resume_json" in current_resume:
                    current_resume = current_resume["resume_json"]
            else:
                current_resume = raw_data
            
            has_resume = bool(current_resume.get("name"))
        except:
            has_resume = False
        
        if not has_resume:
            st.warning("⚠️ No resume loaded. Go to Resume Builder first to load your resume JSON.")
            return
        
        st.success(f"✅ Using resume for: {current_resume.get('name', 'N/A')}")
        
        # Simpler inputs
        col1, col2 = st.columns(2)
        
        with col1:
            company = st.text_input("🏢 Company Name *", placeholder="e.g., Google")
            position = st.text_input("💼 Position Title *", placeholder="e.g., IT Support Analyst")
        
        with col2:
            job_url = st.text_input("🔗 Job URL (optional)", placeholder="https://...")
            status = st.selectbox("📊 Status", [
                "Applied", "Screening", "Phone Interview",
                "Technical Interview", "Final Interview",
                "Offer Received", "Rejected", "Withdrawn"
            ])
        
        # Job Description from main page
        job_description = st.text_area(
            "📋 Job Description *",
            value=st.session_state.get("job_desc", ""),
            height=200,
            placeholder="Paste the full job description here...",
            help="Use the same JD from Resume Builder or paste new one"
        )
        
        # Update session state
        if job_description:
            st.session_state["job_desc"] = job_description
        
        # Big submit button
        if st.button("🚀 Calculate ATS & Save Application", type="primary", use_container_width=True):
            if not company or not position or not job_description:
                st.error("❌ Please fill: Company, Position, and Job Description!")
            else:
                with st.spinner("🤖 Calculating ATS score..."):
                    try:
                        # Calculate ATS Score
                        st.info("🎯 Analyzing resume against job description...")
                        ats_results = call_ai_ats_score(current_resume, job_description)
                        ats_score = f"{ats_results.get('ats_score', 0)}%"
                        
                        st.success(f"✅ ATS Score: {ats_score}")
                        
                        # Generate resume version name
                        resume_version = f"{safe_filename(company)}_{safe_filename(position)}_{datetime.now().strftime('%Y%m%d')}.pdf"
                        
                        # Save to Google Sheets
                        st.info("💾 Saving to Google Sheets...")
                        
                        application_data = {
                            "company": company,
                            "position": position,
                            "job_url": job_url or "N/A",
                            "status": status,
                            "ats_score": ats_score,
                            "contact_person": "",
                            "contact_email": "",
                            "follow_up_date": "",
                            "notes": f"Strengths: {', '.join(ats_results.get('strengths', [])[:2])}",
                            "resume_version": resume_version,
                            "has_cover_letter": "No"
                        }
                        
                        add_job_application(st.session_state["worksheet"], application_data)
                        
                        st.success("🎉 Application tracked successfully!")
                        st.balloons()
                        
                        # Show summary
                        st.divider()
                        st.subheader("📊 Application Summary")
                        
                        sum_col1, sum_col2 = st.columns(2)
                        with sum_col1:
                            st.metric("Company", company)
                            st.metric("Position", position)
                            st.metric("ATS Score", ats_score)
                        
                        with sum_col2:
                            st.metric("Status", status)
                            st.write("**Top Strengths:**")
                            for s in ats_results.get("strengths", [])[:3]:
                                st.write(f"✅ {s}")
                        
                        if ats_results.get("missing_keywords"):
                            st.warning(f"**Missing Keywords:** {', '.join(ats_results['missing_keywords'][:5])}")
                        
                        # Suggest tailoring if score is low
                        if ats_results.get("ats_score", 0) < 75:
                            st.warning(f"⚠️ ATS Score below 75%. Consider using 'AI: Tailor Resume to JD' button!")
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
    
    # ==================== TAB 2: VIEW APPLICATIONS ====================
    with tab2:
        st.subheader("Your Job Applications")
        
        try:
            col1, col2 = st.columns([3, 1])
            with col1:
                search_term = st.text_input("🔍 Search by company or position", placeholder="Type to search...")
            with col2:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.rerun()
            
            applications = get_all_applications(st.session_state["worksheet"])
            
            if search_term:
                applications = search_applications(applications, search_term)
            
            if not applications:
                st.info("📭 No applications yet. Add your first one in the 'Quick Add' tab!")
            else:
                st.write(f"**Total:** {len(applications)} applications")
                
                for idx, app in enumerate(reversed(applications)):
                    with st.expander(f"{app.get('Company', 'N/A')} - {app.get('Position', 'N/A')} ({app.get('Status', 'N/A')}) - ATS: {app.get('ATS Score', 'N/A')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Date Applied:**", app.get("Date Applied", "N/A"))
                            st.write("**Company:**", app.get("Company", "N/A"))
                            st.write("**Position:**", app.get("Position", "N/A"))
                            if app.get("Job URL"):
                                st.markdown(f"**Job URL:** [{app.get('Job URL')}]({app.get('Job URL')})")
                            st.write("**Status:**", app.get("Status", "N/A"))
                        
                        with col2:
                            st.write("**ATS Score:**", app.get("ATS Score", "N/A"))
                            st.write("**Contact:**", app.get("Contact Person", "N/A"))
                            if app.get("Contact Email"):
                                st.write("**Email:**", app.get("Contact Email"))
                            st.write("**Resume Version:**", app.get("Resume Version", "N/A"))
                        
                        if app.get("Notes"):
                            st.write("**Notes:**", app.get("Notes"))
                        
                        new_status = st.selectbox(
                            "Update Status:",
                            ["Applied", "Screening", "Phone Interview",
                             "Technical Interview", "Final Interview",
                             "Offer Received", "Rejected", "Withdrawn"],
                            index=0,
                            key=f"status_{idx}"
                        )
                        
                        if st.button("Update Status", key=f"update_{idx}"):
                            try:
                                row_num = len(applications) - idx + 1
                                update_application_status(st.session_state["worksheet"], row_num, new_status)
                                st.success("✅ Status updated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        
        except Exception as e:
            st.error(f"❌ Error loading applications: {str(e)}")
    
    # ==================== TAB 3: STATISTICS ====================
    with tab3:
        st.subheader("Application Statistics")
        
        try:
            applications = get_all_applications(st.session_state["worksheet"])
            stats = get_statistics(applications)
            
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            
            with metric_col1:
                st.metric("Total Applications", stats["total"])
            with metric_col2:
                st.metric("Waiting Response", stats["applied"])
            with metric_col3:
                st.metric("Interviewing", stats["interviewing"])
            with metric_col4:
                st.metric("Offers", stats["offered"], delta=stats["offered"] if stats["offered"] > 0 else None)
            
            st.progress(stats["response_rate"] / 100)
            st.write(f"**Response Rate:** {stats['response_rate']}%")
            
            if applications:
                st.subheader("Status Breakdown")
                status_counts = {}
                for app in applications:
                    status = app.get("Status", "Unknown")
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                for status, count in sorted(status_counts.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"**{status}:** {count}")
                
                # ATS Score distribution
                st.subheader("ATS Score Distribution")
                ats_scores = []
                for app in applications:
                    score_str = app.get("ATS Score", "0%")
                    try:
                        score = int(score_str.replace("%", ""))
                        ats_scores.append(score)
                    except:
                        pass
                
                if ats_scores:
                    avg_score = sum(ats_scores) / len(ats_scores)
                    st.metric("Average ATS Score", f"{avg_score:.1f}%")
                    
                    high_score = sum(1 for s in ats_scores if s >= 80)
                    med_score = sum(1 for s in ats_scores if 60 <= s < 80)
                    low_score = sum(1 for s in ats_scores if s < 60)
                    
                    st.write(f"🟢 High (80%+): {high_score}")
                    st.write(f"🟡 Medium (60-79%): {med_score}")
                    st.write(f"🔴 Low (<60%): {low_score}")
        
        except Exception as e:
            st.error(f"❌ Error loading statistics: {str(e)}")


def main():
    """Main Streamlit application with AI features"""
    st.set_page_config(page_title="AI Resume Generator", page_icon="📄", layout="wide")
    
    st.title("🤖 AI-Powered Resume Generator")
    
    # Load JSON data first
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
    if "output_name" not in st.session_state:
        st.session_state["output_name"] = f"Resume_{datetime.now().strftime('%Y%m%d_%H%M')}"
    if "output_pdf" not in st.session_state:
        st.session_state["output_pdf"] = f"{safe_filename(st.session_state['output_name'])}.pdf"
    if "cover_pdf" not in st.session_state:
        st.session_state["cover_pdf"] = f"{safe_filename(st.session_state['output_name'])}_CoverLetter.pdf"
    
    # Bottom navigation in collapsible
    with st.expander("🎯 Navigation", expanded=False):
        page = st.radio(
            "Choose Section:",
            ["📄 Resume Builder", "📊 Job Tracker"],
            index=0,
            horizontal=True
        )
    
    if page == "📊 Job Tracker":
        render_job_tracker()
        return
    
    # ==================== RESUME BUILDER ====================
    st.caption("Edit JSON → Use AI Features → Generate PDF")
    
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
            
            # Handle nested structure: {"resume_json": {...}}
            if "resume_json" in parsed_data:
                actual_data = parsed_data["resume_json"]
                # Handle double nesting
                if isinstance(actual_data, dict) and "resume_json" in actual_data:
                    actual_data = actual_data["resume_json"]
                st.info("ℹ️ Nested JSON structure detected (resume_json wrapper)", icon="ℹ️")
            else:
                actual_data = parsed_data
            
            # Show success but with auto-dismiss
            success_placeholder = st.empty()
            success_placeholder.success("✅ Valid JSON", icon="✅")
            
            # Auto-dismiss after 5 seconds
            def dismiss():
                time.sleep(5)
                success_placeholder.empty()
            threading.Thread(target=dismiss, daemon=True).start()
            
            # Show key fields for debugging
            with st.expander("🔍 Quick Preview"):
                st.write("**Name:**", actual_data.get("name", "❌ NOT FOUND"))
                st.write("**Contact:**", actual_data.get("contact", "❌ NOT FOUND"))
                career_obj = actual_data.get("career_objective", "❌ NOT FOUND")
                if career_obj != "❌ NOT FOUND":
                    st.write("**Career Objective:**", career_obj[:100] + "...")
                else:
                    st.write("**Career Objective:**", career_obj)
                st.write("**Experience entries:**", len(actual_data.get("experience", [])))
                st.write("**Education entries:**", len(actual_data.get("education", [])))
                st.write("**Skills entries:**", len(actual_data.get("skills_snapshot", [])))
        except json.JSONDecodeError as e:
            st.error(f"❌ Invalid JSON: {str(e)}", icon="❌")
        
        st.divider()
        
        # File naming
        out_name = st.text_input(
            "📁 Output filename (no .pdf needed)",
            value=st.session_state["output_name"]
        )
        if out_name != st.session_state["output_name"]:
            st.session_state["output_name"] = out_name
        output_pdf = f"{safe_filename(out_name)}.pdf"
        cover_pdf = f"{safe_filename(out_name)}_CoverLetter.pdf"
        st.session_state["output_pdf"] = output_pdf
        st.session_state["cover_pdf"] = cover_pdf
    
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
    with st.expander("🤖 AI Features", expanded=True):
        st.subheader("AI Tools")
        
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
        
        # Auto-improve button
        if st.button("🚀 AI: Auto-Fix Issues from ATS Analysis", type="primary", use_container_width=True):
            if not st.session_state.get("job_desc", "").strip():
                st.warning("⚠️ Need job description to improve resume!")
            else:
                with st.spinner("🔧 Improving resume based on ATS analysis..."):
                    try:
                        raw_data = json.loads(st.session_state["edited_json"])
                        if "resume_json" in raw_data:
                            base = raw_data["resume_json"]
                        else:
                            base = raw_data
                        
                        improved = call_ai_improve_from_ats(
                            base, 
                            st.session_state["ats_results"],
                            st.session_state["job_desc"]
                        )
                        
                        if "resume_json" in raw_data:
                            raw_data["resume_json"] = improved
                        else:
                            raw_data = improved
                        
                        st.session_state["edited_json"] = json.dumps(raw_data, indent=2, ensure_ascii=False)
                        JSON_PATH.write_text(st.session_state["edited_json"], encoding="utf-8")
                        
                        st.success("✅ Resume improved based on ATS analysis! Run ATS analysis again to see new score.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
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

    # ============== DEBUG SECTION ==============
    with st.expander("🐛 Debug: Test Data Loading"):
        col_test1, col_test2 = st.columns(2)

        with col_test1:
            if st.button("🧪 Test JSON Parsing"):
                try:
                    raw_data = json.loads(st.session_state["edited_json"])

                    # Handle nested structure
                    if "resume_json" in raw_data:
                        data = raw_data["resume_json"]
                        st.info("Using nested 'resume_json' structure")
                    else:
                        data = raw_data
                        st.info("Using direct structure")

                    st.success("✅ JSON parsed successfully!")

                    # Show all top-level keys
                    st.write("**Top-level keys found:**", list(data.keys()))

                    # Show sample data
                    st.write("**Name:**", data.get("name", "NOT FOUND"))
                    st.write("**Contact:**", data.get("contact", "NOT FOUND"))
                    st.write("**Career Objective (first 100 chars):**", str(data.get("career_objective", "NOT FOUND"))[:100])
                    st.write("**Number of Experience entries:**", len(data.get("experience", [])))
                    st.write("**Number of Education entries:**", len(data.get("education", [])))
                    st.write("**Number of Skills entries:**", len(data.get("skills_snapshot", [])))

                    # Show first experience entry if exists
                    if data.get("experience"):
                        st.write("**First experience entry:**")
                        st.json(data["experience"][0])

                except Exception as e:
                    st.error(f"Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        with col_test2:
            if st.button("🧪 Test Basic PDF Creation"):
                try:
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import A4

                    test_pdf = "test_basic.pdf"
                    c = canvas.Canvas(test_pdf, pagesize=A4)
                    c.setFont("Helvetica-Bold", 24)
                    c.drawString(100, 700, "TEST PDF - If you see this, PDF works!")
                    c.drawString(100, 650, "Your Name Here")
                    c.save()

                    st.success("✅ Basic PDF created!")
                    with open(test_pdf, "rb") as f:
                        st.download_button("Download Test PDF", f, test_pdf, mime="application/pdf")

                except Exception as e:
                    st.error(f"Error: {e}")
                    import traceback
                    st.code(traceback.format_exc())


st.divider()
    
    # ============== PDF GENERATION SECTION ==============
    
with st.expander("🔞 Stuff Generator", expanded=True):
      st.header("📄 Generate PDFs")
      pdf_col1, pdf_col2 = st.columns(2)
    
with pdf_col1:
        if st.button("⚙️ Generate Resume PDF", use_container_width=True):
            with st.spinner("📄 Generating resume PDF..."):
                try:
                    raw_data = json.loads(st.session_state["edited_json"])
                    
                    # Handle nested structure
                    if "resume_json" in raw_data:
                        data = raw_data["resume_json"]
                        if isinstance(data, dict) and "resume_json" in data:
                            data = data["resume_json"]
                    else:
                        data = raw_data
                    
                    st.info(f"📊 Using data with {len(data.get('experience', []))} experience entries, {len(data.get('education', []))} education entries")
                    
                    JSON_PATH.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
                    
                    output_pdf = "Rachit_Sharma_Resume_Generated.pdf"
                    cover_pdf = "Cover_Letter.pdf"
                    create_resume_pdf(json_path=str(JSON_PATH), output_path=output_pdf)
                    
                    st.success("✅ Resume PDF generated successfully!")
                    
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
                    import traceback
                    st.code(traceback.format_exc())
    
with pdf_col2:
        if st.button("📝 Generate Cover Letter PDF", use_container_width=True):
            with st.spinner("📝 Generating cover letter PDF..."):
                try:
                    raw_data = json.loads(st.session_state["edited_json"])
                    
                    if "resume_json" in raw_data:
                        data = raw_data["resume_json"]
                        if isinstance(data, dict) and "resume_json" in data:
                            data = data["resume_json"]
                    else:
                        data = raw_data
                    
                    if "cover_letter" not in data:
                        st.warning("⚠️ No cover letter found in JSON. Use 'AI: Generate Cover Letter' first!")
                        st.info("💡 Click the '✍️ AI: Generate Cover Letter' button above to create a cover letter first.")
                    else:
                        JSON_PATH.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        
                        create_cover_letter_pdf(json_path=str(JSON_PATH), output_path=cover_pdf)
                        
                        st.success("✅ Cover letter PDF generated!")
                        
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
                    import traceback
                    st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
