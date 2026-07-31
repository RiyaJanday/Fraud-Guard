# FraudGuard — AI-Powered Real-Time Credit Card Fraud Detection System

A premium, production-quality fintech dashboard frontend built with React (Vite), Tailwind CSS,
Chart.js, Framer Motion and a full glassmorphic dark UI system.

## Tech Stack

- **React 19 + Vite** — app shell and build tooling
- **Tailwind CSS 3** — utility-first styling, custom design tokens in `tailwind.config.js`
- **Chart.js + react-chartjs-2** — Volume line chart, Fraud doughnut, Risk area chart, Model radar chart
- **Axios** — API client (`src/lib/api.js`), ready to point at a real backend
- **React Router 7** — routing across all 11 pages
- **Framer Motion** — page transitions, hover states, staggered reveals, gauges
- **Lucide React** — icon set
- **React Hot Toast** — live fraud alert notifications
- **React CountUp** — animated stat counters
- **TanStack Table** — sortable, paginated transaction tables
- **React Hook Form + Zod** — validated forms (Login, Register, Settings)
- **tailwindcss-animate** — small animation utilities

## Getting Started

```bash
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). Login / Register accept any input —
this build ships with realistic mock data (`src/data/mockData.js`) so every screen is fully
explorable without a backend.

To connect a real backend, set `VITE_API_BASE_URL` in a `.env` file (see `.env.example`) and wire
up the calls already scaffolded in `src/lib/api.js` (`fraudApi.getStats`, `getTransactions`, etc.).

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
  context/          AuthContext (mock auth, swap for real JWT/session flow)
  data/             mockData.js — deterministic mock generators
  lib/              api.js, chartSetup.js, utils.js
```

## Pages

1. **Landing** — marketing page with animated hero risk gauge, feature grid, stats
2. **Login / Register** — validated auth forms with glassmorphic cards
3. **Dashboard** — top stats, 6 chart types, heatmap, recent transactions, alerts, SHAP snapshot
4. **Transactions** — searchable, filterable, sortable transaction table with detail drawer
5. **Live Monitoring** — simulated real-time transaction stream with toast alerts
6. **Fraud Analytics** — merchant risk, geography, trend breakdowns
7. **Explainability (SHAP)** — global feature importance + per-transaction explanations
8. **Reports** — filterable report library with download actions
9. **Settings** — tabbed settings (general, security, notifications, API keys, team)
10. **Profile** — analyst profile, stats, recent activity

## Notes for Production

- Replace `src/context/AuthContext.jsx` mock login/register with real API calls.
- Replace `src/data/mockData.js` generators with `fraudApi` calls in each page.
- All colors, spacing and radii are centralized in `tailwind.config.js` — update the palette
  there to re-theme the whole app.
