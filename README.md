# PIPE

**P**lataforma **I**nteligente **P**essoal **e** Expansível — *Personal Intelligent and Expandable Platform*.

A modular personal web platform built with Flask: an AI assistant that operates on real data, an encrypted password vault with a Chrome extension, and 12 on-demand modules behind one interface. The name is both an acronym and the author's surname (Felipe → Pipe).

[![Version](https://img.shields.io/badge/version-1.8.25-E8A33D)](CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/tests-434-2EA44F?logo=pytest&logoColor=white)](#testing)
[![Deployed](https://img.shields.io/badge/deployed-PythonAnywhere-1C7ED6)](https://felipejn.pythonanywhere.com)

**▶ [Live demo](https://felipejn.pythonanywhere.com)** · **[Changelog](CHANGELOG.md)** · **[Project status](Estado_Atual.md)** · **[Chrome extension guide](docs/guia-extensao-chrome.md)**

---

## Table of contents

- [Overview](#overview)
- [Highlights](#highlights)
- [Features](#features)
  - [Module store](#module-store)
  - [Spotlight: encrypted password vault](#spotlight-encrypted-password-vault)
  - [Spotlight: AI assistant with tool use](#spotlight-ai-assistant-with-tool-use)
  - [Spotlight: weather with offline fallback](#spotlight-weather-with-offline-fallback)
  - [Spotlight: privacy-preserving sharing](#spotlight-privacy-preserving-sharing)
- [Cross-cutting platform features](#cross-cutting-platform-features)
- [Security](#security)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Testing](#testing)
- [Getting started](#getting-started)
- [Deployment](#deployment)
- [Project documentation](#project-documentation)

---

## Overview

- **12 modules, one codebase** — tasks, notes, calendar, AI assistant, password vault, weather, fuel prices, currency exchange, file conversions and more, activated per-user at runtime.
- **Production system, not a toy** — deployed on PythonAnywhere with daily scheduled jobs, API-based e-mail delivery (Zoho Mail OAuth 2.0), Telegram notifications and database migrations.
- **Security is a first-class feature** — AES-256-GCM vault, PBKDF2 (600k iterations), 2FA (TOTP / Telegram / email), CSRF, rate limiting, CSP/HSTS and per-user data isolation.
- **AI that reads and writes your data** — an OpenRouter-powered assistant with 19 tools (8 read-only, 11 write), deterministic guardrails and timezone-correct reasoning.
- **Ships with tests** — 434 automated tests with a hard safeguard that prevents any test from touching the production database.

PIPE started as a practical Flask exercise and grew into a portfolio piece: the architecture is designed so new modules plug in without touching existing ones (blueprint + manifest entry + optional dashboard provider).

---

## Highlights

| | |
|---|---|
| 🧩 **12 on-demand modules** | Enabled/disabled per user from the in-app Module Store |
| 🤖 **AI assistant** | 19 tools over tasks, notes, events, fuel, weather, exchange rates |
| 🔐 **Password vault** | AES-256-GCM + PBKDF2 600k; key lives only in server-side session |
| 🌐 **Chrome extension** | Manifest V3 — autofill from the vault, capture only on login forms |
| 🔔 **Multi-channel notifications** | Telegram + Zoho Mail (OAuth 2.0), per-user preferences |
| 📱 **PWA** | Manifest + service worker, dark/light themes, offline shell |
| 🕖 **Daily scheduled job** | EuroMillions results, task deadlines, calendar reminders, fuel prices |
| ✅ **434 tests** | In-memory SQLite fixtures; `drop_all()` blocked against file databases |

---

## Features

| Module | What it does |
|---|---|
| 🎯 **EuroMillions** | Register draws, verify results automatically against a public API, historical frequency analysis, notifications per draw |
| ✅ **Tasks** | Lists with emoji icons, priorities, deadlines, labels, real-time search, overdue notifications (daily until done) |
| 📝 **Notes** | Google-Keep-style colour cards (8 colours), checklists, labels, pin/archive, real-time search |
| 🔑 **Passwords** | Cryptographic password/passphrase/PIN generator **and** an encrypted vault with Chrome autofill |
| 📅 **Calendar** | Monthly + agenda views, colour-coded events, reminders the day before and on the day |
| 🌤️ **Weather** | Open-Meteo forecast (hourly 24h + 7 days) for your saved location — no API key required |
| ⛽ **Fuel prices** | Portuguese station prices (API Aberta) for your chosen municipalities, refreshed by scheduled job, staleness/archiving rules |
| ☀️ **Daily digest** | Deterministic + LLM-written summary of your day, sent to Telegram at 07:00 |
| 🤖 **AI assistant** | Natural-language interface over every module (see [spotlight](#spotlight-ai-assistant-with-tool-use)) |
| 💱 **Currency** | Real-time conversion via Wise API v3 with ExchangeRate-API fallback |
| 🎨 **Colours** | HEX/RGB/HSL/CMYK converter that emits Flutter code in both directions |
| 🔄 **File conversions** | HEIC→JPG and PNG/JPG→ICO, in-memory (nothing written to disk), ZIP batching |

### Module store

Modules are **opt-in per user**. The store (`/modulos/loja`) toggles modules at runtime; the dashboard queries a provider registry and renders a metrics summary for each active module — adding a new module means one blueprint, one manifest entry and an optional dashboard provider, with no changes to existing code.

### Spotlight: encrypted password vault

- **AES-256-GCM** encryption with the key derived from the master password via **PBKDF2-SHA256 (600,000 iterations)**; master password verified with bcrypt.
- The encryption key **never reaches the browser** — it lives only in a server-side session (Flask-Session) and expires after 15 minutes, locking just the vault, not the login session.
- Entries deduplicated per normalised domain, Chrome CSV import, entropy-based strength meter, full per-user query isolation (anti-IDOR).
- **Chrome extension (MV3)**: popup to unlock/list/fill credentials; content script captures credentials **only on login forms** and never on the app itself; CORS locked to the extension's ID; pending captures expire after 15 minutes.
- Docs: [`docs/guia-extensao-chrome.md`](docs/guia-extensao-chrome.md) · [`chrome-extension/README.md`](chrome-extension/README.md)

### Spotlight: AI assistant with tool use

- **19 tools** — 8 read-only (`get_tarefas`, `get_notas`, `get_eventos`, `get_euromilhoes`, `get_cambio`, `get_combustiveis`, `get_meteorologia`, `get_resumo_geral`) and 11 write (create/update/delete tasks, notes and events; credential generation).
- **OpenRouter** with a free-model fallback chain and explicit classification of provider errors (a `200` body can still carry an error).
- **Deterministic guardrails**: weekly-agenda answers are computed from the database, not the model; weather questions must call the tool first — no numbers may be invented; messages over 3,000 characters are rejected.
- **Timezone-correct**: temporal context is computed in `Europe/Lisbon`, so "tomorrow" resolves correctly even on a UTC server.
- Reading mode vs. writing mode toggle, session-scoped history (10 exchanges), rate-limited at 30 msg/min.

### Spotlight: weather with offline fallback

Open-Meteo geocoding + forecast (no API key). When the API is down, the app serves the **last successful forecast up to 24 h old** from its own cache table, clearly flagged as cached — the assistant and daily digest share the same fallback.

### Spotlight: privacy-preserving sharing

Tasks, notes and events can be shared with another user **by e-mail address only** — there is no user directory or listing, so anonymity is preserved. Accepted shares carry a permission level (read/edit) and every route enforces owner-or-share access.

---

## Cross-cutting platform features

- **Registration by invitation only** — unique tokens, 7-day expiry, use counter; admin console to manage invites and accounts.
- **2FA (optional)** — TOTP (Google Authenticator/Authy), Telegram and e-mail, configurable **simultaneously**; the user picks a method at login.
- **Notifications** — per-channel preferences; Telegram Bot API and Zoho Mail (OAuth 2.0 token refresh with on-disk cache); failure reasons surfaced in the UI with actionable advice.
- **Scheduled job** — one PythonAnywhere task at 07:00 handles EuroMillions results (Tue/Fri), task deadlines (daily), calendar reminders (daily) and fuel-price refresh (Tue).
- **Dashboard** — hybrid card grid fed by a provider registry (per-module metrics, SQL-only rendering, no external HTTP), with automatic fallback to the classic layout.
- **PWA** — manifest, service worker (network-first shell), installable icons, dark/light theme with anti-FOUC script.

---

## Security

| Measure | Implementation |
|---|---|
| CSRF | Flask-WTF `CSRFProtect` on every form + `X-CSRFToken` header on AJAX calls |
| Rate limiting | Flask-Limiter on auth, assistant, fuel-update and digest routes (trusted `X-Forwarded-For` for the proxy) |
| Headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP; HSTS when secure cookies are on |
| 2FA | Cryptographically random codes, throttled resend, inactive accounts rejected; TOTP / Telegram / e-mail simultaneously |
| Vault cryptography | AES-256-GCM, PBKDF2-SHA256 **600,000 iterations**, bcrypt master-password check, 15-min vault session timeout |
| Key handling | Encryption key exists **only** in server-side session storage — never in a cookie, never in the browser |
| Data isolation | Every query filtered by `user_id` (anti-IDOR); invite-only registration, admin-gated console |
| Secrets | Production refuses to start without `SECRET_KEY`; development/tests generate ephemeral keys |
| CORS | Vault API restricted to `chrome-extension://<id>` origins; wrong origins get no `Allow-Origin` header |
| Upload limits | Global size/limits on conversions and CSV imports (file count, bytes, rows, image pixels) |
| Audit logging | Failed login attempts logged server-side (e-mail + IP) at warning level |

## Tech stack

| Layer | Technology |
|---|---|
| Framework | Flask 3.1 (Python 3.10+) — app-factory pattern |
| Database | SQLite + Flask-SQLAlchemy; migrations via Flask-Migrate (Alembic) |
| Auth | Flask-Login, Werkzeug password hashing, `pyotp` TOTP, invite-only registration |
| Forms / CSRF | Flask-WTF + WTForms |
| Sessions | Flask-Session (server-side, filesystem) |
| Rate limiting | Flask-Limiter |
| Cryptography | `cryptography` (AES-256-GCM), `bcrypt`, PBKDF2 (hashlib) |
| AI | OpenRouter — chat completions + tool use, free-model fallback chain |
| Integrations | Telegram Bot API · Zoho Mail REST (OAuth 2.0) · Wise FX · Open-Meteo · API Aberta · EuroMillions public API |
| Imaging | Pillow + pillow-heif |
| Frontend | Vanilla HTML/CSS/JS — CSS custom-property design system (dark/light), PWA (manifest + service worker) |
| Tests | pytest (in-memory SQLite fixtures) |
| Hosting | PythonAnywhere (free plan) behind nginx + one daily scheduled task |

## Architecture

```
Browser (PWA, vanilla JS)
        │  fetch + X-CSRFToken
        ▼
create_app() ── security headers · CSRF · rate limiter · module manifest
        ▼
Flask blueprints (one per module: auth, tarefas, notas, calendario,
                  assistente, passwords, meteorologia, combustiveis, …)
        ▼
Services / business rules ──┬──► SQLite (Flask-SQLAlchemy + Flask-Migrate)
                            └──► External APIs (OpenRouter, Telegram, Zoho,
                                 Wise, Open-Meteo, API Aberta)
```

Every module is an independent blueprint: to add one, create the package, register the blueprint, add a manifest entry — the dashboard card appears automatically. Optional per-module dashboard providers plug into a registry loaded at startup.

## Testing

```bash
pytest -q                  # full suite
pytest --collect-only -q   # inventory only
```

- **434 tests across 30 test files** — authentication, vault, sharing, assistant (client, context, tools, editing), weather, fuel dedup/staleness, notifications, daily digest, scheduled jobs, security hardening and the Chrome extension.
- **Guard rail**: `tests/conftest.py` monkey-patches `drop_all()` to raise unless the database URI is `:memory:` — a test can never wipe a real database (an incident from an earlier iteration is documented in the changelog).
- Tests run against ephemeral in-memory SQLite databases created with `create_app('testing')`.

## Getting started

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone
git clone https://github.com/felipejn/pipe-app.git
cd pipe-app

# Virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# Dependencies
pip install -r requirements.txt

# Configuration
cp .env.example .env
# Edit .env and set SECRET_KEY (required — generate with: python -c "import secrets; print(secrets.token_hex(32))")
# Everything else is optional locally — integrations degrade gracefully.

# Database migrations + first admin user
flask --app run db upgrade
python scripts/criar_admin.py
# The script asks for username (internal id), e-mail, first name, surname and
# password. If the username already exists, that account is promoted to admin.

# Run
python run.py
```

The app is available at `http://127.0.0.1:5000`.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | ✅ | Flask secret key — **production refuses to boot without it** |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram notifications + 2FA via Telegram |
| `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` / `ZOHO_REFRESH_TOKEN` / `ZOHO_ACCOUNT_ID` / `ZOHO_FROM_EMAIL` / `ZOHO_DC` | ❌ | Zoho Mail OAuth 2.0 (invites, 2FA e-mail, notifications) |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | ❌ | AI assistant (free-model fallback chain) |
| `WISE_API_KEY` | ❌ | Exchange rates (falls back to ExchangeRate-API without it) |
| `APIABERTA_API_KEY` | ❌ | Fuel prices (anonymous tier works without it) |
| `COFRE_CORS_ORIGINS` | ❌ | Chrome-extension origins allowed to call the vault API |
| `PIPE_PUBLIC_URL` | ❌ | Base URL for links in scheduled-task e-mails |

> Only `SECRET_KEY` is mandatory: without API keys the app still runs, with the corresponding integrations disabled.

## Deployment

Production runs on **PythonAnywhere** (free plan, nginx):

1. `git pull` → `pip install -r requirements.txt` → **Reload**
2. On schema changes: `python scripts/backup_bd.py` → `flask db upgrade` → verify with `flask db current` / `flask db check`
3. One scheduled task runs `scripts/pipe_tasks.py` daily at **07:00**

Full deploy procedures, migrations and known pitfalls are documented in the [CHANGELOG](CHANGELOG.md) and [project status](Estado_Atual.md).

## Project documentation

| Document | Content |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Version history (v1.4.0 → v1.8.25), deploy notes per release, incident write-ups |
| [Estado_Atual.md](Estado_Atual.md) | Living project state: full structure, module reference, deploy runbook |
| [docs/guia-extensao-chrome.md](docs/guia-extensao-chrome.md) | Step-by-step guide for the Chrome vault extension |
| [chrome-extension/README.md](chrome-extension/README.md) | Extension permissions and usage flow |

---

**License:** no license has been declared for this repository — all rights reserved by default.

*PIPE is a personal portfolio project by [felipejn](https://github.com/felipejn). Live: [felipejn.pythonanywhere.com](https://felipejn.pythonanywhere.com)*
