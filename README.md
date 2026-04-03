# JobAutoApply v3.0

**AI-Powered Job Application Automation for India**

Automate job applications across 7 portals — SSC, UPSC, RRB, IBPS, LinkedIn, Naukri, Indeed — with AI-powered matching, ATS resume optimization, stealth browser automation, and self-learning intelligence.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy and edit config
cp .env.example .env
# Edit .env with your API keys and portal credentials

# Start the server
python3 run.py
# Opens at http://localhost:8000
```

## Features

### 🎯 7 Portal Support
- **SSC** (ssc.nic.in) — Government job applications with text CAPTCHA handling
- **UPSC** (upsc.gov.in) — OTR system, live photo capture, exam applications
- **RRB** (rrbcdg.gov.in) — Railway recruitment with form auto-fill
- **IBPS** (ibps.in) — Banking CRP registration and applications
- **LinkedIn** — Easy Apply automation with anti-detection
- **Naukri** — Job search and one-click apply
- **Indeed India** — Job discovery and application

### 🤖 AI Engine
- **Multi-provider**: OpenRouter (free models), Anthropic Claude, OpenAI, or any custom endpoint
- **Job matching**: AI-powered profile-job scoring with local fallback
- **Cover letters**: Auto-generated tailored cover letters
- **Screening Q&A**: Auto-answer common screening questions
- **Self-learning engine**: Failure analysis, strategy adjustment, and learning reports

### 🛡️ Stealth v3
- **20+ detection vectors patched**: WebDriver flag, `navigator.plugins`, permissions API, iframe contentWindow, Chrome runtime, and more
- **Fingerprint profiles**: Rotating browser/device fingerprint sets (`fingerprint_profiles.py`)
- **TLS fingerprint spoofing**: JA3/JA4 TLS fingerprint randomization (`tls_fingerprint.py`)
- **Human interaction simulation**: Bezier curve mouse movements, variable-speed typing with occasional mistakes, natural scroll patterns

### 🔓 CAPTCHA Solver
- **4-strategy system**: OCR (Tesseract), AI vision, paid services (2Captcha/AntiCaptcha), manual fallback
- **Image preprocessing**: Grayscale, threshold, denoise, deskew, upscale (`image_preprocessing.py`)
- **Strategy chain**: Attempts each solver in order, falls back gracefully

### 📝 Resume Optimizer
- **ATS scoring**: Keyword density analysis, formatting compliance checks
- **Keyword matching**: Extracts required skills from job descriptions, maps to resume
- **PDF/DOCX parsing**: Reads existing resumes in common formats
- **Per-job optimization**: Tailors resume content for each application

### 🔍 Radar Scanner
- **Multi-source discovery**: RSS feed aggregation from multiple job sources
- **Keyword filtering**: Matches against configured search criteria
- **Deduplication**: Prevents duplicate job entries across sources

### 💾 Session Persistence
- **Encrypted cookie storage**: Login sessions saved securely across restarts
- **Session restore**: Automatic re-login on browser launch
- **Multi-portal support**: Independent session management per portal

### 🧭 Navigation Helper
- **Popup handling**: Detects and manages modal dialogs, popups, overlays
- **Retry logic**: Automatic retry on transient failures with exponential backoff
- **Smart waits**: Element-aware waits instead of blind `sleep()`

### ✍️ Prompt Engineering
- **Role execution prompts**: Structured prompts for consistent AI behavior
- **Prompt templates**: Reusable templates for common tasks (matching, cover letters, Q&A)
- **Engineering guide**: Documentation on prompt design and optimization

### 🔒 Security
- **Auth enforcement**: All API endpoints require authentication
- **Random secret keys**: Auto-generated on first run, no hardcoded defaults
- **Localhost-only binding**: Server binds to `127.0.0.1` by default
- **TLS bypass disabled**: No certificate verification skipping
- **Settings validation**: Input sanitization and type checking on all config

### 📊 Web Dashboard
- **Dashboard** — Real-time stats, application status, upcoming deadlines
- **Jobs** — Browse, filter, score, and apply to discovered jobs
- **Applications** — Track all applications with status timeline
- **Profile** — Manage profile with completeness indicator
- **Settings** — Configure AI provider, portal credentials, scan settings
- **Dark/Light theme** — Modern responsive UI

## Architecture

```
job-auto-apply/
├── run.py                          # Entry point
├── requirements.txt                # Dependencies
├── .env.example                    # Configuration template
├── src/
│   ├── api/                        # FastAPI routes (12 modules)
│   │   ├── app.py                  # Main app + lifespan
│   │   ├── auth.py                 # Authentication
│   │   ├── profile.py              # Profile CRUD
│   │   ├── jobs.py                 # Job search & scan
│   │   ├── apply.py                # Application tracking
│   │   ├── browser.py              # Browser control
│   │   ├── ai.py                   # AI analysis
│   │   ├── dashboard.py            # Stats & analytics
│   │   ├── portals.py              # Portal management
│   │   ├── settings.py             # Configuration
│   │   ├── learning.py             # Learning reports
│   │   ├── radar.py                # Radar scanner API
│   │   ├── resume.py               # Resume optimizer API
│   │   └── dashboard_pages.py      # HTML routes
│   ├── adapters/                   # Portal-specific adapters
│   │   ├── base_adapter.py         # Abstract base
│   │   ├── ssc_adapter.py          # SSC
│   │   ├── upsc_adapter.py         # UPSC
│   │   ├── rrb_adapter.py          # RRB
│   │   ├── ibps_adapter.py         # IBPS
│   │   ├── linkedin_adapter.py
│   │   ├── naukri_adapter.py
│   │   └── indeed_adapter.py
│   ├── ai/                         # AI engine
│   │   ├── brain.py                # Multi-provider AI with fallback
│   │   ├── radar_scanner.py        # RSS feed job discovery
│   │   ├── self_learning.py        # Failure analysis & strategy adjustment
│   │   └── resume_optimizer.py     # ATS scoring & keyword matching
│   ├── browser/                    # Browser automation
│   │   ├── browser_manager.py      # Playwright lifecycle
│   │   ├── stealth.py              # Anti-detection (20+ vectors)
│   │   ├── fingerprint_profiles.py # Browser fingerprint rotation
│   │   ├── tls_fingerprint.py      # TLS/JA3 fingerprint spoofing
│   │   ├── image_preprocessing.py  # CAPTCHA image enhancement
│   │   ├── form_filler.py          # Form auto-fill
│   │   ├── captcha_handler.py      # 4-strategy CAPTCHA solver
│   │   ├── navigation_helper.py    # Popup handling, retries, smart waits
│   │   ├── session_persistence.py  # Encrypted session/cookie storage
│   │   └── proxy_rotator.py        # Proxy rotation
│   ├── core/                       # Core modules
│   │   ├── config.py               # Configuration
│   │   ├── database.py             # SQLite operations
│   │   ├── models.py               # Pydantic models
│   │   └── encryption.py           # Data encryption
│   └── dashboard/                  # Web UI
│       ├── static/style.css        # Styles
│       └── templates/              # Jinja2 templates
├── prompts/                        # Prompt engineering
│   ├── role-execution.md           # Role-specific execution prompts
│   ├── prompt-engineering-guide.md # Prompt design documentation
│   └── templates/                  # Reusable prompt templates
└── tests/                          # Test suite
```

## Configuration

### Environment Variables (.env)

```bash
# AI Provider (openrouter | anthropic | openai | custom)
AI_PROVIDER=openrouter
OPENROUTER_API_KEY=your-key-here
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Browser Settings
HEADLESS=true
STEALTH_ENABLED=true

