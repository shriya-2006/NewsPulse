# NewsPulse — Enterprise News Monitoring & Report Generation System

**Full-Stack Internship Project developed for RINL, Visakhapatnam Steel Plant**

NewsPulse is an enterprise news monitoring and report generation platform designed to automate the daily process of discovering, filtering, organizing, and reporting industry-relevant news.

The system enables users to search for news related to topics such as **Steel, Coal, Iron Ore, Manufacturing, RINL, Government Policies, Mining, and Exports**, apply language and publication filters, select relevant articles, and generate structured PDF reports.

---

## Overview

Organizations often spend significant time manually searching multiple news sources for industry-relevant information and compiling selected articles into reports.

NewsPulse streamlines this workflow by providing a centralized platform for:

- Searching current industry-related news
- Filtering news by language, newspaper, edition, and date
- Using predefined or custom search tags
- Selecting relevant articles
- Generating downloadable PDF reports
- Maintaining report history
- Monitoring user and system activity through an admin dashboard

---

## Key Features

### Authentication and User Management

- User registration and login
- JWT-based authentication
- Secure password hashing using bcrypt
- Protected frontend and backend routes
- Remember Me functionality
- Forgot-password and password-reset workflow
- SMTP-based password recovery with development fallback
- Role-based access for users and administrators
- Secure logout and authenticated user sessions

### News Search and Aggregation

NewsPulse uses a multi-provider news aggregation strategy:

1. **GNews API**
2. **NewsData.io API**
3. **Google News RSS fallback**

If one provider is unavailable or fails to return usable results, the system can fall back to another configured source.

Additional search capabilities include:

- Predefined industry-specific tags
- Custom keyword searches
- Multi-select tags combined using OR-based search
- English, Telugu, and Hindi search support
- Custom date-range filtering
- Search result pagination
- Loading, error, and no-results states
- Provider failure diagnostics
- Search result caching to reduce repeated external API requests

### Dynamic Language → Newspaper → Edition Filtering

The newspaper and edition filtering system is database-driven rather than hard-coded in the frontend.

The application supports:

- Dynamic newspaper lists based on selected language
- Dynamic edition lists based on selected newspaper
- Searching by edition without requiring a newspaper selection
- Automatic filter resets when parent selections change
- Database-backed newspaper and edition management
- Strict post-fetch newspaper verification

New newspapers and editions can be added through database records without modifying frontend filtering logic.

### Multilingual Support

Industry-specific predefined tags are available in:

- English
- Telugu
- Hindi

The available tags automatically change based on the selected search language.

### Article Selection and PDF Report Generation

Users can:

- Select multiple news articles
- Generate structured PDF reports
- Download generated reports
- Access previously generated reports from Report History

PDF generation is handled using **WeasyPrint** and includes:

- Structured report layout
- Cover page
- Headers and footers
- Page numbering
- Available article content and descriptions
- Persistent report and article records in MySQL

When a news provider supplies article content, NewsPulse uses the available text in the generated report. If full content is unavailable, the system falls back to the available description.

### Report History

The Report History module allows authenticated users to:

- View previously generated reports
- Access report metadata
- Re-download existing PDF reports

### Admin Dashboard

Administrators have access to a dedicated dashboard containing:

- Platform statistics
- User activity information
- Search and report analytics
- Recent activity
- Per-user activity
- Multiple analytical charts and visualizations

### Search Result Caching

To reduce unnecessary calls to external news providers, NewsPulse caches search results in the database.

This helps:

- Reduce API quota consumption
- Improve response time for repeated searches
- Reduce load on RSS providers
- Improve reliability under repeated usage

A retention cleanup process removes old cached data while preserving articles associated with existing reports.

---

## System Architecture

```text
┌─────────────────────┐
│   React Frontend    │
│   Vite + React      │
│   React Router      │
└──────────┬──────────┘
           │
           │ REST API / JSON
           ▼
┌─────────────────────┐
│   FastAPI Backend   │
│                     │
│ Routes              │
│   ↓                 │
│ Pydantic Schemas    │
│   ↓                 │
│ Services            │
│   ↓                 │
│ SQLAlchemy Models   │
└──────────┬──────────┘
           │
           │ SQL
           ▼
┌─────────────────────┐
│      MySQL          │
│      Database       │
└─────────────────────┘
```

---

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- HTML5
- CSS3
- React Router

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy
- JWT Authentication
- bcrypt
- httpx
- WeasyPrint

### Database

- MySQL

### News Sources

- GNews API
- NewsData.io API
- Google News RSS

### Testing

- pytest
- Automated backend test suite

### Deployment

- GitHub — Source code repository
- Render — FastAPI backend
- Vercel — React/Vite frontend
- Aiven — Managed MySQL database

---

## Repository Structure

