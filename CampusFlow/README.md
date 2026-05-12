# CampusFlow / College0 Final Demo

CampusFlow is an AI-enabled online college program management system.

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite
- AI feature: Local knowledge-base chatbot with LLM fallback simulation

This project uses **React and FastAPI**, not Flask. Flask is not needed because FastAPI already provides the backend API.

## Run Backend

```bash
cd backend
python3 -m pip install -r requirements.txt
python3 main.py
```

Open backend docs:

```text
http://127.0.0.1:8000/docs
```

## Run Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open website:

```text
http://127.0.0.1:5173
```

## Demo Logins

Registrar:

```text
username: registrar
password: registrar123
```

Instructor:

```text
username: prof_chen
password: pass123
```

Student:

```text
username: S1001
password: pass123
```