# Scan Settings
SCAN_INTERVAL_MINUTES=120
MAX_APPLICATIONS_PER_RUN=10
MIN_MATCH_SCORE=40

# Server (binds to localhost by default for security)
HOST=127.0.0.1
PORT=8000
```

### Portal Credentials

Add portal credentials via the web UI (Settings → Portal Credentials) or configure in the database.

## API Endpoints

| Module | Endpoint | Description |
|--------|----------|-------------|
| Auth | POST /api/auth/login | Login |
| Profile | GET/PUT /api/profile/ | Profile CRUD |
| Jobs | GET /api/jobs/ | List jobs |
| Jobs | POST /api/jobs/scan | Scan all portals |
| Apply | POST /api/apply/{job_id} | Start application |
| Browser | POST /api/browser/launch | Launch browser |
| AI | POST /api/ai/match | Score job match |
| AI | POST /api/ai/optimize-resume | Optimize resume |
| Resume | POST /api/resume/optimize | ATS optimization |
| Radar | GET /api/radar/scan | Trigger radar scan |
| Learning | GET /api/learning/reports | Learning reports |
| Dashboard | GET /api/dashboard/stats | Get statistics |
| Portals | GET /api/portals/list | List portals |
| Settings | GET/PUT /api/settings/ | Manage settings |

## Testing

```bash
python3 -m pytest tests/ -v
```

## License

Private project. All rights reserved.
