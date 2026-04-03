# Ultra Deep Research — Job Portal Automation

## SSC (ssc.nic.in)
- **Registration**: Online via ssc.nic.in, requires basic details + photo/signature upload
- **Photo specs**: Passport size, JPEG, 20KB-50KB
- **Application flow**: Register → Login → Select exam → Fill form → Upload docs → Pay fee → Submit
- **Captcha**: Text-based CAPTCHA on login/registration pages
- **Form fields**: Name, DOB, Father's name, Category, Education, Address, Photo, Signature
- **Anti-bot**: Session-based, some IP rate limiting
- **Key URLs**: ssc.nic.in/Portal, ssc.nic.in/Login

## UPSC (upsc.gov.in)
- **OTR (One Time Registration)**: New system at otr.pariksha.nic.in
  - 2026: OLD OTR module discontinued, new OTR system introduced
  - Personal details entered ONCE, stored permanently
  - Photo & Signature uploaded once via OTR
  - **Live Photo Capture** required for CAF (Common Application Form) in 2026
- **Application flow**: OTR → Select exam → Fill CAF → Auto-prefilled from OTR → Pay → Submit
- **Photo specs**: Must be recent, specific dimensions, live capture for 2026
- **Captcha**: Yes, on OTR and application pages
- **Anti-bot**: Moderate — session-based, may have JS challenges

## RRB (indianrailways.gov.in)
- **Portal**: rrbcdg.gov.in or regional RRB sites
- **Application flow**: Register → OTP verification → Login → Select post → Fill form → Upload docs → Pay
- **Form fields**: Personal, Education, Community, Domicile, Photo, Signature
- **Captcha**: Text-based + numeric
- **Photo specs**: JPEG, 20-50KB, specific dimensions
- **Anti-bot**: Basic session management, IP-based rate limiting

## IBPS (ibps.in)
- **Portal**: ibps.in → CRP (Common Recruitment Process)
- **Application flow**: Register → Login → Select CRP → Fill form → Upload photo/signature/thumb → Pay → Submit
- **Captcha**: reCAPTCHA v2 (select images)
- **Form fields**: Personal, Education, Experience, Preferences (bank/region choices)
- **Photo**: 4.5cm x 3.5cm, 20-50KB JPEG
- **Signature**: Scanned, 10-20KB JPEG
- **Thumb impression**: Required for some exams
- **Anti-bot**: reCAPTCHA + session management

## LinkedIn
- **Easy Apply**: One-click apply with stored profile data
- **Job search**: Can scrape job listings via search URLs
- **Anti-bot**: VERY aggressive
  - Rate limiting on requests
  - Browser fingerprinting
  - Session validation
  - CAPTCHA on suspicious activity
  - Account lockouts for automation
- **Best practices**: 
  - Use persistent browser profiles (cookies)
  - Human-like delays (30-120s between actions)
  - Randomized mouse movements
  - Limit to 50-100 applications/day
  - Use residential proxies

## Naukri
- **Job search**: API-like endpoints for search results
- **Application**: "Apply" button with stored profile
- **Anti-bot**: Moderate
  - Session-based auth
  - Some rate limiting
  - Mobile OTP verification for sensitive actions
- **Scraping**: Search results loadable via API with proper headers

## Indeed India
- **Application**: Varies by employer — some redirect to external sites
- **Anti-bot**: Moderate — Cloudflare protection
- **Best practices**: Use persistent sessions, respect robots.txt

---

## Anti-Bot Strategies (2026)
### Detection Methods
1. **TLS fingerprinting** (JA3/JA4): Analyzes TLS handshake cipher suites
2. **Browser fingerprinting**: Canvas, WebGL, Audio context, fonts
3. **WebDriver detection**: `navigator.webdriver` flag
4. **Behavioral analysis**: Mouse movements, typing patterns, scroll behavior
5. **IP reputation**: Datacenter vs residential IPs
6. **Rate limiting**: Requests per minute/hour/day
7. **CAPTCHA**: reCAPTCHA v2/v3, hCaptcha, text-based

### Bypass Techniques (2026)
1. **Playwright stealth**: 
   - Override `navigator.webdriver` to false
   - Randomize canvas/WebGL fingerprints
   - Use real Chrome user agents
   - Bezier curve mouse movements
   - Human-like typing with random delays
2. **TLS fingerprint masking**: 
   - Route through real browser (not raw HTTP)
   - Use `--disable-blink-features=AutomationControlled`
3. **Residential proxies**: Rotate IPs from real ISPs
4. **Session persistence**: Reuse cookies across runs
5. **Behavioral simulation**:
   - Random scroll patterns
   - Varying click positions (±5px offset)
   - Natural reading pauses (2-5s)
   - Occasional "mistakes" and corrections

### CAPTCHA Solving
1. **reCAPTCHA v2**: 2Captcha, Anti-Captcha, CapMonster services
2. **reCAPTCHA v3**: Score-based, harder to bypass — use residential IPs + good fingerprints
3. **hCaptcha**: 2Captcha, CapSolver
4. **Text CAPTCHA**: OCR (Tesseract) or AI vision models
5. **Playwright-reCAPTCHA**: Python library for direct solving

---

## Key Implementation Notes
- Use Playwright (NOT Selenium) for all browser automation
- Persistent browser profiles per portal (separate user data dirs)
- Configurable AI backend: OpenRouter (free models), Claude, OpenAI
- FastAPI for web interface
- SQLite for data storage (lightweight, no external DB needed)
- Telegram bot for notifications
- All sensitive data encrypted at rest
