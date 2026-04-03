# Anti-Bot Detection, Captcha Solving & Browser Automation Stealth

> Research document for job-auto-apply project  
> Last updated: 2026-04-03

---

## Table of Contents

1. [Captcha Types in Indian Job Portals](#1-captcha-types-in-indian-job-portals)
2. [Anti-Bot Detection Methods](#2-anti-bot-detection-methods)
3. [Browser Automation Frameworks Comparison](#3-browser-automation-frameworks-comparison)
4. [Proxy & VPN Considerations](#4-proxy--vpn-considerations)
5. [Ethical & Legal Considerations](#5-ethical--legal-considerations)

---

## 1. Captcha Types in Indian Job Portals

### 1.1 reCAPTCHA v2 (Google)

- **How it works:** Checkbox ("I'm not a robot") that escalates to image challenges if suspicious. Uses invisible scoring (reCAPTCHA v3) behind the scenes.
- **Prevalence:** Very common on Naukri, Indeed India, Shine, and many Indian government job portals.
- **Difficulty to bypass:** Medium-High. Google constantly updates detection.
- **Solutions:**
  - **2Captcha** — Human-powered solving, ~$2.99/1000 solves. Average solve time: 15-60 seconds.
  - **Anti-Captcha** — Automated + human hybrid. ~$2.00/1000. Faster API (~10-30s).
  - **CapMonster** — AI-based, local solving. One-time license ~$150-400. Lower cost per solve but accuracy varies (70-90%).
  - **XEvil** — Free/cheap OCR-based solver. Works for simple variants but struggles with complex image grids.

### 1.2 reCAPTCHA v3 (Invisible/Score-based)

- **How it works:** No user interaction. Assigns a risk score (0.0-1.0) based on browsing behavior. Low scores trigger blocking.
- **Prevalence:** Increasingly common on major job portals as it's non-intrusive.
- **Difficulty to bypass:** High. Requires mimicking human behavior, proper browser fingerprinting, and good reputation scores.
- **Solutions:**
  - Achieve high scores through proper stealth browser setup (see Section 2)
  - Use 2Captcha/Anti-Captcha token injection when possible
  - Maintain consistent browsing sessions with realistic mouse movement patterns

### 1.3 hCaptcha

- **How it works:** Similar to reCAPTCHA but privacy-focused. Image selection challenges.
- **Prevalence:** Growing adoption, especially on privacy-conscious sites. Some Indian job portals have switched to hCaptcha.
- **Difficulty to bypass:** Medium. Generally easier than reCAPTCHA.
- **Solutions:**
  - **2Captcha** — Good success rate for hCaptcha.
  - **Anti-Captcha** — Well-supported.
  - **CapMonster** — Decent accuracy.

### 1.4 Custom Image Captchas (Government Portals)

- **How it works:** Simple distorted text/number images. Common on Indian government job portals (UPSC, SSC, Railway Recruitment Board, state-level portals).
- **Prevalence:** Very high on .gov.in and .nic.in domains.
- **Difficulty to bypass:** Low-Medium. Often simple distortion that OCR can handle.
- **Solutions:**
  - **Tesseract OCR** — Open-source, free. Works well for simple distorted text (60-80% accuracy).
  - **EasyOCR** — Python library, better for multi-language captchas including Hindi/Devanagari.
  - **Custom CNN models** — Train on specific portal's captcha images for 90%+ accuracy.
  - **2Captcha** — Reliable fallback for any captcha type.

### 1.5 OTP Verification (SMS/Email)

- **How it works:** One-time password sent to registered mobile number or email for login/signup.
- **Prevalence:** Nearly universal on Indian job portals for account creation and login.
- **Difficulty to bypass:** Cannot be "bypassed" — requires actual phone/email access.
- **Solutions:**
  - **Virtual phone number services:** TextNow, Twilio, Exotel (India-specific), Knowlarity
  - **Email-based OTP:** Use temporary email services or IMAP polling
  - **Pre-authenticated sessions:** Login once manually, save session cookies, reuse
  - **SMS gateway APIs:** Forward OTP programmatically via Twilio/Vonage
  - **Best approach:** Maintain real phone number; use IMAP for email OTPs

### 1.6 Service Comparison Table

| Service | reCAPTCHA v2 | reCAPTCHA v3 | hCaptcha | Custom | Price/1K | Avg Speed |
|---------|-------------|-------------|---------|--------|----------|-----------|
| 2Captcha | ✅ | ✅ | ✅ | ✅ | $2.99 | 15-60s |
| Anti-Captcha | ✅ | ✅ | ✅ | ✅ | $2.00 | 10-30s |
| CapMonster | ✅ | ⚠️ | ✅ | ✅ | License | 5-15s |
| XEvil | ⚠️ | ❌ | ⚠️ | ✅ | Free | <5s |

Legend: ✅ Full support | ⚠️ Partial/variable | ❌ Not supported

---

## 2. Anti-Bot Detection Methods

### 2.1 Browser Fingerprinting

**What it is:** Websites collect a unique "fingerprint" of your browser using various properties (screen resolution, installed fonts, plugins, language settings, timezone, etc.).

**Detection signals:**
- Navigator properties (webdriver flag, plugins array, platform)
- Screen resolution and color depth
- Installed fonts enumeration
- HTTP Accept-Language header consistency with browser locale
- Hardware concurrency and device memory

**Countermeasures:**
```python
# Playwright: Override navigator properties
await page.add_init_script("""
    Object.defineProperty(navigator, 'webdriver', { get: () => false });
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
""")
```

### 2.2 TLS Fingerprinting (JA3/JA4)

**What it is:** The TLS handshake has a unique signature (cipher suite order, extensions, elliptic curves) that identifies the client library (Chrome, curl, Python requests, etc.).

- **JA3** — MD5 hash of TLS Client Hello parameters
- **JA4** — Newer, more granular fingerprint format (replacing JA3)

**Detection signals:**
- Chromium-based browsers have a distinct JA3 fingerprint
- Playwright/Puppeteer may have slightly different TLS fingerprints than regular Chrome
- Python `requests`/`httpx` have different fingerprints than browsers

**Countermeasures:**
- **Use real browser engines** (Playwright, Puppeteer) rather than HTTP clients
- **Patchright** — Patched Playwright that modifies TLS fingerprint to match real Chrome
- **curl-impersonate** — Mimics real browser TLS fingerprints
- **Avoid raw HTTP requests** for protected endpoints — use actual browser instances
- Rotate between different browser versions (Chrome 120, 121, 122, etc.)

### 2.3 WebDriver Detection

**What it is:** Sites check `navigator.webdriver` property, Chrome DevTools Protocol (CDP) indicators, and other automation flags.

**Detection signals:**
```javascript
// Common checks that anti-bot systems perform
navigator.webdriver                           // true in automation
window.cdc_adoQpoasnfa76pfcZLmcfl_Array      // Chrome driver marker
window.cdc_adoQpoasnfa76pfcZLmcfl_Promise    // Chrome driver marker
document.querySelector('[id*="selenium"]')    // Selenium markers
!!window._phantom                              // PhantomJS marker
!!window.callPhantom                           // PhantomJS marker
```

**Countermeasures:**

| Framework | Solution | Effectiveness |
|-----------|----------|---------------|
| Playwright | `chromium.args: ['--disable-blink-features=AutomationControlled']` | Medium |
| Playwright | Patchright (patched Playwright fork) | High |
| Puppeteer | `puppeteer-extra-plugin-stealth` | Medium-High |
| Selenium | `undetected-chromedriver` | High |

### 2.4 Canvas/WebGL Fingerprinting

**What it is:** Websites render invisible canvas/WebGL elements and read the pixel data. Different GPUs and drivers produce subtly different outputs.

**Detection signals:**
- Canvas 2D rendering differences across machines
- WebGL renderer string and vendor
- WebGL parameters (max texture size, etc.)
- AudioContext fingerprinting

**Countermeasures:**
- Use consistent, realistic hardware profiles
- Don't spoof to impossible values (e.g., 0x0 screen resolution)
- **playwright-extra + stealth plugin** patches Canvas/WebGL
- **Patchright** handles these well
- Consider using a real VM with real GPU rather than headless Chrome

### 2.5 Behavioral Analysis

**What it is:** Advanced anti-bot systems analyze user behavior patterns.

**Detection signals:**
- Mouse movement patterns (too perfect or non-existent)
- Typing speed and rhythm (instant text injection vs. human keystrokes)
- Scroll patterns (unnatural scrolling)
- Click precision (perfect center clicks)
- Navigation patterns (too fast between pages, no idle time)

**Countermeasures:**
```python
# Simulate human-like typing with Playwright
import asyncio
import random

async def human_type(page, selector, text):
    for char in text:
        await page.type(selector, char, delay=random.randint(50, 150))
        if random.random() < 0.1:  # Occasional pause
            await asyncio.sleep(random.uniform(0.3, 0.8))

# Simulate mouse movement
async def human_move(page, x, y):
    # Bezier curve movement
    steps = random.randint(10, 25)
    for i in range(steps):
        t = i / steps
        # Add slight randomness
        cx = x * t + random.randint(-5, 5)
        cy = y * t + random.randint(-5, 5)
        await page.mouse.move(cx, cy)
        await asyncio.sleep(random.uniform(0.01, 0.03))
```

**Key behavioral hints:**
- Add random delays between actions (200ms - 2s)
- Move mouse in curved paths, not straight lines
- Occasionally miss-click slightly then correct
- Scroll before filling forms
- Don't navigate faster than a human could

### 2.6 IP Rate Limiting

**What it is:** Blocking or throttling IPs that make too many requests in a short period.

**Detection signals:**
- Request frequency (requests per minute/hour)
- Geographic anomalies (IP hopping across countries)
- Known datacenter IP ranges
- Tor exit node IPs

**Countermeasures:**
- Use residential proxies (see Section 4)
- Implement exponential backoff
- Respect `Retry-After` headers
- Limit to 5-10 requests per minute per target
- Use session persistence (same IP for same session)

### 2.7 Recommended Stealth Stack

**For Python (Recommended):**

```bash
pip install playwright patchright
patchright install chromium
```

```python
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir="/tmp/profile",
        headless=False,  # Headed mode for better stealth
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
        ],
        viewport={"width": 1366, "height": 768},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    )
    # ... automation code
```

**For Node.js:**

```bash
npm install puppeteer-extra puppeteer-extra-plugin-stealth puppeteer
```

```javascript
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--disable-blink-features=AutomationControlled']
});
```

---

## 3. Browser Automation Frameworks Comparison

### 3.1 Playwright (Python/Node.js)

**Pros:**
- Built by Microsoft, actively maintained
- Multi-browser support (Chromium, Firefox, WebKit)
- Excellent auto-waiting mechanisms
- Network interception built-in
- Good stealth with Patchright fork
- Multi-tab, multi-context support
- Strong async support

**Cons:**
- `navigator.webdriver` still set by default (needs Patchright or manual patching)
- Larger binary size
- TLS fingerprint may differ from regular Chrome

**Stealth Score: 7/10 (default) → 9/10 (with Patchright)**

**Best for:** General automation, complex multi-page workflows, network mocking

### 3.2 Selenium (Python) + undetected-chromedriver

**Pros:**
- Most mature ecosystem
- `undetected-chromedriver` is battle-tested
- Wide community support
- Uses real Chrome binary
- Good for existing codebases

**Cons:**
- Slower than Playwright/Puppeteer
- No built-in network interception
- Flaky waits (need explicit waits)
- Selenium Manager can be problematic

**Stealth Score: 8/10 (with undetected-chromedriver)**

**Best for:** Legacy projects, high stealth requirements, sites with aggressive bot detection

### 3.3 Puppeteer (Node.js) + stealth plugin

**Pros:**
- Google-maintained (for Chromium)
- `puppeteer-extra-plugin-stealth` patches many fingerprint vectors
- Lightweight
- Good CDP integration

**Cons:**
- Chrome/Chromium only
- Stealth plugin detection is increasing
- Some stealth patches are becoming outdated (as of 2024-2025)
- TypeScript-heavy documentation

**Stealth Score: 7/10 (with stealth plugin)**

**Best for:** Node.js projects, Chrome-specific automation, lightweight tasks

### 3.4 Comparison Matrix

| Feature | Playwright+Patchright | Selenium+UC | Puppeteer+Stealth |
|---------|----------------------|-------------|-------------------|
| Language | Python, JS/TS, Java, C# | Python, Java, C#, JS | JS/TS only |
| Stealth | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Auto-wait | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Multi-browser | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ (Chrome only) |
| Network intercept | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐ |
| Community | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Active maintenance | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### 3.5 Browser Automation vs API-Based Approaches

**Browser Automation:**
- ✅ Works on any website (no API needed)
- ✅ Can handle JavaScript-rendered content
- ✅ Can interact with complex UI elements
- ❌ Slower, more resource-intensive
- ❌ More detectable
- ❌ Fragile (UI changes break scripts)

**API-Based (Direct HTTP):**
- ✅ Much faster and lighter
- ✅ Easier to scale
- ✅ Less detectable (if TLS fingerprint matches)
- ❌ Need to reverse-engineer API endpoints
- ❌ May not work if API requires auth tokens
- ❌ Can't handle JS-rendered content

**Recommendation for job portals:**
- **Primary:** Browser automation (most portals are JS-heavy, form-based)
- **Secondary:** If API endpoints are discovered (e.g., LinkedIn has undocumented APIs), use direct HTTP with proper headers/tokens
- **Hybrid:** Use browser for login/captcha, then switch to API for bulk operations

---

## 4. Proxy & VPN Considerations

### 4.1 Residential Proxies

**What:** Proxies using real residential IP addresses from ISPs.

**Why needed:** Datacenter IPs are commonly blocked. Residential IPs look like real users.

**Indian Providers:**
- **Bright Data** (formerly Luminati) — Largest pool, includes Indian IPs, $15/GB+
- **Smartproxy** — Good Indian IP coverage, $8.50/GB+
- **IPRoyal** — Budget option, some Indian IPs, $1.75/GB+
- **SOAX** — Flexible targeting, Indian IPs available
- **Oxylabs** — Enterprise-grade, good India coverage

**India-specific considerations:**
- Many Indian job portals are geo-restricted or show different content to Indian IPs
- Indian residential IPs are more expensive than US/EU IPs
- Jio, Airtel, BSNL IP ranges are most trusted by Indian sites

### 4.2 Rotating Proxies

**Strategies:**
- **Per-request rotation:** Each HTTP request uses a different IP. Best for scraping.
- **Per-session rotation:** Same IP for entire session. Best for job applications (looks like a real user).
- **Time-based rotation:** Change IP every N minutes. Good balance.

**Recommendation for job applications:**
```
Use per-session rotation with 10-30 minute session duration.
Rotate IP between sessions, not within a session.
Match IP geolocation to the "location" in your profile.
```

### 4.3 Rate Limiting Best Practices

**Conservative approach (recommended for job portals):**
- Max 5-10 applications per hour per portal
- Random delays between actions: 30s - 5min
- Don't apply to more than 50 jobs per day total
- Take breaks during peak hours (avoid 3-5 AM activity patterns)
- Spread activity across business hours (9 AM - 9 PM IST)

**Detection triggers to avoid:**
- Applying to every job in a category rapidly
- Using the same cover letter for all applications
- No mouse movement / scrolling between actions
- Consistent timing patterns (always exactly 30s between actions)
- Operating outside of normal business hours

### 4.4 Free/Cheap Alternatives

- **Tor:** Avoid — exit nodes are universally blocked
- **Free VPNs:** Avoid — shared IPs, slow, unreliable
- **Browser VPN extensions:** Acceptable for manual use, not automation
- **Datacenter proxies:** OK for low-security sites, blocked by major portals
- **Mobile proxy (4G/5G):** Excellent stealth, rotate via airplane mode toggle

---

## 5. Ethical & Legal Considerations

### 5.1 Terms of Service Implications

**Key issues:**
- Most job portals explicitly prohibit automated access in their ToS
- Violating ToS is **not necessarily illegal** but can result in account bans
- Indian IT Act, 2000 (Section 43) covers unauthorized computer access
- No specific Indian law against web scraping public data

**Risk assessment by portal:**

| Portal | ToS Strictness | Detection Level | Risk of Ban |
|--------|---------------|----------------|-------------|
| Naukri | High | High | High |
| LinkedIn | Very High | Very High | Very High |
| Indeed India | Medium | Medium | Medium |
| Shine | Medium | Medium | Medium |
| Govt portals | Low | Low | Low |
| Foundit | Medium | Medium | Medium |

### 5.2 Rate Limiting Best Practices

**"Polite" automation rules:**
1. **Respect robots.txt** — Check what's allowed before scraping
2. **Identify yourself** — Use a descriptive User-Agent (or at least a normal browser UA)
3. **Limit frequency** — 1 request per 3-5 seconds minimum
4. **Handle errors gracefully** — Back off on 429/503 responses
5. **Don't overload servers** — Peak hours = more caution
6. **Cache aggressively** — Don't re-request data you already have

### 5.3 Data Privacy (Storing Personal Info)

**Indian regulations:**
- **Digital Personal Data Protection Act (DPDPA), 2023** — India's comprehensive data protection law
- Personal data (name, email, phone, resume) requires consent for processing
- Data must be stored securely with reasonable security safeguards
- Right to correction and deletion of personal data

**Best practices for job-auto-apply:**
```
1. Store personal data locally (encrypted) — never transmit to third parties
2. Minimize data collection — only what's needed for applications
3. Use environment variables or encrypted config for sensitive data
4. Implement data retention policy — delete old application records
5. Don't log personal information in plain text
6. Use .env files (excluded from version control) for credentials
```

**Storage recommendations:**
- Resume files: Local encrypted storage
- Credentials: Encrypted keychain or .env with restricted permissions
- Application history: SQLite with local-only access
- Session cookies: Encrypted cookie storage, expire after use

### 5.4 Recommendations for "Polite" Automation

**The Golden Rules:**

1. **Apply like a human, not a machine:**
   - Read job descriptions before applying
   - Customize cover letters when possible
   - Don't apply to obviously irrelevant jobs
   - Limit to 20-30 quality applications per day

2. **Respect the ecosystem:**
   - Job portals provide value — don't abuse them
   - If you're getting blocked, you're going too fast
   - Support the platforms you use (consider premium accounts)

3. **Protect yourself:**
   - Use a dedicated email for job applications
   - Don't use your primary phone number if possible
   - Monitor for unauthorized use of your data
   - Keep credentials separate from application code

4. **Technical best practices:**
   ```yaml
   automation_rules:
     max_applications_per_day: 30
     min_delay_between_apps: "2-5 minutes"
     working_hours: "09:00-21:00 IST"
     rest_between_portals: "10 minutes"
     resume_upload: "manual review required"
     cover_letter: "customize per job or skip"
     captcha_strategy: "2Captcha as fallback"
     proxy: "residential, per-session rotation"
   ```

5. **When to stop:**
   - If a portal sends a warning email
   - If your account gets temporarily suspended
   - If captcha solve rate drops below 50%
   - If you're applying to jobs you wouldn't actually take

---

## Appendix: Quick Reference

### Recommended Tech Stack

```
Language: Python 3.11+
Framework: Playwright (with Patchright for stealth)
Captcha: 2Captcha API (primary), Tesseract OCR (fallback for simple captchas)
Proxies: Bright Data or Smartproxy (residential, Indian IPs)
Storage: SQLite (local), python-dotenv (secrets)
```

### Key Libraries

```
pip install patchright playwright httpx beautifulsoup4
pip install pytesseract pillow easyocr          # OCR for simple captchas
pip install python-2captcha                     # 2Captcha API client
pip install python-dotenv                       # Environment variables
pip install tenacity                            # Retry logic
patchright install chromium
```

### Environment Variables Template

```bash
# .env (DO NOT commit to version control)
NAUKRI_EMAIL=user@example.com
NAUKRI_PASSWORD=...
INDEED_EMAIL=...
LINKEDIN_EMAIL=...
TWOCAPTCHA_API_KEY=...
PROXY_URL=http://user:pass@proxy.example.com:port
PHONE_NUMBER=+91...
```

---

*This document should be updated as anti-bot detection evolves. Last verified against current implementations as of April 2026.*
