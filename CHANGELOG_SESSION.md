# QuantLab – Session Changelog

This file tracks all changes made during this development session.

---

## Prompt 1 — BSM Sensitivity Graphs + Terminal Distribution Integration

**Date:** 2026-10-03

### Summary
Integrated four BSM parameter-sensitivity graphs and a stock terminal-price distribution histogram into the existing Option Pricing page. Users now see a comprehensive analysis of any European option — theoretical price, Greeks, sensitivity to each parameter, and the simulated distribution of the underlying stock's terminal price — all from a single form submission.

### Files Modified

#### `server/app.py`
- **Added** `POST /api/options/bsm/sensitivity` endpoint — calls `bsm_price_vs_strike`, `bsm_price_vs_time`, `bsm_price_vs_rate`, and `bsm_price_vs_vol` concurrently (4 threads) and returns all four parameter sweeps in one response.
- **Added** `POST /api/options/bsm/terminal` endpoint — calls `sim_stock.sim_stock_terminal()` with the option's ticker/horizon, computes histogram bins, and returns edges, frequencies, and summary statistics (mean, median, p05, p95).

#### `server/templates/options.html`
- **Added** a "Terminal simulations" `<select>` dropdown to the form with options matching the simulation page (10k – 1M).
- **Added** `#sensitivity-section` with four `<canvas>` elements in a 2×2 `.sensitivity-grid` for the sensitivity charts.
- **Added** `#terminal-section` with summary stats, and a `<canvas>` histogram for terminal-price distribution.
- **Updated** intro text and metadata to reflect the new analysis capabilities.

#### `server/static/options.js`
- **Rewrote** to add `fetchExtras()` which fires both `/api/options/bsm/sensitivity` and `/api/options/bsm/terminal` in parallel alongside every pricing action (BSM-only, BSM+MC, convergence).
- **Added** `renderSensitivity(data)` — creates four Chart.js line charts (price vs. strike, time, rate, vol) using a shared `makeSensChart()` helper.
- **Added** `renderTerminal(data)` — renders summary stat cards and a histogram of simulated terminal prices.
- All existing functionality (BSM pricing, Monte Carlo, convergence plot) is preserved unchanged.

#### `server/static/app.css`
- **Added** `.sensitivity-grid` — 2×2 CSS grid for the four sensitivity charts.
- **Added** section heading styles for `#sensitivity-section` and `#terminal-section` matching the existing design system.
- **Added** responsive rule to collapse sensitivity grid to single-column on screens ≤ 640px.

### Architecture Decisions
- **Parallel execution:** Both backend (ThreadPoolExecutor for 4 BSM functions) and frontend (Promise.all for sensitivity + terminal alongside pricing) use concurrency to minimise total latency.
- **Separate endpoints:** Sensitivity and terminal data are fetched via dedicated endpoints rather than bloating the existing `/api/options/bsm` response. This keeps the API backwards-compatible and allows independent error handling.
- **Non-blocking extras:** If sensitivity or terminal requests fail, the main pricing result still displays — `fetchExtras()` catches errors silently.
- **Reuse of form inputs:** All new features consume the same ticker/strike/horizon/optionType the user already enters, with no additional input required except the terminal simulation count selector.

---

## Prompt 2 — Multi-User Platform: Authentication & User Portfolio Management

**Date:** 2026-10-03

### Summary
Transformed QuantLab into a multi-user platform. Users can create personal accounts, securely log in, and manage their dedicated stock portfolios with live market valuations, cost bases, and unrealized profit/loss tracking. The user portfolio seamlessly connects with Markowitz mean-variance optimization and quantitative risk analytics.

### Files Created & Modified

#### `requirements.txt`
- Added `Flask-Login>=0.6` and `Flask-SQLAlchemy>=3.1`.

