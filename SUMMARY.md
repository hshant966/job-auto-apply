# JobAutoApply v3.0 — Project Summary

**Location:** `/root/.openclaw/workspace/job-auto-apply/`  
**Imported:** 2026-04-03  
**Source:** `/tmp/export_extract/job-auto-apply/`

## Stats

| Metric | Value |
|--------|-------|
| Total files | 64+ |
| Source modules | 36 (`.py`) |
| API modules | 12 |
| Portal adapters | 7 |
| Browser modules | 10 |
| AI modules | 4 |
| Templates | 6 |
| Prompt files | 3 |
| Test files | 1 |

## Tech Stack

- **Language:** Python 3
- **Web framework:** FastAPI + Uvicorn + Jinja2
- **Browser automation:** Playwright (async) with Stealth v3 (20+ detection vectors)
- **Database:** SQLite (built-in)
- **AI:** Multi-provider (OpenRouter, Anthropic, OpenAI, custom OpenAI-compatible)
- **OCR:** Tesseract (text CAPTCHA solving) with image preprocessing
- **Notifications:** Telegram bot

## Architecture

```
run.py  (entry point → FastAPI app on :8000)
├── src/api/          → 12 route modules (auth, profile, jobs, apply, browser, ai, dashboard, portals, settings, learning, radar, resume)
├── src/adapters/     → 7 portal adapters (SSC, UPSC, RRB, IBPS, LinkedIn, Naukri, Indeed)
├── src/ai/           → brain.py (multi-provider AI), radar_scanner.py (RSS discovery), self_learning.py (failure analysis), resume_optimizer.py (ATS scoring)
├── src/browser/      → Playwright manager, stealth v3, fingerprint profiles, TLS fingerprint, image preprocessing, form filler, CAPTCHA solver, navigation helper, session persistence, proxy rotator
├── src/core/         → config, database (SQLite), Pydantic models, encryption
├── src/dashboard/    → Jinja2 templates + CSS for web UI
├── prompts/          → Role execution prompts, engineering guide, templates
├── research/         → 5 research docs (portal analysis, anti-bot strategies)
└── tests/            → pytest suite
```

## Key Features

1. **7 Indian job portals** — government (SSC, UPSC, RRB, IBPS) + private (LinkedIn, Naukri, Indeed)
2. **Stealth v3** — 20+ detection vectors patched, fingerprint profiles, TLS fingerprint spoofing, human interaction simulation
3. **4-strategy CAPTCHA solver** — OCR, AI vision, paid services, manual fallback with image preprocessing
4. **Resume optimizer** — ATS scoring, keyword matching, PDF/DOCX parsing, per-job tailoring
5. **Radar scanner** — Multi-source RSS feed job discovery with deduplication
6. **Self-learning engine** — Failure analysis, strategy adjustment, learning reports
7. **Session persistence** — Encrypted cookie storage, automatic session restore
8. **Navigation helper** — Popup handling, retry logic, smart element-aware waits
9. **AI-powered matching** — Profile-job scoring, cover letter generation, screening Q&A
10. **Web dashboard** — Stats, job browser, application tracker, settings with dark/light theme
11. **Prompt engineering** — Role execution prompts, reusable templates, engineering guide
12. **Security hardening** — Auth enforcement, random secrets, localhost binding, settings validation

## Setup Requirements

- Python 3, `pip install -r requirements.txt`
- Playwright: `playwright install chromium`
- Copy `.env.example` → `.env` and configure API keys + portal credentials
- Run: `python3 run.py` → http://localhost:8000
