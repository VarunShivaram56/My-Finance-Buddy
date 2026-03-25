# My Finance Buddy

Local-first web app for analyzing redacted bank statement PDFs with a rule-first backend pipeline and a simple React dashboard.

## Stack

- Backend: Python, FastAPI, pdfplumber, MySQL, ChromaDB, OpenRouter API
- Frontend: React, TailwindCSS, Axios, Recharts
- AI models:
  - Agent 1: `google/gemma-3n-e2b-it`
  - Agent 2: `arcee-ai/trinity-mini`
  - Agent 3: `openai/gpt-oss-20b`
  - Embeddings: `nomic-embed-text`

## Project Structure

```text
my-finance-buddy
├── backend
│   ├── agents
│   ├── database
│   ├── routers
│   ├── services
│   ├── utils
│   ├── main.py
│   └── requirements.txt
├── frontend
│   ├── public
│   ├── src
│   ├── package.json
│   └── tailwind.config.js
└── README.md
```

## One-Command Dev Startup

From the project root:

```bash
cd C:\Users\varun\OneDrive\Documents\Playground\my-finance-buddy
npm install
npm run dev
```

This starts:

- React frontend on `http://localhost:3000`
- FastAPI backend on `http://localhost:8000`

Make sure Python dependencies are installed once before using the combined dev command.

## Backend Setup

1. Create a MySQL database named `my_finance_buddy`.
2. Optionally run the schema in [backend/database/schema.sql](C:\Users\varun\OneDrive\Documents\Playground\my-finance-buddy\backend\database\schema.sql).
3. Copy `backend/.env.example` to `backend/.env` and update credentials.
4. Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

5. Start the API directly if needed:

```bash
cd backend
uvicorn main:app --reload
```

## Frontend Setup

1. Copy `frontend/.env.example` to `frontend/.env` if you want to override the API URL.
2. Install dependencies and start the app directly if needed:

```bash
cd frontend
npm install
npm start
```

The UI runs at `http://localhost:3000` and expects the FastAPI backend at `http://localhost:8000`.

## API Overview

### `POST /upload-statement`

Accepts a redacted bank statement PDF as `multipart/form-data`.

```bash
curl -X POST "http://localhost:8000/upload-statement" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample-redacted-statement.pdf;type=application/pdf"
```

### `GET /dashboard`

Returns summary cards, charts, merchant rollups, transactions, and optional AI insights.

```bash
curl "http://localhost:8000/dashboard"
```

## Processing Pipeline

1. `pdfplumber` extracts tables from each PDF page with `page.extract_tables()`.
2. Rule-based parsing detects date, amount, transaction type, and merchant.
3. Low-confidence rows are batched to Agent 1 for JSON structuring.
4. Merchant dictionary and vector memory try categorization first.
5. Unknown merchants are batched to Agent 2 for one of 13 categories.
6. Data is stored in MySQL and summarized for charts.
7. Agent 3 optionally produces short insight bullets.

## Notes

- The app is designed to work locally and only calls LLMs when rules are insufficient.
- ChromaDB stores merchant-category memory to reduce repeated categorization calls.
- Upload only redacted statements to preserve privacy.
