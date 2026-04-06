# My Finance Buddy

Local-first AI-assisted personal finance dashboard. Upload redacted bank statement PDFs, add manual transactions/loans/assets, and explore insights via a SQL-based RAG chatbot. The backend is rule-first with LLM fallbacks only when needed.

## Highlights

- Hybrid pipeline: deterministic parsing/categorization with LLM fallback for low-confidence rows
- SQL-RAG chatbot over your live database (SELECT-only guardrails)
- Dashboard analytics, transactions editor, loans/assets tracking
- Runs locally; you control your data and API keys

## Tech Stack

- Backend: FastAPI, SQLAlchemy, pdfplumber
- Frontend: React, TailwindCSS, Recharts, Axios
- Database: SQLite by default (MySQL supported)
- LLM providers: Groq + OpenRouter (optional)

## Project Structure

```text
my-finance-buddy
|-- backend
|   |-- agents
|   |-- database
|   |-- rag
|   |-- routers
|   |-- services
|   |-- utils
|   |-- main.py
|   `-- requirements.txt
|-- frontend
|   |-- public
|   |-- src
|   |-- package.json
|   `-- tailwind.config.js
|-- scripts
|-- chroma_data
|-- package.json
`-- README.md
```

## Prerequisites

- Node.js 18+ (includes npm)
- Python 3.10+

## Quick Start (One Command)

From the project root:

```bash
npm install
npm run dev
```

This starts:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

The `npm run dev` script calls `scripts/start-backend.ps1`, which will:

- Reuse an existing healthy backend on port 8000 if present
- Create/activate a virtual environment under `backend/.venv`
- Install backend requirements if needed
- Launch the FastAPI server

## Environment Setup (Secrets + Database)

Never commit secrets. Use the provided `.env.example` files and keep your real `.env` files local only.

### Backend

1. Copy the example file:

```bash
copy backend\.env.example backend\.env
```

2. Fill in your values in `backend/.env`:

```text
APP_ENV=development
DATABASE_URL=sqlite:///./backend/my_finance_buddy.db
AGENT_ONE_API_KEY=
AGENT_TWO_API_KEY=
AGENT_THREE_API_KEY=
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
AGENT_ONE_MODEL=groq/compound
AGENT_TWO_MODEL=groq/compound
AGENT_THREE_MODEL=openai/gpt-oss-120b
```

Notes:

- If any API key is blank, the app falls back to rule-based logic for that agent.
- SQL-RAG and AI insights require `OPENROUTER_API_KEY` or `AGENT_THREE_API_KEY`.

### Frontend

1. Copy the example file:

```bash
copy frontend\.env.example frontend\.env
```

2. Update the API base URL if you run the backend elsewhere:

```text
REACT_APP_API_BASE_URL=http://localhost:8000
```

## Database Options

### Option A: SQLite (default, zero setup)

No extra setup needed. The default `DATABASE_URL` already points to SQLite.

### Option B: MySQL

1. Create a database (example name: `my_finance_buddy`).
2. Update `DATABASE_URL` in `backend/.env`:

```text
DATABASE_URL=mysql+pymysql://USER:PASSWORD@HOST:3306/my_finance_buddy
```

3. If you want to initialize a schema manually, use:

- `backend/database/schema.sql`

The backend will also create missing tables automatically via SQLAlchemy at startup.

## Running Services Separately (Optional)

Backend only:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend only:

```bash
cd frontend
npm install
npm start
```

## API Surface (Key Endpoints)

- `POST /auth/register`
- `POST /auth/login`
- `POST /upload-statement`
- `GET /dashboard`
- `GET /transactions`
- `POST /chat`
- `GET /loans`
- `POST /loans`
- `GET /api/assets`
- `POST /api/assets`

## Security Notes

- Do not commit `backend/.env` or `frontend/.env` to Git.
- Use redacted bank statements only.
- The backend stores session tokens as hashes (never raw tokens).

## Troubleshooting

- If `npm run dev` fails to start the backend, try running the backend directly (see above) to see Python errors.
- If the UI cannot reach the API, confirm `REACT_APP_API_BASE_URL` matches the backend URL.
- If LLM calls fail, verify your API keys and provider limits.

## License

Add your license info here.