#### `server/models.py` (New)
- **`User` model:** Includes `id`, `username`, `email`, `password_hash` (scrypt hash via Werkzeug), `created_at`, and relationship `holdings`.
- **`PortfolioHolding` model:** Tracks per-user positions with `user_id`, `ticker`, `shares`, `buy_price`, `created_at`, and `updated_at`. Enforces `UniqueConstraint('user_id', 'ticker')`. Includes `to_dict()` helper for calculating live market value, cost basis, unrealized P&L, and return percentages.

#### `server/app.py`
- **Auth Configuration:** Initialized Flask-SQLAlchemy with local SQLite database (`quantlab.db`) and Flask-Login `LoginManager`.
- **Auth Routes:**
  - `GET /register`, `POST /register`: Account registration with validation (unique username & email, min 8 char password) and automatic login.
  - `GET /login`, `POST /login`: Credential validation against username or email with "Remember me" cookie support and redirect to `next` URL.
  - `GET /logout`: Terminate session and redirect with confirmation banner.
- **Portfolio Endpoints:**
  - `GET /portfolio`: Protected route (`@login_required`) serving the portfolio dashboard.
  - `GET /api/portfolio/holdings`: Returns user-specific holdings, live market valuations (concurrently fetched via yfinance), total portfolio value, total cost basis, unrealized P&L ($ and %), and calculated asset weights.
  - `POST /api/portfolio/holdings`: Adds a new stock position or increments shares and recalculates weighted average cost basis.
  - `PUT /api/portfolio/holdings/<id>`: Updates position shares or buy price with user ownership validation.
  - `DELETE /api/portfolio/holdings/<id>`: Removes position with user ownership validation.
  - `POST /api/portfolio/apply-allocation`: Converts Markowitz optimal allocations ($) into stock shares and saves/adds them directly to the user's portfolio.

#### `server/templates/base.html`
- Added dynamic navigation showing `👤 username` + `Log out` when authenticated, or `Log in` and `Sign up` links when logged out.
- **Hidden navbar on auth routes:** The `<nav>` with module links (`Stock simulation`, `Option pricing`, `Portfolio`, `Risk analytics`) is automatically hidden on `/login` and `/register`, presenting a clean, focused header with only the brand logo and the contextual auth action (`Sign up` on login, `Log in` on sign-up).
- Added global flash message alerts bar (`.flash-bar`, `.flash-success`, `.flash-error`, `.flash-info`).

#### `server/templates/login.html` & `server/templates/register.html` (New)
- Neo-modernist authentication cards with clean form inputs, validation error alerts, and cross-links.

#### `server/templates/portfolio.html`
- Transformed from a standalone calculator into a dual-purpose dashboard:
  1. **My Portfolio Holdings:** KPI cards (Portfolio Value, Cost Basis, Unrealized P&L, Active Positions), Add Position form, interactive Holdings Table with weight progress bars, live prices, P&L, and edit/delete actions.
  2. **Markowitz Optimiser:** Pre-load portfolio stocks button, budget, required return slider, and results panel with "Save Allocation as My Portfolio" action.
  3. **Edit Position Modal:** Inline editing for shares and cost basis.

#### `server/static/portfolio.js`
- Full asynchronous frontend management for user portfolio holdings, CRUD actions, live formatting, modal management, and two-way integration with the Markowitz optimizer.

#### `server/templates/risk.html` & `server/static/risk.js`
- Added "⚡ Import my portfolio" button to automatically load the user's active holdings, weights, and portfolio value directly into the Risk Analytics tool.

#### `server/static/app.css`
- Added styles for authentication forms, flash message bars, data tables (`.data-table`), financial metric cells (`.num-cell`, `.pnl-pos`, `.pnl-neg`), weight bars, and modal backdrops adhering strictly to the Swiss editorial × financial terminal design system.

#### `server/test_portfolio_auth.py` (New)
- Automated integration test suite verifying user registration, login redirects, portfolio CRUD operations, user isolation (User A cannot access or delete User B's positions), and Markowitz allocation saving.

