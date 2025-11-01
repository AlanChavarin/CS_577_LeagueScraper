# League Scraper Project

A full-stack application with Next.js frontend and Django backend.

## Project Structure

```
.
├── frontend/          # Next.js frontend application
└── backend/           # Django backend API
```

## Frontend Setup

Navigate to the `frontend` directory and follow the Next.js setup instructions:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on `http://localhost:3000`

## Backend Setup

### Start PostgreSQL Database

First, start the PostgreSQL database using Docker Compose (from project root):

```bash
docker-compose up -d
```

### Django Setup

Navigate to the `backend` directory and follow the Django setup instructions:

```bash
cd backend
python -m venv venv
# Activate virtual environment (Windows: venv\Scripts\activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend runs on `http://localhost:8000`

**Note**: Make sure PostgreSQL is running before starting the Django server.

## Features

- **Frontend**: Next.js with TypeScript, Tailwind CSS, and ESLint
- **Backend**: Django with REST Framework and CORS support
- **Database**: PostgreSQL running in Docker
- **Data Science Libraries**: numpy, pandas, scipy, scikit-learn, matplotlib, seaborn

