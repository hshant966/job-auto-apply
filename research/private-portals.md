# Indian Private Job Portals - Automation Research

*Research compiled: April 3, 2026*

## Table of Contents
1. [LinkedIn](#1-linkedin-linkedincom)
2. [Naukri.com](#2-naukricom)
3. [Indeed India](#3-indeed-india-inindeedcom)
4. [Monster India / Foundit](#4-monster-india--foundit)
5. [Glassdoor India](#5-glassdoor-india)
6. [Instahyre & Hirist](#6-instahyre--hirist-tech-focused)
7. [Cross-Platform Analysis](#7-cross-platform-analysis)
8. [Anti-Bot & Browser Fingerprinting](#8-anti-bot--browser-fingerprinting)
9. [Common Form Fields](#9-common-form-fields-across-platforms)
10. [Known Automation Tools](#10-known-automation-tools--extensions)
11. [Feasibility Assessment](#11-feasibility-assessment)

---

## 1. LinkedIn (linkedin.com)

### Account Registration/Login Flow
- **Registration:** Email/phone + password; OAuth via Google/Apple
- **Login:** Email + password; SSO options
- **MFA:** Optional SMS/authenticator app
- **Session:** Long-lived cookies (li_at session cookie persists ~1 year); JSESSIONID for API calls
- **LinkedIn uses** a proprietary authentication system with CSRF tokens per request

### Profile Structure and Fields
- **Basic:** Name, headline, location, industry, summary/about
- **Experience:** Company, title, location, dates, description, media attachments
- **Education:** School, degree, field, dates, activities, grades
- **Skills:** Up to 50 endorsed skills
- **Certifications:** Name, issuer, URL, dates
- **Projects, Publications, Languages, Volunteer Experience**
- **Resume:** PDF upload stored server-side; multiple resumes supported
- **Profile completeness** is scored internally (All-Star, etc.)

### Job Search API / Scraping Possibilities
- **Official API:** LinkedIn Marketing/Sales APIs exist but NO public Job Search API
- **Internal API (Voyager):** LinkedIn uses a GraphQL API at `https://www.linkedin.com/voyager/api/`
  - Job search: `GET /voyager/api/jobs/jobPostings?q=jobSearch&keywords=python&location=India`
  - Job details: `GET /voyager/api/jobs/jobPostings/{jobId}`
  - Easy Apply fields: `GET /voyager/api/jobs/jobPostings/{jobId}/jobApplicationForm`
  - Requires `li_at` session cookie + CSRF token (JSESSIONID)
  - Rate limited: ~100 requests/minute varies by endpoint
- **Scraping:** Possible with authenticated session; HTML structure is React-based (server-rendered initially)
- **Difficulty:** HIGH - LinkedIn actively fights scraping with aggressive detection

### Application Submission Flow
**Easy Apply (1-5 steps):**
1. Click "Easy Apply" button on job listing
2. Review/confirm contact info (auto-filled from profile)
3. Upload/select resume (PDF/DOCX, max 2MB)
4. Answer screening questions (dropdowns, text fields, yes/no)
5. Review and submit

**Full Application (External):**
- Redirects to company ATS (Workday, Greenhouse, Lever, etc.)
- Cannot be automated from LinkedIn side

**Easy Apply API Structure:**
- Form fields returned via GraphQL: `jobApplicationForm` query
- Each field has: `type` (TEXT, DROPDOWN, RADIO, CHECKBOX, FILE), `label`, `required`, `options[]`
- Submission: POST to `/voyager/api/jobs/jobPostings/{id}/submitApplication`
- Body includes: form answers, resume reference, cover letter reference
- Response: 201 Created or error with validation messages

### Resume Upload Requirements
- **Formats:** PDF, DOCX, DOC
- **Max size:** 2MB (some sources say 5MB for certain flows)
- **Storage:** Uploaded resumes stored server-side; can reference by ID in subsequent applications
- **Profile resume:** One default resume; can upload different ones per application

### Anti-Bot Measures
- **Cloudflare:** Used on some endpoints
- **Rate limiting:** IP-based and account-based; aggressive limits on search/API calls
- **CAPTCHA:** reCAPTCHA v3 (invisible, scored); triggered by rapid actions
- **Browser fingerprinting:** Canvas fingerprint, WebGL, navigator properties, fonts
- **Session anomaly detection:** Login from new IP/location triggers verification
- **Automation detection:** Selenium/Playwright detected via `navigator.webdriver` flag, Chrome DevTools Protocol
- **Account restrictions:** Detected bots get "commercial use" limits or temporary blocks
- **Known patterns:** Rapid job applications (>50/hour) trigger soft blocks

### Mobile App vs Web Differences
- **Mobile API:** Uses different endpoints (`/mwap/` prefix); generally more lenient rate limits
- **Easy Apply:** Available on both; mobile may have fewer form steps
- **Notifications:** Push notifications for job alerts
- **App uses** native HTTP client (harder to intercept than browser)

### Known Automation Tools/Extensions
1. **Auto_job_applier_linkedIn** (GitHub, Python + Selenium) - Most popular open-source tool
   - Uses undetected-chromedriver for anti-detection
   - Supports Easy Apply with auto-fill of screening questions
   - OpenAI integration for resume customization
   - 100+ applications/hour claimed
2. **LinkedIn Easy Apply Bot with LangGraph** - Uses GPT-4o for form understanding
3. **LinkedHelper** (commercial) - Chrome extension for connection/message automation
4. **Dripify** (commercial) - Cloud-based LinkedIn automation
5. **PhantomBuster** - Cloud scraping/automation service

### API Access
- **Official:** No job application API publicly available
- **Unofficial (Voyager GraphQL):** Requires authenticated session cookies
  - Key endpoints documented above
  - Changes frequently (field names, paths)
  - Must maintain CSRF token chain
- **LinkedIn Partner API:** Exists for ATS integrations (limited access)

---

## 2. Naukri.com

### Account Registration/Login Flow
- **Registration:** Email/phone + password; Google/Facebook OAuth
- **Login:** Email/mobile + password; OTP-based login
- **Session:** JWT-based tokens; `naukSessionId` cookie
- **Profile completion** required before applying to jobs (step-by-step wizard)

### Profile Structure and Fields
- **Basic:** Name, email, phone, current location, preferred locations
- **Professional:** Current company, designation, years/months experience, industry, functional area, role
- **Education:** Highest degree, university, specialization, year of passing
- **Salary:** Current CTC, expected CTC (mandatory fields - unique to Naukri)
- **Skills:** Multiple skill tags with proficiency
- **Resume:** PDF upload; resume headline (text summary)
- **Profile summary:** Free-text description
- **Key differentiators:** Notice period, preferred job type (permanent/contract), gender, date of birth

### Job Search API / Scraping Possibilities
- **Official API:** None public
- **Internal APIs:**
  - Job search: `GET https://www.naukri.com/jobapi/v3/search` with query params (keywords, location, experience, salary, page)
  - Job details: `GET https://www.naukri.com/jobapi/v3/job/{jobId}`
  - Apply: `POST https://www.naukri.com/apply/now/{jobId}`
  - Profile update: Various endpoints under `/profileapi/`
  - **Auth:** `appid` + `systemid` headers (apparently internal tokens); session cookies
- **Scraping:** SPA (React); SSR HTML available for search results
- **Naukri Launcher:** Internal tool used by recruiters; reverse-engineered network calls mentioned on Reddit
- **Difficulty:** MEDIUM - Less aggressive than LinkedIn; has rate limits

### Application Submission Flow
1. Click "Apply" on job listing
2. If Easy Apply: Direct submission with existing profile + resume
3. If full application: Redirects to company ATS or Naukri's extended form
4. **One-click apply** for profile-complete users
5. Some jobs require: cover letter, additional questions, portfolio link

### Resume Upload Requirements
- **Formats:** PDF, DOCX, DOC
- **Max size:** ~5MB
- **Multiple resumes:** Not directly supported; one active resume at a time
- **Resume parser:** Naukri has an in-house parser that extracts structured data
- **Resume quality score:** Internal algorithm rates resume completeness

### Anti-Bot Measures
- **Rate limiting:** Moderate; search API limits around 60 requests/minute
- **CAPTCHA:** Google reCAPTCHA v2 on login; v3 on some actions
- **Cloudflare:** Used on main site
- **Session management:** Tokens expire after inactivity
- **IP-based blocking:** Rapid requests from same IP get throttled
- **Less aggressive** than LinkedIn overall

### Mobile App vs Web Differences
- **Mobile API:** Dedicated mobile API endpoints; JSON-based
- **Push notifications:** Job alerts, recruiter views
- **App-specific features:** "Naukri FastForward" (resume writing service)
- **Mobile app** uses a different auth flow with device fingerprinting

### Known Automation Tools/Extensions
- **Fewer open-source tools** compared to LinkedIn
- **Python scripts:** Some developers reverse-engineered the API for auto-refresh of profile (keeps profile "active" in search results)
- **Profile refresh bot:** Common DIY automation - periodically updating a field to boost profile visibility
- **Commercial services:** Resume writing services use automation internally

### API Access
- **Official:** No public API
- **Unofficial internal APIs:**
  - Job search: `/jobapi/v3/search` (requires appid/systemid headers)
  - These headers appear to be tied to the Naukri mobile app or internal tools
  - Changing values may break functionality
- **Profile refresh automation:** Common pattern using Selenium to update profile timestamp

---

## 3. Indeed India (in.indeed.com)

### Account Registration/Login Flow
- **Registration:** Email + password; Google/Apple/Facebook OAuth
- **Login:** Email + password; SSO
- **Session:** Cookie-based; `indeed_csrf_token`, `JSESSIONID`
- **Account linked** to global Indeed account

### Profile Structure and Fields
- **Basic:** Name, email, phone, location
- **Work experience:** Company, title, dates, description
- **Education:** School, degree, field, dates
- **Skills:** Tags/skills list
- **Resume:** PDF upload (primary) or Indeed resume builder
- **Preferences:** Job type, salary, location radius
- **Profile is simpler** than LinkedIn/Naukri; focus is on resume

### Job Search API / Scraping Possibilities
- **Official API:** Publisher API (deprecated for new applicants); limited to job listing data
- **Indeed API v2:** For employers (posting jobs, managing applications)
- **Internal APIs:**
  - Job search: `GET https://in.indeed.com/jobs?q=python&l=India` (HTML) or internal JSON endpoints
  - Job details: Structured HTML with JSON-LD schema markup
  - Apply: Various flows depending on "Apply on Indeed" vs "Apply on company site"
- **Scraping:** Server-rendered HTML for search results; easier to parse than SPAs
- **Difficulty:** MEDIUM-HIGH - Indeed is aggressive about automation detection

### Application Submission Flow
**"Apply on Indeed" (1-3 steps):**
1. Click "Apply Now" on Indeed-hosted job
2. Upload resume or use Indeed resume
3. Answer screening questions (if any)
4. Review and submit

**"Apply on Company Site":**
- Redirects to external ATS (Workday, iCIMS, Taleo, etc.)
- Indeed tracks conversion for employers

**Key difference:** Indeed has both native apply and external redirect; ratio varies by market

### Resume Upload Requirements
- **Formats:** PDF, DOCX, DOC, TXT, RTF
- **Max size:** 5MB
- **Indeed Resume:** Can create resume directly on platform (structured form)
- **Cover letter:** Optional; text field or file upload

### Anti-Bot Measures
- **Cloudflare:** Heavy use; challenge pages common
- **CAPTCHA:** reCAPTCHA on registration/login; may appear during rapid browsing
- **Rate limiting:** Aggressive; search requests throttled after ~30/minute
- **Bot detection:** "To deter bot activity, Job Seekers in certain locations may [be challenged]" (TOS, Feb 2026)
- **Terms explicitly prohibit** "submitting applications by automated means"
- **IP blocking:** Known to block VPN/datacenter IPs
- **Fingerprinting:** Advanced browser fingerprinting on apply flow

### Mobile App vs Web Differences
- **Mobile app** has separate API infrastructure
- **Indeed Apply** smoother on mobile (fewer steps)
- **Push job alerts** more prominent
- **Mobile API** generally more resilient to automation

### Known Automation Tools/Extensions
- **Easy Apply Bot** (various repos) - Targets Indeed's "Apply on Indeed" jobs
- **Indeed-specific scrapers:** Python (requests + BeautifulSoup) for job data
- **Auto-apply tools** less common than LinkedIn ones due to stricter enforcement
- **Commercial tools:** LazyApply, LoopCV support Indeed

### API Access
- **Official:** Employer API only (job posting management)
- **Unofficial:** Internal search endpoints; structured data in HTML (JSON-LD)
- **RSS feeds:** Were available historically; largely deprecated

---

## 4. Monster India / Foundit

### Foundit.in (formerly Monster India)

### Account Registration/Login Flow
- **Registration:** Email/phone + password; Google/Facebook OAuth
- **Login:** Email/mobile + password; OTP
- **Session:** Cookie-based session management
- **Rebranded** from Monster India to Foundit.in (2022)

### Profile Structure and Fields
- **Basic:** Name, email, phone, gender, DOB, location
- **Professional:** Current company, designation, experience (years/months), industry, functional area, role
- **Education:** Highest degree, university, specialization
- **Salary:** Current CTC, expected CTC
- **Skills:** Multiple tags
- **Resume:** PDF upload
- **Key differentiators:** Notice period, resume headline, profile summary
- **Similar to Naukri** in structure (Indian job portal conventions)

### Job Search API / Scraping Possibilities
- **Official API:** None public
- **Internal APIs:**
  - Job search: `GET https://www.foundit.in/srp/results` with query parameters
  - Less documented than Naukri/LinkedIn
- **Scraping:** SPA (React); SSR available for search results
- **Difficulty:** MEDIUM - Smaller platform, less aggressive anti-bot

### Application Submission Flow
1. Click "Apply" on job listing
2. If profile complete: One-click apply
3. If not: Form to fill (experience, education, salary expectations)
4. Some jobs redirect to company site

### Resume Upload Requirements
- **Formats:** PDF, DOCX, DOC
- **Max size:** ~5MB
- **Resume parser:** Built-in; extracts structured data

### Anti-Bot Measures
- **Basic rate limiting**
- **CAPTCHA:** On login; occasional on apply
- **Cloudflare:** Basic protection
- **Less sophisticated** than LinkedIn/Indeed

### Mobile App vs Web Differences
- **Foundit app** has similar functionality
- **Push notifications** for job matches
- **Mobile API** not extensively documented

### Known Automation Tools/Extensions
- **Minimal open-source tooling**
- **Some Selenium scripts** exist for profile refresh
- **Commercial services** handle automation internally

### API Access
- **Official:** None
- **Unofficial:** Internal search endpoints accessible with session

---

## 5. Glassdoor India

### Account Registration/Login Flow
- **Registration:** Email + password; Google/Apple OAuth
- **Login:** Email + password; SSO
- **Glassdoor owned by Recruit Holdings** (same as Indeed); accounts increasingly linked
- **Session:** Cookie-based; shares infrastructure with Indeed

### Profile Structure and Fields
- **Primary focus:** Company reviews, salary data, interview questions
- **Job seeker profile:** Similar to Indeed (shared parent company)
- **Basic:** Name, email, job title, employer
- **Contribution profile:** Reviews, salaries, photos
- **Resume:** Can upload for job applications
- **Less detailed** profile than LinkedIn/Naukri for job seeking

### Job Search API / Scraping Possibilities
- **Official API:** None public
- **Job search:** `GET https://www.glassdoor.co.in/Job/india-python-jobs-SRCH_IL.0,5_IN113_KO6,12.htm`
- **Jobs sourced from:** Indeed's job feed + direct employer postings
- **Scraping:** Mixed SSR/SPA; HTML parseable
- **Glassdoor is more scraper-friendly** for review/salary data historically
- **Difficulty:** MEDIUM

### Application Submission Flow
- **Primarily redirects** to Indeed or company ATS for applications
- **"Apply on Glassdoor"** rare; mostly a job aggregator
- **Focus is on research** (reviews, salaries) not direct applications

### Anti-Bot Measures
- **CAPTCHA:** On some pages
- **Rate limiting:** Moderate
- **Cloudflare:** Basic
- **Historically more permissive** than LinkedIn for scraping review data

### Known Automation Tools/Extensions
- **Glassdoor scrapers:** Well-documented for review/salary data extraction
- **Job application tools:** Minimal; Glassdoor is primarily a research tool
- **glassdoor-scraper** (Python, GitHub) - For review data

### API Access
- **Official:** None (previously had partner APIs for reviews)
- **Unofficial:** HTML scraping possible

---

## 6. Instahyre & Hirist (Tech-Focused)

### Instahyre (instahyre.com)

#### Account Registration/Login Flow
- **Registration:** Email/LinkedIn import; Google OAuth
- **Login:** Email + password; OTP
- **Curated platform:** Significantly smaller pool; employer-invite model in some cases

#### Profile Structure and Fields
- **Tech-focused:** Skills, GitHub, portfolio links prominent
- **Basic:** Name, email, phone, location
- **Professional:** Current role, company, experience, skills (with proficiency)
- **Education:** Degree, college
- **Preferences:** Role type, company size, salary expectations
- **Profile quality score:** Internal rating system
- **LinkedIn import:** Can auto-populate from LinkedIn

#### Job Search / Application
- **Matched jobs** based on profile (less manual searching)
- **Application:** Apply button; profile sent directly to employer
- **Employer side:** Companies search and invite candidates
- **Less volume** than Naukri; more curated

#### Anti-Bot Measures
- **Minimal** - Smaller scale; less target for bots
- **Basic rate limiting**
- **CAPTCHA on registration** primarily

#### API Access
- **None documented**
- **Small platform** with limited automation interest

---

### Hirist (hirist.com)

#### Account Registration/Login Flow
- **Registration:** Email/phone + password; Google/GitHub OAuth
- **Login:** Standard email/password
- **Tech job portal** focused on IT/software roles

#### Profile Structure and Fields
- **Tech-heavy:** Skills, frameworks, technologies, GitHub profile
- **Basic:** Name, email, phone, current company, designation
- **Experience:** Detailed work history
- **Education:** Degree, institution
- **Notice period:** Important field (Indian market specific)
- **CTC:** Current and expected

#### Job Search / Application
- **Search by:** Skills, location, experience, salary
- **Application:** Direct apply with profile
- **Recruiter contact** model (similar to Instahyre)

#### Anti-Bot Measures
- **Basic** - Smaller platform
- **CAPTCHA on forms**

#### API Access
- **None documented**

---

## 7. Cross-Platform Analysis

### Platform Comparison Matrix

| Feature | LinkedIn | Naukri | Indeed India | Foundit | Glassdoor | Instahyre | Hirist |
|---------|----------|--------|-------------|---------|-----------|-----------|--------|
| Market dominance | Global #1 | India #1 | Global #2 | India mid | Research | Niche tech | Niche tech |
| Profile depth | Very high | High | Medium | Medium | Low | Medium | Medium |
| Easy Apply | Yes | Yes | Yes | Yes | No (redirects) | Yes | Yes |
| Anti-bot strength | Very high | Medium | High | Low-Med | Medium | Low | Low |
| API availability | Internal (GraphQL) | Internal (REST) | None useful | None | None | None | None |
| Open-source tools | Many | Few | Some | Minimal | Some (reviews) | None | None |
| Scraping difficulty | Very hard | Medium | Hard | Easy-Med | Medium | Easy | Easy |
| Mobile API | Yes (mwap) | Yes | Yes | Yes | Yes | Yes | Yes |

### Application Flow Comparison

**One-Click Apply (easiest):**
- LinkedIn Easy Apply (with pre-filled profile)
- Naukri (when profile complete)
- Indeed "Apply on Indeed"
- Instahyre

**Multi-Step Forms:**
- LinkedIn (Easy Apply with screening questions)
- Naukri (extended applications)
- Indeed (company-specific questions)

**External Redirect (hardest to automate):**
- LinkedIn (full applications)
- Indeed (Apply on company site)
- Glassdoor (mostly redirects)
- All platforms (for some jobs)

### Automation Difficulty Ranking (easiest to hardest)
1. **Hirist** - Minimal protection
2. **Instahyre** - Small scale, basic protection
3. **Foundit** - Basic anti-bot
4. **Naukri** - Medium protection, well-documented internal API
5. **Glassdoor** - Medium protection
6. **Indeed India** - Aggressive Cloudflare, strong fingerprinting
7. **LinkedIn** - Most aggressive detection, account ban risk high

---

## 8. Anti-Bot & Browser Fingerprinting

### Common Anti-Bot Techniques Across Platforms

#### Cloudflare
- **Used by:** LinkedIn, Naukri, Indeed, Foundit, Glassdoor
- **Challenge types:** JS challenge, managed challenge (interactive), CAPTCHA
- **Bot detection:** TLS fingerprinting, HTTP/2 fingerprint, JA3/JA4 signatures
- **Bypass difficulty:** High; requires undetected browser or TLS spoofing
- **Impact:** `requests`/`urllib` blocked immediately; headless Chrome may be flagged

#### Browser Fingerprinting Methods
1. **Canvas fingerprinting:** Render hidden canvas, hash pixel data
2. **WebGL fingerprinting:** GPU/driver info from WebGL context
3. **Navigator properties:** `navigator.webdriver`, `navigator.languages`, `navigator.platform`
4. **Font enumeration:** Detect installed fonts via CSS/JS
5. **Audio fingerprinting:** Web Audio API context fingerprint
6. **Screen/viewport:** Resolution, color depth, device pixel ratio
7. **Plugin enumeration:** `navigator.plugins`
8. **Battery API:** Battery status fingerprint (deprecated but still checked)
9. **Timezone/locale:** Inconsistent timezone = red flag
10. **Chrome DevTools Protocol detection:** `Runtime.enable` hook detection

#### Specific Detection Methods by Platform

**LinkedIn:**
- `navigator.webdriver` flag check (bypassed by undetected-chromedriver)
- Chrome DevTools Protocol detection
- Behavioral analysis: mouse movement patterns, scroll behavior, typing speed
- TLS fingerprinting via Cloudflare
- Request header analysis (Accept-Language, User-Agent consistency)
- Login anomaly detection (new device/IP/location)
- Application pattern detection (too many applications, too fast)

**Naukri:**
- reCAPTCHA v3 scoring (behavioral, not interactive)
- Session token validation
- Moderate request rate monitoring
- Less sophisticated than LinkedIn

**Indeed:**
- Cloudflare managed challenges
- Aggressive IP reputation checking (blocks VPNs/datacenters)
- Request timing analysis
- Browser fingerprint collection

### Bypass Approaches (Research Only)

| Technique | Effectiveness | Detection Risk |
|-----------|--------------|----------------|
| undetected-chromedriver | High (LinkedIn) | Medium (behavioral still detectable) |
| Playwright-stealth | Medium | Medium |
| Real browser + automation (CDP) | High | Medium-Low |
| Residential proxies | High (IP-based) | Low (if consistent) |
| Human-like delays + mouse movement | Medium | Low |
| Mobile API emulation | Medium-High | Low |
| Browser profile reuse | High | Low |

---

## 9. Common Form Fields Across Platforms

### Universal Fields (All Platforms)
- Full name
- Email address
- Phone number
- Current location
- Resume/CV upload (PDF)
- Years of experience
- Current/last job title
- Current/last company name

### Common Fields (4+ Platforms)
- Expected salary/CTC
- Notice period / Availability date
- Highest education level
- University/College name
- Key skills
- Preferred job location(s)
- Work authorization (visa status)

### Platform-Specific Fields

**Naukri-specific:**
- Current CTC (mandatory, INR)
- Expected CTC (mandatory, INR)
- Industry type
- Functional area
- Role category
- Gender
- Date of birth
- Resume headline (text, 250 chars)

**LinkedIn-specific:**
- LinkedIn headline
- Industry
- Profile URL
- Cover letter (optional, text or file)
- Work samples/portfolio
- Years at specific company

**Indeed-specific:**
- Indeed resume (structured) vs uploaded resume
- Start date availability
- Shift preference (day/night/rotating)
- Background check consent

### Screening Question Patterns
1. **Yes/No:** "Are you authorized to work in India?"
2. **Dropdown:** Years of experience with specific technology
3. **Text:** "Describe your experience with..."
4. **Numeric:** "How many years of Python experience?"
5. **Multiple choice:** Salary range, preferred work arrangement
6. **File upload:** Portfolio, certifications (uncommon)

---

## 10. Known Automation Tools & Extensions

### Open Source

| Tool | Platform | Tech Stack | Stars | Status |
|------|----------|-----------|-------|--------|
| Auto_job_applier_linkedIn | LinkedIn | Python, Selenium, undetected-chromedriver | 10k+ | Active |
| linkedin-easy-apply-bot (LangGraph) | LinkedIn | Python, LangGraph, GPT-4o | - | Experimental |
| LinkedIn-Easy-Apply-Automation | LinkedIn | Python, Selenium | - | Active |
| Indeed scraper | Indeed | Python, requests | - | Various |
| glassdoor-scraper | Glassdoor | Python, BeautifulSoup/Selenium | - | Maintenance |

### Commercial

| Tool | Platforms | Type | Cost |
|------|-----------|------|------|
| LazyApply | LinkedIn, Indeed, Naukri | Cloud auto-apply | ~$100-200 lifetime |
| LoopCV | LinkedIn, Indeed | Cloud | Free tier available |
| Sonara AI | LinkedIn, Indeed | AI auto-apply | ~$20-40/month |
| Massive | LinkedIn, Indeed | Cloud | - |
| JobHire.AI | Multiple | AI agent | - |
| Scale.jobs | Workday-based ATS | Human-assisted | ~$200-400 |
| LinkedHelper | LinkedIn | Chrome extension | ~$15-50/month |
| Dripify | LinkedIn | Cloud | ~$40-100/month |
| PhantomBuster | LinkedIn, Indeed | Cloud scraping | ~$60-90/month |

### Indian Market Specific
- **Naukri profile refresh bots** - Common DIY Python scripts
- **Resume formatting services** - Use internal automation
- **Job alert aggregators** - Telegram/WhatsApp bots

---

## 11. Feasibility Assessment

### For an Automated Job Application System Targeting India

#### Tier 1: Highly Feasible
- **Hirist, Instahyre:** Minimal anti-bot; simple apply flow; small market
- **Foundit:** Basic protection; similar to Naukri but easier

#### Tier 2: Feasible with Effort
- **Naukri:** Well-documented internal API; manageable anti-bot; India's largest portal
  - Key challenge: Maintaining session + API headers as they change
  - Approach: Selenium + API interception OR direct API calls with reverse-engineered auth
  - CTC/notice period fields are Indian-specific but standardizable

- **LinkedIn Easy Apply only:** Proven by open-source tools; limited to Easy Apply jobs
  - Key challenge: Account ban risk; behavioral detection
  - Approach: undetected-chromedriver + human-like behavior + rate limiting
  - Not feasible for "Apply on company site" jobs

#### Tier 3: Difficult
- **Indeed India:** Aggressive Cloudflare; blocks automation
  - Approach: Residential proxies + real browser automation
  - "Apply on Indeed" jobs only (external redirect not automatable)

- **LinkedIn Full Applications:** Not feasible through LinkedIn automation
  - Would need to handle each company's ATS separately

#### Tier 4: Not Recommended for Automation
- **Glassdoor:** Primarily a research tool; redirects for applications
- **External ATS (Workday, Taleo, iCIMS):** Each has unique forms; Workday especially complex

### Recommended Approach
1. **Primary targets:** LinkedIn Easy Apply + Naukri (covers ~70% of Indian job market)
2. **Secondary:** Indeed India (Apply on Indeed jobs only)
3. **Supplement with:** Instahyre/Hirist for tech roles
4. **Fallback:** Manual application for external redirect jobs

### Technical Architecture Considerations
- **Browser automation:** Playwright (preferred) or Selenium with stealth plugins
- **Session management:** Persistent browser profiles to avoid re-login
- **Anti-detection:** Residential proxies, human-like behavior simulation, random delays
- **Resume management:** Template-based with variable injection per platform
- **Form filling:** LLM-based question answering for screening questions
- **Monitoring:** Application tracking across platforms

---

## Appendix: LinkedIn Easy Apply API Deep Dive

### Authentication Flow
1. Login via web → extract `li_at` cookie + `JSESSIONID`
2. All API requests include:
   - `Cookie: li_at=<token>; JSESSIONID=<csrf>`
   - `csrf-token: <JSESSIONID value>`
   - `x-restli-protocol-version: 2.0.0`
   - `x-li-lang: en_US`

### Key Endpoints
```
# Job Search
GET /voyager/api/jobs/jobPostings?q=jobSearch&keywords={kw}&location={loc}&start={offset}&count=25

# Job Details
GET /voyager/api/jobs/jobPostings/{jobId}

# Easy Apply Form (get fields)
GET /voyager/api/jobs/jobPostings/{jobId}/jobApplicationForm

# Submit Application
POST /voyager/api/jobs/jobPostings/{jobId}/submitApplication
Body: { "screeningQuestions": [...], "resume": { "id": "..." }, ... }

# Upload Resume
POST /voyager/api/media/uploadAsset
# Returns asset URN for use in application

# User's Applied Jobs
GET /voyager/api/jobs/jobApplications?count=25&start=0
```

### Form Field Types
- `TEXT_QUESTION` → Free text input
- `DROPDOWN_QUESTION` → Select from options
- `RADIO_QUESTION` → Radio buttons
- `CHECKBOX_QUESTION` → Checkbox (boolean)
- `FILE_QUESTION` → Resume/document upload
- `NUMERIC_QUESTION` → Number input (years of experience)
- `DATE_QUESTION` → Date picker

---

## Appendix: Naukri Internal API

### Key Endpoints (Reverse-Engineered)
```
# Job Search
GET /jobapi/v3/search?noOfResults=20&urlType=search_by_key_cm&searchType=adv&keyword=python&location=bangalore&page=1
Headers: appid: 103, systemid: Naukri

# Job Detail
GET /jobapi/v3/job/{jobId}?loggedIn=false

# Profile
GET /api/profiles/myProfile
POST /api/profiles/updateProfile

# Apply
POST /apply/now/{jobId}
Body: { "recoId": "...", "searchId": "..." }

# Resume Upload
POST /api/profiles/uploadResume
# Multipart form data
```

### Headers Required
```
appid: 103
systemid: Naukri
Content-Type: application/json
User-Agent: Mozilla/5.0 ...
```

*Note: These internal APIs are undocumented and may change without notice.*

---

*End of Research Document*