```text
NewsPulse/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── scripts/
│   │   ├── services/
│   │   │   └── news/
│   │   ├── templates/
│   │   └── utils/
│   │
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── context/
│   │   ├── pages/
│   │   └── styles/
│   │
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── database/
│   └── schema.sql
│
└── README.md
```

---

## Core Modules

| Module | Description | Status |
|---|---|---|
| Project Architecture | Full-stack project structure and layered architecture | Complete |
| Authentication | Register, login, logout, password reset, JWT authentication | Complete |
| News Search | Multi-provider news aggregation and filtering | Complete |
| Multilingual Search | English, Telugu, and Hindi industry tags | Complete |
| Dynamic Filters | Database-backed language, newspaper, and edition filtering | Complete |
| Article Selection | Multi-article selection for report generation | Complete |
| PDF Reports | Structured PDF generation and download | Complete |
| Report History | View and re-download generated reports | Complete |
| Admin Dashboard | Statistics, charts, and user activity | Complete |
| Search Caching | Database-backed caching and retention cleanup | Complete |
| Automated Testing | Backend pytest test suite | Complete |

---

## Local Development Setup

### Prerequisites

Make sure the following are installed:

- Python 3.x
- Node.js and npm
- MySQL
- Git

---

## 1. Clone the Repository

```bash
git clone https://github.com/shriya-2006/NewsPulse.git
cd NewsPulse
```

---

## 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment.

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file from the example.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Configure the required environment variables in `.env`.

> Never commit the real `.env` file, database passwords, API keys, or secret keys to GitHub.

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

The backend will normally be available at:

```text
http://localhost:8000
```

FastAPI API documentation:

```text
http://localhost:8000/docs
```

---

## 3. Database Setup

Create a MySQL database and import:

```text
database/schema.sql
```

Then configure the backend environment variables with the appropriate database connection details.

The application uses MySQL for:

- Users
- Authentication-related data
- Search history
- Newspapers and editions
- Cached search results
- Reports
- Report articles
- Administrative analytics

---

## 4. Frontend Setup

Open a new terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the frontend environment file.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux / macOS

```bash
cp .env.example .env
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

## Environment Variables

The repository contains `.env.example` files that document the environment variables required by the frontend and backend.

### Important Security Rules

- Never commit `.env` files
- Never commit database passwords
- Never commit production `SECRET_KEY` values
- Never commit API keys
- Store production secrets using the environment-variable settings provided by the deployment platform

---

## API Overview

The backend exposes REST API endpoints for:

- Authentication
- User management
- News search
- Search tags
- Newspapers
- Editions
- PDF report generation
- Report history
- Administrative analytics
- Health checks

FastAPI automatically provides interactive API documentation at:

```text
/docs
```

when the backend is running.

---

## Testing

The backend includes an automated pytest test suite covering major application functionality.

Run the tests from the `backend` directory:

```bash
pytest
```

The test suite covers areas including:

- Authentication
- News search
- Reports
- Admin functionality
- Search caching
- Database schema consistency

---

## Deployment Architecture

The production deployment uses separate services for each layer:

```text
                ┌────────────────────┐
                │      Vercel        │
                │   React Frontend   │
                └─────────┬──────────┘
                          │
                          │ HTTPS / REST API
                          ▼
                ┌────────────────────┐
                │       Render       │
                │  FastAPI Backend   │
                └─────────┬──────────┘
                          │
                          │ Secure MySQL Connection
                          ▼
                ┌────────────────────┐
                │       Aiven        │
                │   MySQL Database   │
                └────────────────────┘
```

### Production Services

- **Frontend:** Vercel
- **Backend:** Render
- **Database:** Aiven MySQL
- **Source Control:** GitHub

Production credentials and API keys are configured through the respective deployment platforms and are not stored in the repository.

---

## Security

NewsPulse implements several security practices:

- Password hashing with bcrypt
- JWT-based authentication
- Protected API endpoints
- Role-based access control
- Environment-based secret management
- `.gitignore` protection for local environment files
- Server-side request validation using Pydantic
- Database-backed authentication and authorization

---

## Project Status

**Core Development: Complete**

The major functional modules of NewsPulse are implemented end-to-end:

- Authentication
- News aggregation and search
- Multilingual tags
- Dynamic filtering
- Article selection
- PDF report generation
- Report history
- Admin analytics
- Search caching
- Automated backend testing

The project is prepared for cloud deployment using a managed MySQL database, a hosted FastAPI backend, and a separately deployed React frontend.

---

## Internship Context

NewsPulse was developed as a full-stack internship project for **RINL, Visakhapatnam Steel Plant**.

The project addresses a practical enterprise workflow: reducing the manual effort required to discover industry-relevant news and compile selected information into structured reports.

---


## Disclaimer

NewsPulse aggregates news metadata and available content from configured third-party news providers and RSS sources. Availability and completeness of article content depend on the respective provider, API plan, and source. The application does not bypass publisher access controls or guarantee access to full copyrighted article text.
