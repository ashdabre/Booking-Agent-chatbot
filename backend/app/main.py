from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
from .agent import build_agent
from .google_calendar import get_credentials_from_code, build_flow, deserialize_credentials
import os
from fastapi.responses import JSONResponse

app = FastAPI()

# Enable CORS so frontend can call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict if needed: ["http://localhost:8501"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Root route for browser check
@app.get("/")
def root():
    return {"message": "✅ FastAPI backend is running."}

# Build the LangGraph agent
agent = build_agent()

# 👇 GET Google OAuth URL
@app.get("/auth/url")
def auth_url():
    try:
        flow = build_flow()
        auth_url, _ = flow.authorization_url(prompt='consent')
        return {"url": auth_url}
    except Exception as e:
        print("Error in /auth/url:", e)
        return {"error": str(e)}

# 👇 Google OAuth callback — exchange code for tokens
@app.get("/auth/callback")
def auth_callback(code: str):
    try:
        creds = get_credentials_from_code(code)
        return {
            "status": "success",
            "creds": creds.to_json()
        }
    except Exception as e:
        return {"error": str(e)}

# 👇 Main chat endpoint
@app.post("/chat")
async def chat(msg: dict):
    creds = deserialize_credentials(msg["creds"])

    # Ensure full state is passed to the agent
    initial_state = {
        "input": msg["text"],
        "creds": creds,
        "start": "",
        "end": "",
        "duration": 30,
        "available": False,
        "message": "",
        "confirmation": ""
    }

    try:
        result = agent.invoke(initial_state)
        return {
            "response": result.get("confirmation") or result.get("message", "Sorry, could not complete request.")
        }
    except Exception as e:
        return {"error": str(e)}

    
def get_credentials_from_code(code: str):
    print("Auth code received:", code)
    flow = build_flow()
    flow.fetch_token(code=code)
    return flow.credentials
