# FounderOS LinkedIn Studio

> **Personal LinkedIn Content Command Center for Technology Founders**  
> Powered by **Groq AI**, **GitHub REST API**, and the **Official LinkedIn API**.  
> Features the complete editorial writing framework and V3 Humanizer audit from [sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills).

---

## 🚀 Key Features

* **Complete Web Dashboard**: Responsive, clean admin application built with **React**, **TypeScript**, and **Tailwind CSS**, served directly by **FastAPI**.
* **9 Dedicated Control Pages**:
  1. **Overview**: Live operational metrics, platform health, next 7 scheduled topics, and recent publications.
  2. **Content Calendar**: Interactive 30-day schedule showing pillar assignments and outbox draft statuses.
  3. **Drafts & Queue**: Searchable outbox table with live character count, audit state, and status tags.
  4. **New Post**: Custom generation studio with pillar selector, objective controls, and instant preview.
  5. **Draft Editor**: Side-by-side editing interface with realistic LinkedIn feed preview, live V3 humanizer safety audit, and cryptographic approval locking.
  6. **Research & Sources**: Live Groq browser-search records, citation tracking, and verified evergreen background data.
  7. **Content Strategy**: Visual distribution of the 8 founder content pillars, company fact isolation, and brand voice guidelines.
  8. **Publishing History**: Verified archive of confirmed published posts with LinkedIn Post URNs.
  9. **Run Logs & Settings**: Redacted operational logs, publishing safety modes, and emergency pause controls.
* **V3 Humanizer Heuristics & Editorial Safety**:
  * Detects and removes AI clichés (*"delve"*, *"game-changer"*, *"testament"*, *"revolutionize"*).
  * Enforces paragraph AI vocabulary density $\le 3.0\%$.
  * Em-dash limiter ($\le 1$ per 100 words).
  * Eliminates reveal bridges (*"Here's why:"*, *"Plot twist:"*, *"Let that sink in"*).
  * Eliminates false sincerity announcements (*"Full transparency"*, *"I'll be honest"*).
  * Blocks external URLs in post bodies to avoid LinkedIn algorithm distribution penalties.
* **Anti-Hallucination Fact Isolation**:
  * Company facts for **KodeToCareer** and **Viato** are strictly confined to verified claims in `config/company_facts.yaml`. The engine is strictly forbidden from inventing metrics, customer quotes, or fictitious features.
* **At-Most-Once Publishing Guard**:
  * Dual-layer gate: Dashboard confirmation modal + server-side environment checks (`AUTO_PUBLISH=true` and `DRY_RUN=false`).
  * Optimistic concurrency state claiming before calling LinkedIn. Ambiguous timeouts are marked `UNKNOWN` and never retried.

---

## 📁 Repository Structure

```
.
├── frontend/                     # React + TypeScript + Vite + Tailwind CSS Dashboard
│   ├── src/
│   │   ├── components/           # Navbar, Sidebar, Modal, UI primitives
│   │   ├── layouts/              # DashboardLayout with responsive sidebar
│   │   ├── pages/                # 10 pages: Overview, Calendar, Drafts, Editor, etc.
│   │   ├── lib/                  # ApiClient, TypeScript types
│   │   └── styles/               # Tailwind & custom CSS
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── app/                          # FastAPI Backend & Automation Core
│   ├── api.py                    # REST API routes under /api/v1/*
│   ├── auth.py                   # Single-founder bcrypt auth & HMAC session management
│   ├── static.py                 # Static files & Single Page Application fallback router
│   ├── config.py                 # Pydantic settings & secret redaction
│   ├── content.py                # Prompt builder & 2-pass draft repair
│   ├── github_state.py           # GitHub Contents API & optimistic concurrency
│   ├── groq_client.py            # Groq chat completion SDK client
│   ├── linkedin_client.py        # Official LinkedIn Posts & UGC API client
│   ├── main.py                   # CLI entrypoint for Render Cron Job
│   ├── models.py                 # Pydantic data schemas
│   ├── research.py               # Groq browser search tool & evergreen fallback
│   ├── safety.py                 # V3 Humanizer audit & formatting scrubber
│   └── topic_rotation.py         # 30-day Asia/Kolkata rotation engine
├── config/                       # Editable Brand & Company Configurations
│   ├── brand_profile.md          # Personal brand voice & guidelines
│   ├── company_facts.yaml        # Verified facts for KodeToCareer & Viato
│   ├── content_pillars.yaml      # 8 content pillars & 30-day schedule
│   └── verified_sources.yaml     # Curated technical sources
├── prompts/                      # Editorial & System Documentation
│   ├── system_writer.md
│   ├── humanizer.md
│   └── audit.md
├── scripts/
│   ├── bootstrap_state_branch.py # Initializer for GitHub automation-state branch
│   └── get_linkedin_token.py     # OAuth token & Author URN generator
├── tests/                        # 53 Automated unit tests (100% offline mocks)
├── render.yaml                   # Dual-service Render Blueprint (Web + Cron Job)
├── requirements.txt              # Production Python dependencies
├── THIRD_PARTY_NOTICES.md        # MIT license notice for upstream linkedin-skills
└── .env.example                  # Environment variable reference template
```

