#  📅 Booking Agent – Google Calendar Scheduler


A smart conversational assistant built using LangGraph, Google Calendar API, FastAPI, and Streamlit. Easily book or cancel meetings through natural language like:
#
"Hey, book a meeting between 3-5 PM next week."

"Do you have free time this Friday?"

""Book a meeting between 3-5 PM next week."
."

#
🧠 Features
✨ Natural language understanding (NLU)

📅 Real-time Google Calendar integration

✅ Availability checking before booking

🗑️ Support for deletion (e.g., "Delete meeting at 3 PM")

📆 Handles ranges: “Book a slot between 2–4 PM next week”

🔐 Google OAuth2-based authentication

#

# Backend Setup (FastAPI + LangGraph)
📍 Step 1: Create and activate virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows


📍 Step 2: Install dependencies

pip install -r requirements.txt


📍 Step 3: Add credentials.json
Place your Google API OAuth2 credentials file (credentials.json) in the backend directory. Make sure it has calendar scopes.

📍 Step 4: Run the backend server

uvicorn app.main:app --reload --port 8001


# 🎨 Frontend Setup (Streamlit)
📍 Step 1: Navigate to frontend and install dependencies

cd ../frontend
pip install streamlit requests

📍 Step 2: Run the Streamlit app

streamlit run app.py
It will open at http://localhost:8501

#


# 🔐 Google Calendar Setup
Go to https://console.cloud.google.com

Create a project

Enable Google Calendar API

Create OAuth2 Client ID credentials (choose Desktop or Web)

Download the credentials.json file and place it in the /backend folder
