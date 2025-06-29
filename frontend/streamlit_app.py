import streamlit as st
import requests
import json

API_URL = "http://localhost:8001"  # Update this if backend runs elsewhere

st.set_page_config(page_title="📅 Booking Agent", page_icon="📅")
st.title("📅 Booking Agent - Google Calendar")

# ✅ Handle query params
query_params = st.query_params

# ✅ Store chat history
if "history" not in st.session_state:
    st.session_state.history = []

# ✅ Handle Google Auth Callback
if "code" in query_params and "creds" not in st.session_state:
    code = query_params["code"]
    try:
        res = requests.get(f"{API_URL}/auth/callback", params={"code": code})
        data = res.json()
        if "creds" in data:
            st.session_state.creds = data["creds"]  # This is a serialized JSON
            st.success("✅ Google Calendar connected.")
        else:
            st.error(f"❌ Auth failed: {data}")
    except Exception as e:
        st.error(f"Auth callback error: {e}")
        st.stop()

# ✅ If creds not connected
if "creds" not in st.session_state:
    if st.button("🔗 Connect Google Calendar"):
        try:
            res = requests.get(f"{API_URL}/auth/url")
            auth = res.json()
            if "url" in auth:
                st.markdown(f"[👉 Click here to authenticate]({auth['url']})", unsafe_allow_html=True)
            else:
                st.error(f"Backend error: {auth}")
        except Exception as e:
            st.error(f"Could not get auth URL: {e}")
    st.stop()

# ✅ Chat UI
user_input = st.chat_input("Ask me to book a meeting...")

if user_input:
    st.session_state.history.append({"sender": "user", "text": user_input})
    with st.spinner("🤖 Working..."):
        try:
            payload = {
                "text": user_input,
                "creds": st.session_state.creds
            }
            response = requests.post(f"{API_URL}/chat", json=payload)

            # Debug info
            st.write("🔍 Status Code:", response.status_code)
            if response.status_code == 200:
               st.write("🔍 Raw response: ✅ Meeting booked successfully")
            else:
               st.write("🔍 Raw response: ❌ Booking Unsuccessfull")
            if response.headers.get("Content-Type", "").startswith("application/json"):
                resp = response.json()
                raw_text = resp.get("response") or resp.get("error") or str(resp)
            else:
                raw_text = response.text

            # st.write("🔍 Raw response:", raw_text)

            # ✅ Only parse if valid JSON
            if response.headers.get("Content-Type", "").startswith("application/json"):
                resp = response.json()
            else:
                st.error("❌ Backend did not return valid JSON")
                st.stop()

            event = resp.get("response", {})
            if isinstance(event, dict) and event.get("htmlLink"):
    # nicely format from the dict directly
              msg = (
        "✅ **Success! Your meeting is booked.**\n\n"
        f"- 📌 **Title:** {event['summary']}\n"
        f"- 📅 **Start:** {event['start']}\n\n"
        f"- ⏰ **End:** {event['end']}\n\n"
        f"- 👤 **Organizer:** {event['organizer']}\n\n"
        f"- 🔗 **[Open in Google Calendar]({event['htmlLink']})**"
                    )
            else:
    # fallback to whatever string message the backend sent
              msg = resp.get("response") or resp.get("error") or "⚠️ No response from agent."

            st.session_state.history.append({"sender": "bot", "text": msg})
        except Exception as e:
            st.error(f"❌ Chat request failed: {e}")

# ✅ Show messages
for msg in st.session_state.history:
    role = "user" if msg["sender"] == "user" else "assistant"
    st.chat_message(role).markdown(msg["text"], unsafe_allow_html=True)
