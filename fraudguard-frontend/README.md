# FraudGuard — Frontend

The dashboard UI for FraudGuard: a premium, glassmorphic dark-mode fintech
frontend built with React (Vite) and Tailwind CSS, fully wired to the real
FastAPI backend — no mock data left in the running app.

**Live:** https://fraud-guard-kappa.vercel.app

## Tech Stack

- **React 19 + Vite** — app shell and build tooling
- **Tailwind CSS 3** — utility-first styling, custom design tokens in `tailwind.config.js`
- **Chart.js + react-chartjs-2** — Volume line chart, Fraud doughnut, Risk trend, Model performance radar, heatmap
- **Axios** — API client (`src/lib/api.js`), talks to the real backend
- **React Router 7** — routing across all pages
- **Framer Motion** — page transitions, hover states, staggered reveals, gauges
- **Lucide React** — icon set
- **React Hot Toast** — live fraud alert notifications (driven by a real WebSocket feed)
- **React CountUp** — animated stat counters
- **TanStack Table** — sortable, paginated transaction tables
- **React Hook Form + Zod** — validated forms (Login, Register, Settings)
- **tailwindcss-animate** — small animation utilities

## Getting Started

```bash
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173).

You need a running backend for the app to be useful — see the project root's
[`LOCAL_RUN.md`](../LOCAL_RUN.md) to boot the full stack, or point
`VITE_API_BASE_URL` (in a `.env` file — see `.env.example`) at the deployed
backend if you just want to browse the UI against real live data.

## Build

```bash
npm run build
npm run preview
```

## Project Structure

```
src/
  components/
    layout/        Sidebar, Topbar, DashboardLayout, ProtectedRoute
    ui/             GlassCard, StatCard, Badge, RiskGauge, PageHeader, GradientBlobs
    charts/         VolumeLineChart, FraudDoughnutChart, RiskAreaChart,
                     PerformanceRadarChart, FraudHeatmap, RiskTimelineChart
    transactions/   TransactionTable, TransactionDrawer, StatusBadge
    dashboard/      AlertsPanel, NotificationsPanel
  pages/            Landing, Login, Register, Dashboard, Transactions,
                     LiveMonitoring, FraudAnalytics, Explainability,
                     Reports, Settings, Profile
  context/          AuthContext — real JWT auth (login/register/logout,
                     token refresh, cached user, updateUser for in-place
                     profile edits)
  data/             mockData.js — leftover from early UI-only development;
                     no longer imported anywhere, safe to delete
  lib/              api.js (fraudApi — every real backend call, plus
                     getApiErrorMessage for the backend's error envelope),
                     transform.js (maps backend response shapes to what the
                     UI components expect), chartSetup.js, utils.js
```

## Pages

All pages below call `fraudApi` and render real backend data — none are
placeholder/mock.

1. **Landing** — marketing page with animated hero risk gauge, feature grid, stats
2. **Login / Register** — real JWT auth, RBAC-aware
3. **Dashboard** — real aggregate stats (with real week-over-week deltas), 6 chart types, heatmap, recent transactions, alerts
4. **Transactions** — searchable, filterable, sortable transaction table with detail drawer, backed by real pagination
5. **Live Monitoring** — real-time transaction stream over a WebSocket connection, with toast alerts
6. **Fraud Analytics** — real merchant risk, decision distribution, trend breakdowns
7. **Explainability (SHAP)** — real global feature importance + real per-transaction SHAP explanations
8. **Reports** — real PDF/CSV export, generated on request from live data
9. **Settings** — real password change, real notification preferences, real team management (Admin only — invite/activate/deactivate users)
10. **Profile** — real review-queue stats and resolved-case activity history

## Notes

- `src/context/AuthContext.jsx` exposes `updateUser(partial)` so any page
  that edits the profile (currently just Settings) can update the cached
  user without a full re-fetch — Topbar/Profile pick up the change immediately.
- Backend error responses are shaped `{ error: { code, message } }`, not
  FastAPI's default `{ detail }`. Always read errors via
  `getApiErrorMessage(err)` from `lib/api.js` rather than
  `err.response.data.detail` directly.
- All colors, spacing and radii are centralized in `tailwind.config.js` —
  update the palette there to re-theme the whole app.
