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
import os

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
    call_ai_improve_from_ats,
    get_provider_choices,
    list_models,
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


def require_login() -> bool:
    """Require a password before granting access to the app."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    app_password = None
    try:
        app_password = st.secrets.get("APP_PASSWORD")
    except Exception:
        app_password = None
    if not app_password:
        app_password = os.getenv("APP_PASSWORD")

    if not app_password:
        st.error("❌ APP_PASSWORD is not configured. Set it in Streamlit secrets or environment.")
        st.stop()

    if st.session_state["authenticated"]:
        with st.sidebar:
            if st.button("🚪 Log out"):
                st.session_state["authenticated"] = False
                st.rerun()
        return True

    st.title("🔐 Login")
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")
        if submitted:
            if password == app_password:
                st.session_state["authenticated"] = True
                st.success("✅ Logged in successfully.")
                st.rerun()
            else:
                st.error("❌ Incorrect password.")

    return False


def _init_ai_runtime_state() -> None:
    """Initialize session state used for runtime AI provider configuration."""
    if "ai_runtime_config" not in st.session_state:
        st.session_state["ai_runtime_config"] = {
            "provider": "openai",
            "api_key": "",
            "base_url": "",
            "model": "",
        }
    if "ai_models_cache" not in st.session_state:
        st.session_state["ai_models_cache"] = []
    if "ai_models_error" not in st.session_state:
        st.session_state["ai_models_error"] = ""


def render_ai_provider_settings() -> None:
    """Render runtime AI provider settings in a glass-style popover."""
    _init_ai_runtime_state()
    provider_choices = get_provider_choices()
    runtime_cfg = st.session_state["ai_runtime_config"]

    selected_provider = runtime_cfg.get("provider", "openai")
    if selected_provider not in provider_choices:
        selected_provider = "custom"

    st.markdown(
        """
        <style>
        div[data-testid="stPopover"] button[kind="secondary"] {
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.25);
            background: linear-gradient(135deg, rgba(255,255,255,0.22), rgba(255,255,255,0.08));
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            box-shadow: 0 12px 30px rgba(31, 38, 135, 0.18);
        }
        div[data-testid="stPopoverContent"] {
            border-radius: 24px;
            border: 1px solid rgba(255,255,255,0.18);
            background: linear-gradient(135deg, rgba(255,255,255,0.20), rgba(255,255,255,0.06));
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
        }
        .glass-card {
            border-radius: 20px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.75rem;
            border: 1px solid rgba(255,255,255,0.16);
            background: linear-gradient(135deg, rgba(255,255,255,0.20), rgba(255,255,255,0.05));
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.popover("🫧 AI Provider Settings"):
        st.markdown(
            """
            <div class="glass-card">
                <strong>Switch providers at runtime.</strong><br/>
                Pick a provider, paste an API key, optionally override the base URL, then fetch models.
            </div>
            """,
            unsafe_allow_html=True,
        )

        provider_keys = list(provider_choices.keys())
        selected_provider = st.selectbox(
            "Provider",
            provider_keys,
            index=provider_keys.index(selected_provider),
            format_func=lambda key: provider_choices.get(key, key.title()),
        )

        api_key = st.text_input(
            "API Key",
            value=runtime_cfg.get("api_key", ""),
            type="password",
            placeholder="Enter provider API key",
        )
        base_url = st.text_input(
            "Base URL Override",
            value=runtime_cfg.get("base_url", ""),
            placeholder="Leave blank to use provider default",
        )
        model_override = st.text_input(
            "Model Override",
            value=runtime_cfg.get("model", ""),
            placeholder="Leave blank to use env/default model",
        )

        st.session_state["ai_runtime_config"] = {
            "provider": selected_provider,
            "api_key": api_key,
            "base_url": base_url,
            "model": model_override,
        }

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("Fetch Models", use_container_width=True):
                try:
                    models = list_models(
                        provider=selected_provider,
                        api_key=api_key or None,
                        base_url=base_url or None,
                    )
                    st.session_state["ai_models_cache"] = models
                    st.session_state["ai_models_error"] = ""
                    if not model_override and models:
                        st.session_state["ai_runtime_config"]["model"] = models[0]
                    st.success(f"Fetched {len(models)} model(s).")
                except Exception as e:
                    st.session_state["ai_models_cache"] = []
                    st.session_state["ai_models_error"] = str(e)
                    st.error(f"Unable to fetch models: {e}")

        with action_col2:
            if st.button("Clear Runtime Settings", use_container_width=True):
                st.session_state["ai_runtime_config"] = {
                    "provider": "openai",
                    "api_key": "",
                    "base_url": "",
                    "model": "",
                }
                st.session_state["ai_models_cache"] = []
                st.session_state["ai_models_error"] = ""
                st.success("Runtime AI settings cleared. Env/secrets will be used.")

        models = st.session_state.get("ai_models_cache", [])
        if models:
            current_model = st.session_state["ai_runtime_config"].get("model") or models[0]
            if current_model not in models:
                models = [current_model, *models]
            chosen_model = st.selectbox(
                "Available Models",
                models,
                index=models.index(current_model),
                help="Use Fetch Models to refresh this list from the selected provider.",
            )
            st.session_state["ai_runtime_config"]["model"] = chosen_model
            st.caption(f"Selected model: `{chosen_model}`")
        elif st.session_state.get("ai_models_error"):
            st.caption("Tip: check the provider, base URL, and API key, then try Fetch Models again.")

        active_model = st.session_state["ai_runtime_config"].get("model") or "env/default"
        st.info(
            f"Active provider: {provider_choices.get(selected_provider, selected_provider)} | "
            f"Active model: {active_model}"
        )


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

    if not require_login():
        return

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
        render_ai_provider_settings()
        
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
                            raw_data = json.loads(st.session_state["edited_json"])

                            # Handle nested structure consistently
                            if "resume_json" in raw_data:
                                data = raw_data["resume_json"]
                                if isinstance(data, dict) and "resume_json" in data:
                                    data = data["resume_json"]
                            else:
                                data = raw_data

                            cl = call_ai_generate_cover_letter(data, st.session_state["job_desc"])

                            # Defensive normalization for malformed/nested responses.
                            if isinstance(cl, dict) and isinstance(cl.get("cover_letter"), dict):
                                cl = cl["cover_letter"]

                            body_points = cl.get("body_points", []) if isinstance(cl, dict) else []
                            if isinstance(body_points, str):
                                body_points = [body_points]
                            if not isinstance(body_points, list):
                                body_points = []
                            cl["body_points"] = [str(p).strip() for p in body_points if str(p).strip()]

                            if not cl["body_points"]:
                                raise ValueError("Generated cover letter is empty. Please regenerate with a clearer job description.")
                            
                            # Fallbacks
                            if not cl.get("phone_number"):
                                contact = data.get("contact", "")
                                m = re.search(r"(\+?\d[\d\s]{7,}\d)", contact)
                                if m:
                                    cl["phone_number"] = m.group(1).strip()
                            
                            if not cl.get("signature_name"):
                                cl["signature_name"] = data.get("name", "")
                            
                            data["cover_letter"] = cl

                            if "resume_json" in raw_data:
                                raw_data["resume_json"] = data
                            else:
                                raw_data = data

                            st.session_state["edited_json"] = json.dumps(raw_data, indent=2, ensure_ascii=False)
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
        
        # ============== CONSOLIDATED CUSTOMIZATION MENU ==============
        
    with st.expander("⚙️ Resume & Cover Letter Settings", expanded=False):
        st.header("🎛️ Customize Your Documents")
        st.caption("All customization options in one place")
        
        # Tab-based organization within the expander
        settings_tab1, settings_tab2, settings_tab3 = st.tabs([
            "📋 Resume Sections", 
            "✉️ Cover Letter", 
            "🎨 PDF Styling"
        ])
        
        # ========== TAB 1: RESUME SECTIONS ==========
        with settings_tab1:
            try:
                raw_data = json.loads(st.session_state.get("edited_json", "{}"))
                if "resume_json" in raw_data:
                    data = raw_data["resume_json"]
                    if isinstance(data, dict) and "resume_json" in data:
                        data = data["resume_json"]
                else:
                    data = raw_data
                
                st.success(f"✅ Editing resume for: {data.get('name', 'N/A')}")
                
                # Section toggles
                st.subheader("📋 Section Visibility")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    include_objective = st.checkbox("Career Objective", value=bool(data.get("career_objective")), key="inc_obj")
                    include_skills = st.checkbox("Skills Snapshot", value=bool(data.get("skills_snapshot")), key="inc_skills")
                
                with col2:
                    include_experience = st.checkbox("Experience", value=bool(data.get("experience")), key="inc_exp")
                    include_education = st.checkbox("Education", value=bool(data.get("education")), key="inc_edu")
                
                with col3:
                    include_certs = st.checkbox("Certifications", value=bool(data.get("certifications")), key="inc_cert")
                    include_refs = st.checkbox("References", value=bool(data.get("references")), key="inc_ref")
                
                st.divider()
                
                # Career Objective customization
                if include_objective:
                    st.subheader("🎯 Career Objective")
                    career_obj = st.text_area(
                        "Career Objective",
                        value=data.get("career_objective", ""),
                        height=120,
                        help="2-3 sentences that summarize your professional goals and value proposition"
                    )
                else:
                    career_obj = ""
                
                # Save changes button for resume
                if st.button("💾 Save Resume Section Changes", use_container_width=True, type="secondary", key="save_resume"):
                    # Update data with customizations
                    if not include_objective:
                        data.pop("career_objective", None)
                    else:
                        data["career_objective"] = career_obj
                    
                    if not include_skills:
                        data.pop("skills_snapshot", None)
                    
                    if not include_experience:
                        data.pop("experience", None)
                    
                    if not include_education:
                        data.pop("education", None)
                    
                    if not include_certs:
                        data.pop("certifications", None)
                    
                    if not include_refs:
                        data.pop("references", None)
                    
                    # Update session state
                    if "resume_json" in raw_data:
                        raw_data["resume_json"] = data
                    else:
                        raw_data = data
                    
                    st.session_state["edited_json"] = json.dumps(raw_data, indent=2, ensure_ascii=False)
                    st.success("✅ Resume sections updated!")
                    st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error loading resume data: {str(e)}")
        
        # ========== TAB 2: COVER LETTER ==========
        with settings_tab2:
            try:
                raw_data = json.loads(st.session_state.get("edited_json", "{}"))
                if "resume_json" in raw_data:
                    data = raw_data["resume_json"]
                    if isinstance(data, dict) and "resume_json" in data:
                        data = data["resume_json"]
                else:
                    data = raw_data
                
                cover_letter = data.get("cover_letter", {})
                
                if not cover_letter:
                    st.info("💡 No cover letter found. Generate one first using the '✍️ AI: Generate Cover Letter' button.")
                else:
                    st.success(f"✅ Cover letter loaded for {data.get('name', 'N/A')}")
                    
                    # Section toggles
                    st.subheader("📋 Section Settings")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        include_date = st.checkbox("Include Date", value=True, key="cl_date")
                        include_recipient = st.checkbox("Include Recipient Info", value=True, key="cl_recipient")
                    with col2:
                        include_subject = st.checkbox("Include Subject Line", value=True, key="cl_subject")
                        include_contact = st.checkbox("Include Contact Info", value=True, key="cl_contact")
                    with col3:
                        include_company_addr = st.checkbox("Include Company Address", value=bool(cover_letter.get("company_address")), key="cl_addr")
                    
                    st.divider()
                    
                    # Header customization
                    st.subheader("📋 Header Information")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        date_val = st.text_input("Date", value=cover_letter.get("date", "AUTO"), help="Use AUTO for today's date", key="cl_date_val")
                        recipient = st.text_input("Recipient", value=cover_letter.get("recipient", "Hiring Manager"), key="cl_recip")
                        company = st.text_input("Company", value=cover_letter.get("company", ""), key="cl_comp")
                    
                    with col2:
                        role_title = st.text_input("Role Title", value=cover_letter.get("role_title", ""), key="cl_role")
                        company_address = st.text_area("Company Address", value=cover_letter.get("company_address", ""), height=80, key="cl_addr_val")
                    
                    subject = st.text_input("Subject Line", value=cover_letter.get("subject", ""), key="cl_subj")
                    opening = st.text_input("Opening Greeting", value=cover_letter.get("opening", "Dear Hiring Manager,"), key="cl_open")
                    
                    st.divider()
                    
                    # Body paragraphs
                    st.subheader("📝 Letter Body")
                    body_points = cover_letter.get("body_points", [])
                    
                    if not body_points:
                        body_points = ["", "", "", ""]
                    
                    updated_body_points = []
                    
                    for i, paragraph in enumerate(body_points):
                        with st.expander(f"Paragraph {i+1}", expanded=False):
                            para_text = st.text_area(
                                f"Content",
                                value=paragraph,
                                height=150,
                                key=f"cl_para_{i}",
                                help="Write naturally, like you're having a conversation"
                            )
                            updated_body_points.append(para_text)
                            
                            # Word count for this paragraph
                            word_count = len(re.findall(r'\b[\w\']+\b', para_text))
                            st.caption(f"📊 Words: {word_count}")
                    
                    # Add paragraph button
                    if st.button("➕ Add Another Paragraph", key="cl_add_para"):
                        updated_body_points.append("")
                    
                    # Calculate total word count
                    total_words = sum(len(re.findall(r'\b[\w\']+\b', p)) for p in updated_body_points)
                    st.metric("Total Body Word Count", total_words, help="Aim for 500-600 words")
                    
                    if total_words < 450:
                        st.warning("⚠️ Cover letter might be too short. Aim for 500-600 words.")
                    elif total_words > 650:
                        st.warning("⚠️ Cover letter might be too long. Try to keep it under 600 words.")
                    else:
                        st.success("✅ Word count looks good!")
                    
                    st.divider()
                    
                    # Footer customization
                    st.subheader("📋 Signature")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        closing = st.text_input("Closing", value=cover_letter.get("closing", "Best regards,"), key="cl_close")
                        signature_name = st.text_input("Signature Name", value=cover_letter.get("signature_name", data.get("name", "")), key="cl_sig")
                    
                    with col2:
                        phone_number = st.text_input("Phone Number", value=cover_letter.get("phone_number", ""), key="cl_phone")
                        email = st.text_input("Email", value=cover_letter.get("email", ""), key="cl_email")
                    
                    st.divider()
                    
                    # Save changes button
                    if st.button("💾 Save Cover Letter Changes", use_container_width=True, type="secondary", key="save_cl"):
                        # Update cover letter in data
                        updated_cover_letter = {
                            "date": date_val if include_date else "",
                            "recipient": recipient if include_recipient else "",
                            "company": company,
                            "role_title": role_title,
                            "company_address": company_address if include_company_addr else "",
                            "subject": subject if include_subject else "",
                            "opening": opening,
                            "body_points": [p for p in updated_body_points if p.strip()],
                            "closing": closing,
                            "signature_name": signature_name if include_contact else "",
                            "phone_number": phone_number if include_contact else "",
                            "email": email if include_contact else ""
                        }
                        
                        data["cover_letter"] = updated_cover_letter
                        
                        # Update session state
                        if "resume_json" in raw_data:
                            raw_data["resume_json"] = data
                        else:
                            raw_data = data
                        
                        st.session_state["edited_json"] = json.dumps(raw_data, indent=2, ensure_ascii=False)
                        st.success("✅ Cover letter updated!")
                        st.rerun()
            
            except Exception as e:
                st.error(f"❌ Error loading cover letter: {str(e)}")
        
        # ========== TAB 3: PDF STYLING ==========
        with settings_tab3:
            st.subheader("🎨 PDF Appearance")
            st.caption("Customize fonts and styling for your PDFs")
            
            font_col1, font_col2 = st.columns(2)
            
            with font_col1:
                font_scale = st.slider(
                    "📏 Font Size Scale",
                    min_value=0.5,
                    max_value=1.5,
                    value=st.session_state.get("font_scale", 1.0),
                    step=0.05,
                    help="Adjust the overall size of all fonts in the PDF. 1.0 = normal, 0.8 = smaller, 1.2 = larger",
                    key="pdf_font_scale"
                )
                st.session_state["font_scale"] = font_scale
            
            with font_col2:
                font_family = st.selectbox(
                    "🔤 Font Family",
                    options=["Helvetica", "Times", "Courier"],
                    index=["Helvetica", "Times", "Courier"].index(st.session_state.get("font_family", "Helvetica")),
                    help="Choose the font style for your PDF",
                    key="pdf_font_family"
                )
                st.session_state["font_family"] = font_family
            
            st.info(f"Current settings: Font size at {int(font_scale * 100)}%, using {font_family} font")

    st.divider()
        
        # ============== PDF GENERATION SECTION ==============
        
    with st.expander("📄 PDF Generator", expanded=True):
        st.header("📥 Generate & Download Your Documents")
        st.caption("One-click generation with automatic download")
        
        # Get font settings from session state
        font_scale = st.session_state.get("font_scale", 1.0)
        font_family = st.session_state.get("font_family", "Helvetica")
        
        st.info(f"📊 Current PDF Settings: {int(font_scale * 100)}% font size, {font_family} font")
        st.caption("💡 Tip: Change settings in '⚙️ Resume & Cover Letter Settings' → 'PDF Styling' tab")
        
        st.divider()
        
        pdf_col1, pdf_col2 = st.columns(2)
        
    with pdf_col1:
            st.subheader("📄 Resume PDF")
            if st.button("⚙️ Generate & Download Resume", use_container_width=True, type="primary", key="gen_resume"):
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
                        
                        # Validate data
                        if not data.get("name"):
                            st.error("❌ No resume data found. Please load your resume JSON first.")
                        else:
                            st.info(f"📊 Generating PDF for {data.get('name')}")
                            
                            JSON_PATH.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
                            
                            # Define output path for resume PDF
                            output_pdf = "Rachit_Sharma_Resume_Generated.pdf"
                            create_resume_pdf(
                                json_path=str(JSON_PATH), 
                                output_path=output_pdf,
                                font_scale=font_scale,
                                font_family=font_family
                            )
                            
                            st.success("✅ Resume PDF generated successfully!")
                            
                            if Path(output_pdf).exists():
                                with open(output_pdf, "rb") as f:
                                    pdf_bytes = f.read()
                                    st.download_button(
                                        "⬇️ Download Resume PDF",
                                        data=pdf_bytes,
                                        file_name=output_pdf,
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key="download_resume"
                                    )
                                
                                # Show file size
                                file_size = len(pdf_bytes) / 1024
                                st.caption(f"📊 File size: {file_size:.1f} KB")
                            else:
                                st.error("❌ PDF file was not created. Please try again.")
                                
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON. Please fix syntax errors in editor.")
                    except Exception as e:
                        st.error(f"❌ Error generating PDF: {str(e)}")
                        import traceback
                        with st.expander("🔍 Error Details"):
                            st.code(traceback.format_exc())
        
    with pdf_col2:
            st.subheader("📝 Cover Letter PDF")
            if st.button("📝 Generate & Download Cover Letter", use_container_width=True, type="primary", key="gen_coverletter"):
                with st.spinner("📝 Generating cover letter PDF..."):
                    try:
                        raw_data = json.loads(st.session_state["edited_json"])
                        
                        if "resume_json" in raw_data:
                            data = raw_data["resume_json"]
                            if isinstance(data, dict) and "resume_json" in data:
                                data = data["resume_json"]
                        else:
                            data = raw_data
                        
                        if "cover_letter" not in data or not data["cover_letter"]:
                            st.warning("⚠️ No cover letter found in JSON.")
                            st.info("💡 Click the '✍️ AI: Generate Cover Letter' button above to create a cover letter first.")
                        else:
                            st.info(f"📊 Generating cover letter for {data.get('name')}")
                            
                            JSON_PATH.write_text(json.dumps(raw_data, indent=2, ensure_ascii=False), encoding="utf-8")
                            
                            # Define output path for cover letter PDF
                            cover_pdf = "Cover_Letter.pdf"
                            create_cover_letter_pdf(
                                json_path=str(JSON_PATH), 
                                output_path=cover_pdf,
                                font_scale=font_scale,
                                font_family=font_family
                            )
                            
                            st.success("✅ Cover letter PDF generated!")
                            
                            if Path(cover_pdf).exists():
                                with open(cover_pdf, "rb") as f:
                                    pdf_bytes = f.read()
                                    st.download_button(
                                        "⬇️ Download Cover Letter PDF",
                                        data=pdf_bytes,
                                        file_name=cover_pdf,
                                        mime="application/pdf",
                                        use_container_width=True,
                                        key="download_coverletter"
                                    )
                                
                                # Show file size and word count if available
                                file_size = len(pdf_bytes) / 1024
                                st.caption(f"📊 File size: {file_size:.1f} KB")
                                
                                if "body_word_count" in data.get("cover_letter", {}):
                                    word_count = data["cover_letter"]["body_word_count"]
                                    st.caption(f"📝 Body word count: {word_count} words")
                            else:
                                st.error("❌ PDF file was not created. Please try again.")
                                
                    except json.JSONDecodeError:
                        st.error("❌ Invalid JSON in editor.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        with st.expander("🔍 Error Details"):
                            st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