---

## 🛠️ Local Development

### 1. Prerequisites
* **Python 3.11+** or **3.12**
* **Node.js 18+** and **npm**

### 2. Setup Environment
```bash
# Clone the repository
git clone https://github.com/KAYHANH/linkedin-automation.git
cd linkedin-automation

# Install Python backend dependencies
pip install -r requirements.txt

# Install frontend dependencies and build assets
cd frontend
npm install
npm run build
cd ..
```

### 3. Configure `.env`
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate your credentials:
```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.8-27b
GITHUB_TOKEN=ghp_...
GITHUB_REPOSITORY=username/repo-name
LINKEDIN_ACCESS_TOKEN=AQ...
LINKEDIN_AUTHOR_URN=urn:li:person:YOUR_URN
DASHBOARD_USERNAME=founder
```

### 4. Running the Application
You can run the web dashboard in two ways:

#### Option A: Unified Production Mode (FastAPI serves UI & API)
```bash
uvicorn app.api:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000).  
Log in with your credentials (Default in local dev: `founder` / `founder123`).

#### Option B: Vite Hot-Reload Development
* Terminal 1 (Backend API):
  ```bash
  uvicorn app.api:app --reload --port 8000
  ```
* Terminal 2 (Frontend Dev Server):
  ```bash
  cd frontend
  npm run dev
  ```
  Open [http://localhost:5173](http://localhost:5173).

---

## 🧪 Testing

Run all 53 automated tests:
```bash
python -m pytest tests -v
```

Run manual dry-run generation:
```bash
python -m app.main --dry-run
```

---

## ☁️ Deployment on Render

This repository includes a multi-service `render.yaml` Blueprint:

1. **Web Service (`founderos-linkedin-studio`)**:
   * Runs FastAPI and serves the compiled React dashboard.
   * Plan: Free / Starter.
2. **Cron Job (`groq-linkedin-daily-publisher`)**:
   * Runs daily at `30 3 * * *` UTC (09:00 AM Asia/Kolkata).
   * Generates, audits, and persists content to your GitHub state branch.

### Deployment Steps:
1. Push your repository to GitHub.
2. Log in to [dashboard.render.com](https://dashboard.render.com).
3. Click **New +** $\rightarrow$ **Blueprint**.
4. Select your GitHub repository (`KAYHANH/linkedin-automation`).
5. Fill in the secrets prompted by Render:
   * `GROQ_API_KEY`
   * `GITHUB_TOKEN`
   * `GITHUB_REPOSITORY`
   * `LINKEDIN_ACCESS_TOKEN`
   * `LINKEDIN_AUTHOR_URN`
   * `DASHBOARD_PASSWORD_HASH`
   * `SESSION_SECRET`
6. Click **Apply**.

---

## ⚠️ Service Limits & Quotas

* **Groq API**: Free tier provides generous rate limits but enforces Tokens Per Day (TPD) caps. Recommended model: `qwen/qwen3.8-27b`.
* **LinkedIn API**: Official member access tokens are valid for **60 days**. When expired, regenerate using `python scripts/get_linkedin_token.py`.
* **GitHub REST API**: Standard personal access tokens provide 5,000 requests per hour. State writes use optimistic concurrency (`sha` matching) to guarantee at-most-once consistency.
* **Render Free Tier**: Render Web Services spin down after 15 minutes of inactivity on the free tier. Render Cron Jobs require a Starter plan under current Render terms.

---

## 📄 License
This application is distributed under the **MIT License**. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for upstream attributions.
