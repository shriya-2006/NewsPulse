# NewsPulse — Frontend (React + Vite)

## Scope so far
- **Day 1:** Auth pages and Dashboard shell built and styled, no real logic.
- **Module 2:** JWT Authentication fully wired.
- **Module 3:** News Search fully wired.
- **Module 4:** PDF Report Generation fully wired.
- **Module 5:** Admin Dashboard fully wired — stats, charts, activity tables at `/admin` (admin-only).
- **This update: Report History.** A new `/reports` page lists every report you've generated (title, keyword, language, newspaper, edition, article count, date) with a re-download button for each — closing the gap the Module 4/5 READMEs flagged as remaining polish.

## Setup

```bash
cd frontend
npm install
cp .env.example .env      # points VITE_API_BASE_URL at the backend

npm run dev
```

Runs at http://localhost:5173. Requires the backend running at
http://localhost:8000 (see backend/README.md).

## How to test the auth flow

1. Go to `/register`, create an account — you're signed in immediately and land on `/dashboard`.
2. Refresh the page — you should stay logged in (token is validated against `/auth/me` on load).
3. Click **Sign out** — you're returned to `/login`.
4. Try visiting `/dashboard` directly while signed out — you're bounced to `/login`.
5. Log back in with **"Keep me signed in"** checked, then close and reopen the tab — you should still be signed in (token persisted in `localStorage` instead of `sessionStorage`).
6. Try `/forgot-password` with your email, then check the **backend terminal** for the logged reset link if SMTP isn't configured, and use it to land on `/reset-password?token=...`.
7. On the Dashboard, search "steel" — you should see real, current news articles (via the Google News RSS fallback if no API keys are set on the backend).
8. Click a predefined tag (e.g. "RINL") — it searches for that tag immediately.
9. Add a custom tag, refresh the page, confirm it's still there (it's stored server-side per your account), then delete it.
10. Pick a specific newspaper — the edition dropdown should populate with that paper's editions.
11. Select a couple of articles via their checkboxes — "Generate Report" should become enabled and show a count.
12. Click "Generate Report" — after a moment, a PDF should download automatically, and a green success message should appear showing how many articles were included. Open the PDF and confirm it looks professional: cover page with keyword/language/newspaper/edition, each article with source/date, header/footer, and page numbers.
13. Try it again with zero articles selected — the button should be disabled.
14. Promote yourself to admin (see backend/README.md's SQL snippet), sign out and back in, and you should see an "Admin Dashboard" link in the navbar. Click it — you should see real stats, charts, and tables reflecting your own searches/reports.
15. Sign in as a non-admin account and try navigating to `/admin` directly — you should be redirected to `/dashboard`, not shown an error page.
16. Click "Reports" in the navbar (or "View in Report History →" after generating one) — you should see every report you've generated, with a working re-download button on each row.

## Folder structure

```
frontend/
├── src/
│   ├── main.jsx              # React root
│   ├── App.jsx                # Route definitions, wraps app in AuthProvider
│   ├── api/
│   │   ├── client.js         # fetch wrapper — checkHealth(), apiRequest(), ApiError
│   │   ├── auth.js           # register/login/forgotPassword/resetPassword/me/logout calls
│   │   ├── news.js           # searchNews/fetchLanguages/fetchNewspapers/fetchEditions/fetchTags/addTag/deleteTag calls
│   │   ├── reports.js        # generateReport/listReports/downloadReport (authenticated blob download)
│   │   └── admin.js          # fetchAdminDashboard/fetchAdminUsers calls
│   ├── context/
│   │   └── AuthContext.jsx   # session state: user, token, login/register/logout, persistence
│   ├── pages/
│   │   ├── Login.jsx
│   │   ├── Register.jsx
│   │   ├── ForgotPassword.jsx
│   │   ├── ResetPassword.jsx  # landing page for the emailed/logged reset link
│   │   ├── Dashboard.jsx
│   │   ├── Dashboard.css
│   │   ├── ReportsHistory.jsx # /reports — list past reports with re-download
│   │   ├── ReportsHistory.css
│   │   ├── AdminDashboard.jsx # stats, charts, activity tables (admin only)
│   │   └── AdminDashboard.css
│   ├── components/
│   │   ├── auth/
│   │   │   ├── AuthLayout.jsx    # shared split-panel shell for all auth pages
│   │   │   ├── AuthLayout.css
│   │   │   ├── ProtectedRoute.jsx # route guard used by /dashboard
│   │   │   └── AdminRoute.jsx    # route guard used by /admin (requires is_admin)
│   │   ├── admin/
│   │   │   ├── StatCard.jsx      # single overview metric tile
│   │   │   ├── BarChartCard.jsx  # reusable bar chart (recharts)
│   │   │   └── PieChartCard.jsx  # reusable pie chart (recharts)
│   │   └── dashboard/
│   │       ├── Navbar.jsx        # shows signed-in user, real sign-out
│   │       ├── SearchBar.jsx
│   │       ├── TagChips.jsx      # predefined + custom tags, add/delete
│   │       ├── FilterBar.jsx     # cascading language -> newspaper -> edition + date filters (all fetched, nothing hardcoded)
│   │       ├── ArticleCard.jsx   # single article result with checkbox
│   │       └── NewsPanel.jsx     # loading skeletons, error/no-results, pagination
│   └── styles/
│       ├── tokens.css        # design tokens (colors, type, spacing)
│       └── forms.css         # shared input/button styles, incl. form-banner--error
├── index.html
├── package.json
└── vite.config.js
```

## Design direction

Palette and type are deliberately tied to the subject: graphite/steel
tones with a single molten-ember accent, a thin gradient "seam" motif used
under headers, Space Grotesk for display type and Inter for body text.

