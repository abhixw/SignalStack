# 🚀 SignaXAI - AI-Native Hiring Platform

**SignaXAI** is an AI-powered hiring platform that evaluates candidates based on real work artifacts (GitHub repositories) rather than resumes. It uses advanced signal extraction, LLM-powered analysis, and transparent scoring to match candidates to job outcomes.

![SignaXAI Demo](https://img.shields.io/badge/Status-Hackathon%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688)

---

## ✨ Features

### For Recruiters
- **Outcome-Based Job Definitions** - Define jobs by what candidates will accomplish, not just skills
- **AI Task Decomposition** - Automatically break down projects into verifiable tasks
- **Smart Candidate Matching** - AI analyzes GitHub repos to match candidates to tasks

### For Candidates
- **Proof-Based Applications** - Submit GitHub repositories as proof of work
- **Transparent Scoring** - See exactly why you matched (or didn't match)
- **Fair Evaluation** - Anonymized review option removes bias

### Technical Features
- **Signal Extraction** - Detects ML models, web frameworks, tests, deployment artifacts
- **LLM-Powered Evaluation** - Uses Groq llama3-70b-8192 for intelligent analysis
- **Audit Logging** - Full transparency of all system actions
- **System Learning** - Weights adjust based on feedback

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React Frontend │────▶│  FastAPI Backend │────▶│   SQLite DB     │
│   (Vite + JSX)   │     │   (Python 3.10)  │     │                 │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌──────────┐  ┌─────────┐
              │ GitHub  │  │  Groq    │  │ Signal  │
              │   API   │  │   LLM    │  │ Engine  │
              └─────────┘  └──────────┘  └─────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- GitHub Token (for repo analysis)
- Groq API Key (for AI features)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys:
# GROQ_API_KEY=your_key_here
# GITHUB_TOKEN=your_token_here

# Run server
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

### Access the App
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📖 Usage Guide

### 1. Create an Outcome (Job)
1. Navigate to "Create Outcome"
2. Enter role title and project description
3. Click "Suggest with AI" to auto-generate tasks
4. Review and save

### 2. Submit Proof (Candidate)
1. Click on an outcome from the dashboard
2. Enter your email and GitHub repository URL
3. View live preview of your repo
4. Submit proof

### 3. Evaluate Candidates
1. Click "Evaluate AI" on an outcome
2. System analyzes GitHub repos for signals:
   - ML models (.pkl, scikit-learn)
   - Web frameworks (Flask, FastAPI)
   - Tests (pytest, unittest)
   - Deployment (Docker, CI/CD)
3. View match scores and evidence

### 4. Review & Decide
1. Go to "Reviewer Queue"
2. Click on an evaluation
3. See detailed breakdown with code evidence
4. Make hiring decision

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite, Lucide Icons |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite (dev), PostgreSQL (prod-ready) |
| AI/ML | Groq llama3-70b-8192 , GitHub API |
| Auth | JWT (planned) |

---

## 📁 Project Structure

```
SignalStack/
├── backend/
│   ├── main.py           # FastAPI app & routes
│   ├── services.py       # Signal extraction & LLM
│   ├── crud.py           # Database operations
│   ├── models.py         # SQLAlchemy models
│   ├── schemas.py        # Pydantic schemas
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/        # React page components
│   │   ├── components/   # Reusable UI components
│   │   └── api.js        # API client
│   └── package.json
└── README.md
```

---

## 🔑 Environment Variables

Create a `.env` file in the `backend/` directory:

```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_personal_access_token
```

---

## 🧪 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/outcomes` | List all job outcomes |
| POST | `/outcomes` | Create new outcome |
| POST | `/proofs` | Submit candidate proof |
| POST | `/plugin/evaluate` | Run AI evaluation |
| GET | `/evaluations` | List all evaluations |
| POST | `/plugin/feedback` | Submit hiring feedback |
| GET | `/admin/audit-logs` | View all system actions |

---

## 🎯 Roadmap

- [x] Core evaluation engine
- [x] LLM-powered task decomposition
- [x] GitHub signal extraction
- [x] Anonymized review mode
- [x] Audit logging
- [ ] User authentication
- [ ] Multi-tenant support
- [ ] Production deployment
- [ ] Webhook integrations

---

## 👥 Team

Built for Hackathon 2026.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Groq API for AI capabilities
- FastAPI for the excellent Python framework
- React team for the frontend framework
