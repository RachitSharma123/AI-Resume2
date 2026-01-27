# google_sheets_integration.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import streamlit as st

# Define the scope
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def get_google_sheets_client():
    """Initialize and return Google Sheets client."""
    try:
        # Get credentials from Streamlit secrets
        creds_dict = st.secrets.get("google_sheets_credentials", {})
        
        if not creds_dict:
            st.error("❌ Google Sheets credentials not found in secrets")
            return None
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"❌ Error connecting to Google Sheets: {str(e)}")
        return None


def create_job_tracker_sheet(client, sheet_name="Job Applications Tracker"):
    """Create a new job tracker spreadsheet."""
    try:
        # Create new spreadsheet
        spreadsheet = client.create(sheet_name)
        worksheet = spreadsheet.sheet1
        
        # Set up headers
        headers = [
            "Date Applied",
            "Company",
            "Position",
            "Job URL",
            "Status",
            "ATS Score",
            "Contact Person",
            "Contact Email",
            "Follow-up Date",
            "Notes",
            "Resume Version",
            "Cover Letter"
        ]
        
        worksheet.update('A1:L1', [headers])
        
        # Format header row
        worksheet.format('A1:L1', {
            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            "horizontalAlignment": "CENTER"
        })
        
        return spreadsheet.url, spreadsheet.id
    except Exception as e:
        raise Exception(f"Error creating tracker: {str(e)}")


def get_or_create_tracker(client, sheet_id=None):
    """Get existing tracker or create new one."""
    try:
        if sheet_id:
            # Try to open existing sheet
            try:
                spreadsheet = client.open_by_key(sheet_id)
                worksheet = spreadsheet.sheet1
                return spreadsheet, worksheet
            except:
                st.warning("⚠️ Could not find existing tracker, creating new one...")
        
        # Create new tracker
        url, new_sheet_id = create_job_tracker_sheet(client)
        st.success(f"✅ Created new tracker! Save this ID: {new_sheet_id}")
        st.info(f"📊 Tracker URL: {url}")
        
        spreadsheet = client.open_by_key(new_sheet_id)
        worksheet = spreadsheet.sheet1
        return spreadsheet, worksheet
        
    except Exception as e:
        raise Exception(f"Error accessing tracker: {str(e)}")


def add_job_application(worksheet, application_data):
    """Add a new job application to the tracker."""
    try:
        # Get current date
        date_applied = datetime.now().strftime("%Y-%m-%d")
        
        # Prepare row data
        row = [
            date_applied,
            application_data.get("company", ""),
            application_data.get("position", ""),
            application_data.get("job_url", ""),
            application_data.get("status", "Applied"),
            application_data.get("ats_score", ""),
            application_data.get("contact_person", ""),
            application_data.get("contact_email", ""),
            application_data.get("follow_up_date", ""),
            application_data.get("notes", ""),
            application_data.get("resume_version", ""),
            application_data.get("has_cover_letter", "No")
        ]
        
        # Append row
        worksheet.append_row(row)
        return True
    except Exception as e:
        raise Exception(f"Error adding application: {str(e)}")


def get_all_applications(worksheet):
    """Get all job applications from tracker."""
    try:
        all_records = worksheet.get_all_records()
        return all_records
    except Exception as e:
        raise Exception(f"Error fetching applications: {str(e)}")


def update_application_status(worksheet, row_number, new_status):
    """Update status of a specific application."""
    try:
        # Status is in column E (5th column)
        worksheet.update_cell(row_number, 5, new_status)
        return True
    except Exception as e:
        raise Exception(f"Error updating status: {str(e)}")


def get_statistics(applications):
    """Calculate statistics from applications."""
    if not applications:
        return {
            "total": 0,
            "applied": 0,
            "interviewing": 0,
            "offered": 0,
            "rejected": 0,
            "response_rate": 0
        }
    
    total = len(applications)
    applied = sum(1 for app in applications if app.get("Status") == "Applied")
    interviewing = sum(1 for app in applications if "Interview" in app.get("Status", ""))
    offered = sum(1 for app in applications if "Offer" in app.get("Status", ""))
    rejected = sum(1 for app in applications if "Reject" in app.get("Status", ""))
    
    response_rate = ((total - applied) / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "applied": applied,
        "interviewing": interviewing,
        "offered": offered,
        "rejected": rejected,
        "response_rate": round(response_rate, 1)
    }


def search_applications(applications, search_term):
    """Search applications by company or position."""
    if not search_term:
        return applications
    
    search_term = search_term.lower()
    return [
        app for app in applications
        if search_term in app.get("Company", "").lower() 
        or search_term in app.get("Position", "").lower()
    ]
```

## 📦 Your project structure should look like:
```
your-project/
├── main.py
├── pdf_generator.py
├── drawing_utils.py
├── utils.py
├── ai_functions.py
├── google_sheets_integration.py  ← CREATE THIS FILE
├── resume_data.json
├── requirements.txt
└── .streamlit/
    └── secrets.toml
