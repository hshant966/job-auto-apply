# Indian Government Job Application Portals - Comprehensive Research

> Last Updated: 2026-04-03
> Purpose: Document all major Indian govt job portals for automation/analysis

---

## Table of Contents
1. [Common Patterns Across All Portals](#common-patterns)
2. [SSC (Staff Selection Commission)](#1-ssc)
3. [UPSC (Union Public Service Commission)](#2-upsc)
4. [RRB (Railway Recruitment Board)](#3-rrb)
5. [IBPS (Institute of Banking Personnel Selection)](#4-ibps)
6. [State PSC Portals](#5-state-psc-portals)
7. [NCS (National Career Service)](#6-ncs)
8. [Employment News](#7-employment-news)
9. [NIC Infrastructure Analysis](#nic-infrastructure)

---

## Common Patterns Across All Portals <a name="common-patterns"></a>

### Shared Characteristics
- **One-Time Registration (OTR)**: All major portals now use OTR systems — register once, apply for multiple exams
- **OTP Verification**: All require mobile + email OTP verification during registration
- **Photo/Signature Upload**: Universal requirement with very similar specs
- **Aadhaar Integration**: Increasingly mandatory or strongly recommended
- **SBI Payment Gateway**: Most portals use SBI for fee collection
- **Captcha**: All use image-based CAPTCHA (no common API pattern)
- **Two-Part Applications**: Most use Part-I (registration/basic info) and Part-II (payment/center selection)

### Standard Document Specifications (Common Across Portals)
| Document | Format | Size Range | Dimensions |
|----------|--------|------------|------------|
| Photograph | JPG/JPEG | 20-200 KB | 3.5cm × 4.5cm (200×230 px typical) |
| Signature | JPG/JPEG | 10-50 KB | 3.5cm × 1.5cm (140×60 px typical) |
| Thumb Impression | JPG | 10-50 KB | 3cm × 3cm |
| Category Certificate | PDF | < 500 KB-1 MB | N/A |
| Photo ID | PDF | < 500 KB | N/A |

### Common Payment Methods
1. Credit/Debit Card (Visa/Master/RuPay)
2. Net Banking (SBI is primary gateway)
3. UPI
4. Cash via SBI Challan (offline)

---

## 1. SSC (Staff Selection Commission) <a name="1-ssc"></a>

**Portal**: `https://ssc.gov.in` (new) | `https://ssc.nic.in` (legacy)
**Backend**: NIC hosted, ASP.NET based (new portal is modernized)

### Registration Flow (OTR - One-Time Registration)

1. **Visit Portal**: Go to `https://ssc.gov.in`
2. **Click "Register Now"**: Initiates OTR process
3. **Basic Details**: Enter Name, Aadhaar Number, Date of Birth, Gender, Father's Name, Mother's Name
4. **Category & Qualification**: Select category (SC/ST/OBC/General/EWS), highest educational qualification
5. **Contact Details**: Mobile number, email ID, permanent address, correspondence address
6. **OTP Verification**: OTP sent to both mobile AND email — must verify both
7. **Photo & Signature Upload**: Upload as per specifications
8. **Registration Complete**: Receive Registration ID + Password via SMS/email

### Application Form Fields

**Personal Details:**
- Name (as per 10th certificate)
- Date of Birth (DD/MM/YYYY)
- Gender
- Father's Name
- Mother's Name
- Nationality
- Category (General/SC/ST/OBC/EWS)
- Sub-category (if any, like PwD, Ex-Serviceman)

**Identity Details:**
- Aadhaar Number (last 6 digits for verification)
- Photo ID type and number

**Education Details:**
- 10th (Board, Year, Percentage/CGPA)
- 12th (Board, Year, Percentage/CGPA)
- Graduation (University, Year, Percentage/CGPA)
- Post-graduation (if applicable)
- Professional qualifications

**Address:**
- Permanent Address (with PIN code)
- Correspondence Address (with PIN code)

**Exam Preferences:**
- Post preference order (up to 4-5 posts)
- Exam center preference (3 cities)
- Language preference for exam

**Category/Certificates:**
- Reservation category
- EWS certificate details
- PwD certificate details
- Ex-servicemen details

### Document Upload Requirements

| Document | Format | Min Size | Max Size | Dimensions |
|----------|--------|----------|----------|------------|
| Photograph | JPG/JPEG | 4 KB | 20 KB | 3.5cm × 4.5cm (100×127 px) |
| Signature | JPG/JPEG | 1 KB | 12 KB | 3.5cm × 1.5cm (140×60 px) |
| Live Photo | JPG (captured via webcam) | Auto | Auto | Webcam resolution |

**Photo Specifications:**
- Recent (taken within 3 months)
- Color photo, white/light background
- Full face visible, no cap/mask/glasses
- Eyes open, looking straight at camera
- New portal uses **Live Photo Capture** via webcam/mobile camera

**Signature Specifications:**
- Sign on white paper with blue/black ink
- Scan at 200 DPI
- Only the signature area, no extra white space

### Payment Flow

1. Complete Part-I (basic registration)
2. Proceed to Part-II (application form)
3. Select payment method:
   - **Online**: Credit/Debit Card, Net Banking, UPI
   - **Offline**: Generate SBI Challan, deposit cash at SBI branch
4. Fee: ₹100 (General/OBC male), Free for Female/SC/ST/PwD/Ex-SM
5. Payment receipt auto-linked to application

### Captcha/OTP Details
- **Captcha**: Image-based CAPTCHA on login page (distorted text)
- **OTP**: Sent to registered mobile number AND email during:
  - Initial registration
  - Login (if OTP-based login selected)
  - Application submission
- **Live Photo**: Webcam capture as anti-fraud measure (no uploading pre-captured photos for application)

### Form URL Structure
```
https://ssc.gov.in/portal/authentication/login
https://ssc.gov.in/portal/otr/register
https://ssc.gov.in/portal/application/apply/{exam_code}
https://ssc.gov.in/portal/payment/initiate
```

### API Endpoints (Observed)
- Login: POST to `/portal/authentication/login`
- OTP verification: POST to `/portal/authentication/verify-otp`
- Application submit: POST to `/portal/application/submit`
- Payment gateway: Redirects to SBI ePay or similar

### Common Issues & Workarounds
- **Old OTR not working on new site**: Must re-register on new portal (ssc.gov.in)
- **Live photo issues**: Need webcam with good lighting; mobile camera can be used as alternative
- **Payment timeout**: Wait 30 min before retry; save transaction ID
- **Last-day submission**: Server congestion is common; submit 3-5 days early
- **Aadhaar linking issues**: If Aadhaar doesn't match, use alternate ID proof
- **Photo rejection**: Most common issue — ensure correct size, format, and face visibility

---

## 2. UPSC (Union Public Service Commission) <a name="2-upsc"></a>

**Portal**: `https://upsconline.gov.in` (application) | `https://upsc.gov.in` (info)
**Backend**: Dedicated UPSC IT system (recently revamped with tender for new system)

### Registration Flow (OTR - One-Time Registration)

1. **Visit Portal**: Go to `https://upsconline.gov.in`
2. **Click "New Registration" / OTR Registration**
3. **Part-I Registration**:
   - Enter Name, Date of Birth, Gender, Father's Name, Mother's Name
   - Email ID and Mobile Number
   - Category (General/SC/ST/OBC/EWS/PwD)
   - Nationality
   - Have you ever changed name? (Yes/No)
4. **OTP Verification**: OTP sent to mobile and email
5. **Generate Registration ID (RID)**
6. **Part-II Registration**:
   - Login with RID + Date of Birth
   - Upload Photograph and Signature
   - Fee Payment
   - Select Exam Center (first-apply-first-allot basis)
   - Choose optional subjects (for CSE)
   - Fill detailed qualification information
7. **Final Submission**: Review and submit

### Application Form Fields

**Personal Details:**
- Name (exactly as in matriculation certificate)
- Date of Birth
- Gender
- Father's Name / Mother's Name
- Nationality
- Marital Status
- Community / Category
- Whether belonging to minority
- Are you a benchmark disability person?

**Educational Qualifications:**
- Matriculation / 10th (Board, Year, Subjects, Percentage)
- Higher Secondary / 12th (Board, Year, Subjects, Percentage)
- Graduation (University, College, Year, Subject, Division/Class)
- Post-Graduation (if applicable)
- Professional Degree (if applicable)

**Employment Details:**
- Currently employed? (Yes/No)
- If yes: Department, Designation, Pay Scale

**Exam-Specific:**
- Choice of Examination Center (3 preferences)
- Optional Subject (for CSE)
- Medium of Examination
- Number of attempts already made

**Reservation/Relaxation:**
- SC/ST/OBC/EWS status
- PwD status and type
- Ex-Servicemen status
- Age relaxation claimed

**Address:**
- Complete postal address with PIN code

### Document Upload Requirements

| Document | Format | Size | Dimensions |
|----------|--------|------|------------|
| Photograph | JPG/JPEG | 20 KB - 300 KB | 3.5cm × 4.5cm |
| Signature | JPG/JPEG | 20 KB - 300 KB | 3.5cm × 1.5cm |
| Photo ID | PDF | Up to 1 MB | N/A |
| Category Certificate | PDF | Up to 1 MB | N/A |
| PwD Certificate | PDF | Up to 1 MB | N/A |

**Photo Specifications:**
- Recent color photograph
- White background preferred
- Face should occupy 50-70% of the photo
- No caps, masks, or glasses
- JPG/JPEG format only

**Signature Specifications:**
- Sign on white paper with black ink
- Scan in JPG/JPEG format
- Clear and legible

### Payment Flow

1. Complete Part-I registration → Get RID
2. Login to Part-II with RID + DOB
3. Click "Pay Examination Fees"
4. Payment options:
   - **Cash**: Generate Pay-in-Slip (Challan), deposit at any SBI branch → Get Transaction ID → Return to portal and enter Transaction ID
   - **Credit/Debit Card**: Any bank
   - **Net Banking**: SBI only
   - **UPI**: Any bank
5. Fee: ₹100-₹200 depending on exam (Female/SC/ST/PwD exempted)
6. After payment → Complete remaining Part-II fields

### Captcha/OTP Details
- **Captcha**: Image-based CAPTCHA on login
- **OTP**: Required for login (via email/mobile)
- **SSL Warning**: Portal uses HTTPS; browsers may show "Proceed to upsconline.gov.in (unsafe)" — must click Advanced → Proceed
- **Mobile phones NOT compatible**: UPSC explicitly states only Desktop/Laptop should be used

### Form URL Structure
```
https://upsconline.gov.in/upsc/OTRP/candidate/registration
https://upsconline.gov.in/upsc/OTRP/candidate/login
https://upsconline.gov.in/upsc/OTRP/examination/{exam_code}/apply
https://upsconline.gov.in/upsc/OTRP/payment/
```

### Common Issues & Workarounds
- **Blank/Zero Registration Number**: Application not submitted successfully — must refill
- **Browser compatibility**: Best on Chrome/Firefox; IE not recommended
- **Resolution issues**: Hold Ctrl + Mouse scroll down to adjust resolution if form doesn't fit
- **Cache problems**: Clear browser cache before filling
- **Special characters**: `!@#$%^&*()` etc. not accepted in Name/Address fields
- **Center capacity**: First-come-first-served; popular centers fill fast
- **Fee payment timeout**: Wait 30 min; if debited but not reflected, wait 24h
- **Challan processing**: Visit SBI next day; ask bank to use Screen Reference Number if needed
- **Correction window**: Opens after application closing date — limited fields editable

---

## 3. RRB (Railway Recruitment Board) <a name="3-rrb"></a>

**Portal**: Regional RRB websites (21 zones) + centralized portal
**Backend**: NIC hosted, centralized application system across all RRB zones
**Example URLs**: `https://www.rrbchennai.gov.in`, `https://rrbald.gov.in`, etc.
**Registration Portal**: `https://www.rrbcdg.gov.in` (centralized)

### Registration Flow

1. **Visit Official RRB Website**: Select your preferred RRB zone
2. **Click "New Registration"**: For first-time applicants
3. **Basic Details**: Name (exactly as per 10th certificate), Father's Name, DOB, Mobile Number, Email ID
4. **OTP Verification**: Sent to mobile and email (may take 2-5 min during peak)
5. **Registration Number Generated**: Screenshot/save immediately — valid for all future RRB exams
6. **Login with Registration Number + Password**
7. **Complete Application Form** (multiple sections):
   - Personal Details
   - Educational Qualifications
   - Category Information
   - Post Preferences (up to 5 posts)
   - Exam Center Choices (3 centers)
8. **Upload Documents**
9. **Fee Payment**
10. **Final Submission**

### Application Form Fields

**Personal Details:**
- Name (exactly as per 10th certificate — critical!)
- Father's Name / Mother's Name
- Date of Birth (DD-MM-YYYY)
- Gender
- Nationality
- Category (UR/OBC/SC/ST/EWS)
- Sub-category (PwD, Ex-SM, etc.)
- Domicile State
- Aadhaar Number (strongly recommended)

**Educational Details:**
- 10th: Board, Year, Roll Number, Percentage
- 12th: Board, Year, Roll Number, Percentage
- Graduation: University, College, Year, Stream, Percentage
- Additional qualifications (ITI, Diploma, etc.)
- Technical qualifications (if applicable)

**Exam Preferences:**
- Post preference (rank up to 5 posts)
- Exam center preference (rank 3 cities)
- Language for exam (Hindi/English/Regional)

**Experience:**
- Railway service experience (if any)
- Work experience details

**Reservation:**
- Category certificate number and issuing authority
- EWS certificate details
- PwD certificate (type and percentage of disability)

### Document Upload Requirements

| Document | Format | Size | Dimensions |
|----------|--------|------|------------|
| Photograph | JPG/JPEG | 20-50 KB | 3.5cm × 4.5cm |
| Signature | JPG/JPEG | 10-20 KB | 3.5cm × 1.5cm |
| Category Certificate | PDF | Up to 1 MB | N/A |
| Educational Certificates | PDF | Up to 1 MB each | N/A |
| Aadhaar | PDF | Up to 1 MB | N/A |

**Photo Specifications:**
- Recent (within 3 months)
- Colored, light background
- Face clearly visible
- No caps/sunglasses
- Auto-validated by system for dimensions

**Signature Specifications:**
- White paper, black ink
- Scan at 200 DPI
- Clean, no extra markings

### Payment Flow

1. Complete all form sections
2. Proceed to payment:
   - **Debit/Credit Card** (all banks)
   - **Net Banking**
   - **UPI**
3. Gateway charges: ₹10-20 additional
4. Fee: ₹500 (General/OBC), ₹250 (SC/ST/Ex-SM/Women/Minorities/EWS/PwD)
5. **Critical**: Save payment receipt immediately — download offline
6. Transaction ID is your payment reference

### Captcha/OTP Details
- **Captcha**: Image-based on login page
- **OTP**: Required for registration and login
- **Aadhaar-based biometric**: Some RRBs mandate Aadhaar for biometric verification during document verification stage

### Form URL Structure
```
https://www.rrbcdg.gov.in/registration
https://www.rrbcdg.gov.in/application/{cen_code}
https://rrcrecruit.co.in/{region_code}/application/
```

### Common Issues & Workarounds
- **40% application rejection rate**: Mainly due to photo/education errors
- **Name mismatch**: Must match 10th certificate EXACTLY (including spelling)
- **Payment failure**: Wait 30 min before retry; duplicate debits common
- **Correction window**: Opens 2-3 days after closure; limited fields editable
  - Can correct: Name spelling (minor), photo/signature (if rejected), exam center
  - Cannot correct: DOB, educational qualification, applied posts
- **Portal timeouts**: Submit 3-5 days before deadline
- **Wrong category**: Cannot be changed later — verify before applying
- **Photo rejection**: Most common issue (25% of problems) — ensure correct background, face visibility

---

## 4. IBPS (Institute of Banking Personnel Selection) <a name="4-ibps"></a>

**Portal**: `https://www.ibps.in` (info) | `https://ibpsreg.ibps.in` (registration)
**Backend**: IBPS own system (not NIC), specialized for banking recruitment
**Registration URLs vary by exam**: `ibpsreg.ibps.in/crppo{exam_code}`

### Registration Flow

1. **Visit IBPS Registration Portal**: `https://ibpsreg.ibps.in/crp{exam_code}/`
2. **Click "New Registration"**
3. **Enter Basic Details**:
   - Name, Father's Name, Mother's Name
   - Date of Birth
   - Gender
   - Category
   - Nationality
   - Mobile Number, Email ID
4. **OTP Verification**: Sent to mobile and email
5. **Upload Photograph, Signature, and Left Thumb Impression**:
   - Photograph via webcam/mobile capture OR file upload
   - Signature scanned
   - Left thumb impression scanned
6. **Registration Number Generated**
7. **Login with Registration Number + Password**
8. **Fill Application Form**:
   - Personal Details
   - Educational Qualifications
   - Work Experience (if any)
   - Language Proficiency
   - Post Preferences
   - Exam Center Preferences
9. **Fee Payment**
10. **Final Submission**

### Application Form Fields

**Personal Details:**
- Name (as per certificates)
- Father's / Husband's Name
- Mother's Name
- Date of Birth
- Gender
- Marital Status
- Category (SC/ST/OBC-CL/OBC-NCL/General/EWS)
- Nationality
- PwD status and type
- Ex-Servicemen / Disabled Ex-Servicemen

**Identity:**
- Aadhaar Number
- PAN Number
- Photo ID type and number

**Education:**
- 10th / SSLC (Board, Year, Percentage)
- 12th / HSC (Board, Year, Percentage)
- Graduation (University, College, Year, Stream, Percentage/CGPA)
- Post-Graduation
- Professional Qualifications (CA/CS/CMA etc.)
- Computer Literacy (Diploma/Degree in Computer)

**Language:**
- Language proficiency (read/write/speak)
- State/UT of domicile (determines regional language for interview)

**Experience:**
- Work experience in banking/financial sector
- Years of experience

**Exam Preferences:**
- State/UT preference for posting
- Bank preference (for PO/Clerk — up to 4-5 banks in order)
- Exam center (3 choices)

**For IBPS RRB:**
- Office Assistant vs Officer Scale I/II/III preference
- Regional Rural Bank preference

### Document Upload Requirements

| Document | Format | Size | Dimensions |
|----------|--------|------|------------|
| Photograph | JPG/JPEG | 20 KB - 50 KB | 200 × 230 pixels |
| Signature | JPG/JPEG | 10 KB - 20 KB | 140 × 60 pixels |
| Left Thumb Impression | JPG/JPEG | 10 KB - 20 KB | 240 × 240 pixels |
| Hand-written Declaration | JPG/JPEG | 50 KB - 100 KB | 800 × 400 pixels |
| Category Certificate | PDF | Up to 500 KB | N/A |

**Photo Specifications:**
- Recent color photograph
- White background
- Face should cover 60-70% of photo
- No cap, mask, or glasses
- Webcam capture option available during registration

**Signature Specifications:**
- Black ink on white paper
- Clear and legible
- Only the signature, no extra markings

**Left Thumb Impression:**
- Clear impression on white paper
- Blue/black ink
- Must be left thumb specifically

**Hand-written Declaration:**
- Specific text provided by IBPS
- Must be in candidate's own handwriting
- In English
- Black ink on white paper

### Payment Flow

1. Complete application form
2. Proceed to payment:
   - **Online Payment**: Debit Card, Credit Card, Net Banking, UPI
3. Fee: ₹175 (SC/ST/PwD), ₹850 (General/OBC/EWS) for most exams
4. Payment gateway: Integrated (typically via BillDesk or similar)
5. Transaction ID generated upon successful payment

### Captcha/OTP Details
- **Captcha**: Image-based CAPTCHA on all entry points
- **OTP**: Required for registration verification (mobile + email)
- **Re-captcha**: Sometimes uses Google reCAPTCHA v2

### Form URL Structure
```
https://ibpsreg.ibps.in/crp{exam_code}/
https://ibpsreg.ibps.in/crppoxvjun25/  (example: PO XIV)
https://ibpsreg.ibps.in/crpclerkxiv25/  (example: Clerks XIV)
https://ibpsreg.ibps.in/crprrbsxiv25/  (example: RRBs XIV)
```

### Common Issues & Workarounds
- **Photo/signature rejection**: Very strict validation; use the IBPS guidelines PDF for exact specs
- **Hand-written declaration errors**: Must match exact text provided; in own handwriting
- **Payment issues**: Use latest browser; disable popup blockers
- **Browser compatibility**: Chrome and Firefox recommended
- **Registration ID not received**: Check spam folder; may take a few minutes
- **Multiple applications**: Only last application considered; don't submit multiple

---

## 5. State PSC Portals <a name="5-state-psc-portals"></a>

**Key Portals:**
| State | Portal | URL |
|-------|--------|-----|
| Uttar Pradesh (UPPSC) | e-Pariksha OTR | `https://otr.pariksha.nic.in` |
| Bihar (BPSC) | BPSC Online | `https://bpsc.bih.nic.in` |
| Madhya Pradesh (MPPSC) | MPPSC Online | `https://www.mppsc.mp.gov.in` |
| Rajasthan (RPSC) | RPSC Online | `https://rpsc.rajasthan.gov.in` |
| Maharashtra (MPSC) | MPSC Online | `https://mpsc.gov.in` |
| West Bengal (WBPSC) | PSCWB | `https://pscwbapplication.in` |
| Tamil Nadu (TNPSC) | TNPSC Online | `https://www.tnpsc.gov.in` |
| Karnataka (KPSC) | KPSC Online | `https://kpsc.kar.nic.in` |
| Kerala (KPSC) | Kerala PSC | `https://www.keralapsc.gov.in` |
| Andhra Pradesh (APPSC) | APPSC | `https://psc.ap.gov.in` |
| Telangana (TSPSC) | TSPSC | `https://www.tspsc.gov.in` |

### Common Backend: NIC's e-Pariksha OTR Platform

**Key Finding**: Many State PSCs use **NIC's e-Pariksha OTR (One-Time Registration) platform** hosted at `otr.pariksha.nic.in`. This is a shared NIC infrastructure.

**e-Pariksha OTR Registration Flow:**

1. **Visit**: `https://otr.pariksha.nic.in`
2. **Select PSC**: Choose which PSC to register for (e.g., UPPSC)
3. **Registration**:
   - Valid Email ID
   - Valid Mobile Number
   - Aadhaar Number (last 6 digits)
   - Personal Details
4. **Login Options**: Email ID / Mobile Number / OTR Number
5. **Verify Details**: Email OTP + Mobile OTP
6. **Fill Sections**:
   - Personal Details
   - Other Details
   - Communication Details
   - Qualification Details
   - Experience Details
   - Photo & Signature
7. **Admin Validation**: Applicant's details and photo/signature validated
8. **OTR Number Generated**: Use this for all future applications

**OTR Statistics (as of research date):**
- ~34 lakh registrations
- ~34 lakh validated
- ~34 lakh OTR generated

### Common Application Fields Across State PSCs

**Personal:**
- Name, DOB, Gender, Father/Husband Name, Mother Name
- Category (SC/ST/OBC/General)
- Nationality, Domicile
- Aadhaar Number

**Education:**
- All qualification details from 10th onwards
- University/Board, Year, Percentage/Grade

**Experience:**
- Government/Non-government experience
- Designation, Department, Duration

**Exam-Specific:**
- Post applied for
- Exam center preference
- Optional subject (for state civil services)

### State PSC Payment Flow
- Most use online payment (Debit/Credit/Net Banking/UPI)
- Some accept e-Challan at designated banks
- Fee varies widely by state and category
- SC/ST/PwD usually exempt or reduced fee

### Common Issues
- **OTP delays**: Common across all state portals
- **Portal downtime**: State portals frequently go down during peak application periods
- **Photo upload issues**: Each state has slightly different specs
- **Aadhaar linking issues**: Some states mandate Aadhaar; others don't
- **Browser compatibility**: Many state portals have poor mobile support

---

## 6. NCS (National Career Service) <a name="6-ncs"></a>

**Portal**: `https://www.ncs.gov.in`
**Ministry**: Ministry of Labour & Employment, Government of India
**Version**: 6.18 (as of research date)

### Registration Flow

1. **Visit**: `https://www.ncs.gov.in`
2. **Job Seeker Registration**:
   - Create account with mobile number/email
   - OTP verification
   - Fill personal details
   - Upload resume
   - Add skills and qualifications
3. **Complete Profile**:
   - Personal information
   - Educational background
   - Work experience
   - Skills
   - Preferred job categories
   - Preferred locations
4. **Search and Apply**: Browse government and private job listings

### Key Difference from Other Portals
- **NCS is a job portal, NOT an exam portal**: It aggregates job listings (govt + private)
- **Does NOT host application forms** for SSC/UPSC/RRB etc.
- **Primary function**: Job matching, career counseling, job fairs
- **Government jobs listed** link to respective portal (SSC/UPSC/etc.)

### NCS Registration Fields

**Personal:**
- Name, DOB, Gender
- Mobile (OTP verified), Email
- Aadhaar (optional)
- Address with PIN code

**Education:**
- Highest qualification
- Board/University, Year of passing
- Percentage/CGPA

**Employment:**
- Current employment status
- Previous work experience
- Skills (tagged from predefined list)

**Preferences:**
- Desired job type (Full-time/Part-time/Contractual)
- Preferred industry
- Preferred location
- Expected salary range

### Document Upload
- Resume/CV (PDF, up to 2 MB)
- Photo (optional for profile)
- Certificates (optional)

### Payment
- **Free**: No fee for job seekers
- Employers pay for premium listings

### Captcha/OTP
- OTP for mobile and email verification
- Standard image CAPTCHA

### URL Structure
```
https://www.ncs.gov.in/
https://www.ncs.gov.in/job-seeker/register
https://www.ncs.gov.in/job-seeker/login
https://www.ncs.gov.in/search/jobs
```

---

## 7. Employment News <a name="7-employment-news"></a>

**Portal**: `https://employmentnews.gov.in`
**Ministry**: Ministry of Information and Broadcasting
**Publication**: Weekly journal "Employment News" / "Rozgar Samachar"

### Nature of Portal
- **Informational only** — NOT an application portal
- Lists government job vacancies from various departments
- Provides links to respective application portals
- Does NOT have its own application system

### Portal Features
1. **Job Listings**: Aggregated from all govt departments
2. **Search by Category**: Defence, Railways, Banking, Teaching, etc.
3. **Search by Date**: Weekly edition listings
4. **Search by Organization**: Filter by specific department
5. **Direct Links**: Each listing links to the actual application portal

### URL Structure
```
https://employmentnews.gov.in/
https://employmentnews.gov.in/newemp/AllJobs.aspx?k=All
https://employmentnews.gov.in/newemp/home.aspx
```

### Value for Automation
- **Good for monitoring**: Can scrape to detect new job postings
- **Links to actual portals**: Provides direct URLs to application pages
- **Structured data**: Job title, organization, last date, vacancy count

---

## NIC Infrastructure Analysis <a name="nic-infrastructure"></a>

### NIC (National Informatics Centre) Role

NIC is the primary IT infrastructure provider for Indian government services. Many recruitment portals use NIC-hosted systems.

### Identified NIC Platforms

| Platform | Used By | URL Pattern |
|----------|---------|-------------|
| **e-Pariksha OTR** | UPPSC, and other State PSCs | `otr.pariksha.nic.in` |
| **SSC Portal** | SSC | `ssc.gov.in` (NIC hosted) |
| **State PSC Portals** | Various State PSCs | `*.nic.in` domains |
| **NIC Cloud/DevOps** | Various govt services | `cloud.nicsi.nic.in` |

### Common NIC Patterns
1. **Domain**: All use `.nic.in` or `.gov.in` domains
2. **Hosting**: NIC data centers (government-owned)
3. **SSL Certificates**: Government-issued, may cause browser warnings
4. **Technology Stack**: 
   - ASP.NET / Java backend
   - Oracle / SQL Server databases
   - Server-side rendering (traditional, not SPA)
5. **Payment Integration**: SBI ePay or SBI Collect
6. **OTP Service**: NIC's own SMS gateway or government SMS gateway

### NOT Common Backend
- **SSC**: Has its own new portal (recently redesigned)
- **UPSC**: Has its own IT system (recently tendered for revamp)
- **IBPS**: Completely independent system
- **RRB**: Semi-centralized but uses own platform

### Key Insight for Automation
> There is NO single common API or backend across all Indian govt job portals. Each has its own system. The closest thing to a shared platform is NIC's e-Pariksha OTR used by some State PSCs. For automation, each portal needs individual integration.

---

## Summary: Automation Feasibility Matrix

| Portal | Difficulty | Captcha | OTP | Live Photo | API Available | Notes |
|--------|-----------|---------|-----|------------|---------------|-------|
| SSC | High | Yes (image) | Yes (mobile+email) | Yes (webcam) | No public API | Live photo capture is anti-automation measure |
| UPSC | High | Yes (image) | Yes (mobile+email) | No | No public API | Explicitly says no mobile compatibility |
| RRB | High | Yes (image) | Yes (mobile+email) | No | No public API | 40% rejection rate from errors |
| IBPS | High | Yes (image+reCAPTCHA) | Yes (mobile+email) | Yes (webcam/mobile) | No public API | Strict validation on all uploads |
| State PSCs | Medium-High | Varies | Yes | Varies | No public API | e-Pariksha OTR is shared platform |
| NCS | Low | Yes | Yes | No | No public API | Job listing portal only, free |
| Employment News | Very Low | No | No | No | No public API | Informational only, scrape-able |

### Key Automation Challenges
1. **Image CAPTCHA on all portals** — requires CAPTCHA solving service or manual intervention
2. **OTP verification** — requires access to registered mobile/email
3. **Live photo capture** (SSC) — webcam required, blocks pre-captured photo upload
4. **No public APIs** — all interaction must be via browser automation
5. **Session timeouts** — short sessions, forms must be completed quickly
6. **Browser-specific rendering** — government portals often work best on specific browsers
7. **SSL certificate warnings** — government SSL certs may require exception handling
8. **Peak-time server issues** — portals crash during high-traffic application periods
9. **No standardized form structure** — each portal has different field names, layouts, flows
10. **Aadhaar verification** — increasingly mandatory, adds complexity

### Recommended Approach
For any automation tool:
1. **Browser automation** (Playwright/Puppeteer) for form filling
2. **Manual CAPTCHA solving** or CAPTCHA-solving API integration
3. **OTP interception** via registered email API (IMAP) or SMS gateway
4. **Pre-validated document library** (photos/signatures pre-sized to each portal's specs)
5. **Form field mapping** per portal — maintain a config file for each portal
6. **Error recovery** — retry logic for payment failures, session timeouts
