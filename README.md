# SchedulaiWeb
SchedulaiWeb is a smart AI-powered calendar assistant that uses natural language and LLMs to schedule, update, and manage your Google Calendar events — all in real time, with secure OAuth login and a live in-app calendar viewer.

<br>
<p align="center">
<img width="676" height="401" alt="image" align="center" src="https://github.com/user-attachments/assets/e5849d76-a27d-4cd9-9226-6eb9c662d2c7" />
</p>
<br>


# 🧠 SchedulaiWeb — Smart AI Calendar Assistant

**SchedulaiWeb** is an intelligent calendar assistant that lets users schedule, update, delete, and view events using natural language — powered by **LLMs and Google Calendar API**. Designed with a FastAPI backend and MongoDB for secure token storage, Schedulai turns everyday text like _“Book a call with Sarah tomorrow at 3”_ into actual calendar actions.

<br>
<p align="center">
<img width="1268" height="627" alt="image"  src="https://github.com/user-attachments/assets/c5242c47-2e25-45dc-baf7-c21a1b9dad9c" />
</p>
</br>

---

## 🎯 Purpose

SchedulaiWeb aims to make **calendar management conversational**. Whether it’s scheduling a meeting, checking for available slots, rescheduling, or viewing today’s events — just type your intent. The assistant understands and executes it via your connected Google Calendar.

---

## ⚙️ Core Features

- ✅ **Natural Language Scheduling**
  - “Schedule a call with John tomorrow from 2pm to 3pm”
- 🔁 **Reschedule or Rename Events**
  - “Move the 3pm call to 4pm” or “Rename my meeting to ‘Client Sync’”
- ❌ **Delete by Title + Time**
  - “Delete the ‘Standup’ at 10am”
- 📅 **Live Free Slot Detection**
  - “What free slots do I have on Friday?”
- 📌 **Booked Event Summary**
  - “What are my meetings today?”
- 🌐 **Live Google Calendar View**
  - A built-in calendar popup shows real-time synced events using FullCalendar.js
- 🔐 **Google OAuth 2.0 Login**
  - Credentials stored securely in MongoDB
- 📦 **OpenRouter LLM Integration**
  - Uses **Mistral-7B-Instruct** to parse user messages into structured JSON

---

## 🔁 Google Calendar Integration

Schedulai uses:
- **Google OAuth2** to authenticate users (redirects to Google login)
- **Google Calendar API** to:
  - Add new events
  - Delete/reschedule existing events
  - Check free/busy slots
  - Fetch and display daily events

Each request uses tokens securely stored in MongoDB under a unique `user_id`.

---

## 💡 How It Works

1. User logs in via Google (OAuth 2.0)
2. Message is typed: _“Schedule a meeting with Mike on Thursday from 4 to 5”_
3. OpenRouter’s **Mistral-7B** LLM parses the message → structured JSON
4. Backend routes action to Google Calendar API
5. Event is created/deleted/updated accordingly
6. If needed, the live calendar popup refreshes to reflect changes instantly

---

## 🛠 Setup Instructions

### 🔐 1. Environment Variables

Create or update a `.env` file:
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
REDIRECT_URI=http://localhost:8000/auth/callback

OPENROUTER_API_KEY=your_openrouter_api_key
LLM_MODEL=mistralai/mistral-7b-instruct:free

MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/

### 📄 2. Google Credentials File

Download `credentials.json` from [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and place in root


**3.Finally Install and Run**

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

---------------------------------------------
**These are excluded from Git for security:**

.env

credentials.json

token.json

__pycache__, .venv, etc.
--------------------------------------------
⚠️ Final Note
There may be some errors when first running the app due to the removal of sensitive files like credentials or tokens. These are easy to troubleshoot by:

Providing your own .env and client_secret.json

Checking the terminal/log messages for missing values

Ensuring MongoDB Atlas access is correctly configured

This is a rough but functional prototype, showcasing real-time AI-powered scheduling. While there's plenty of room for UI/UX polish and code improvements, its core strengths lie in intelligent calendar control and seamless integration of AI with Google services.



