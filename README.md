# Groq-Powered LinkedIn Automation on Render

A reliable, cloud-native daily LinkedIn content generation and publishing engine powered by **Groq**, **Official LinkedIn APIs**, **GitHub REST API**, and **Render Cron Jobs**.

Adapted from the editorial frameworks and humanizer methodologies in [sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills) (MIT License) and built as an independent, testable Python system without third-party publishing brokers (no Publora, no TinyFish, no paid databases, no browser scraping).

---

## Architecture Overview

```
                                      [ Render Cron Job ]
                                (Daily at 09:00 Asia/Kolkata / 03:30 UTC)
                                                │
                                                ▼
                                         [ app.main CLI ]
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
          [ topic_rotation ]             [ research ]                    [ safety ]
       (30-day pillar cycle)         (Groq browser_search           (V3 humanizer audit,
                                      + evergreen fallback)         density, hook rules)
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                ▼
                                        [ content.py ]
                                   (Groq draft & repair)
                                                │
                               ┌────────────────┴────────────────┐
                               ▼                                 ▼
                     [ github_state.py ]               [ linkedin_client.py ]
                  Branch: automation-state             Official Posts API / UGC
              - automation_state/YYYY-MM-DD.json     (w_member_social scope)
              - automation_outbox/YYYY-MM-DD.md        At-most-once safety
              - automation_history/YYYY-MM-DD.json   (No automatic retries)
```

---

## 1. Local Installation

### Prerequisites
- Python 3.11 or 3.12
- Git

### Setup
```bash
# Clone or navigate to the workspace
cd groq-linkedin-automation

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# For testing and development
pip install -r requirements-dev.txt
```

---

## 2. Groq API Key Setup

1. Sign up or log in at [console.groq.com](https://console.groq.com/).
2. Navigate to **API Keys** and generate a new key (`gsk_...`).
3. Add the key to your `.env` file or Render environment settings:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key_here
   ```

---

## 3. Model Selection & Research Compatibility

- **Default Model:** `llama-3.3-70b-versatile`
  - High reasoning capability, fast inference on Groq LPUs, and supports server-side tool use (`browser_search`).
- **Alternative Model:** `llama-3.1-8b-instant`
  - Extremely fast and low latency; suitable for lightweight drafting.
- **Tool-Use Compatibility:**
  - The system utilizes Groq's official server-side `browser_search` tool (`tools=[{"type": "browser_search"}]`).
  - Web research and structured JSON generation are split into distinct pipeline stages.
  - If web search fails, is unsupported by the model, or `ENABLE_WEB_SEARCH=false`, the engine falls back gracefully to curated evergreen engineering topics defined in `config/verified_sources.yaml`. **The engine never pretends a source was checked if it was not.**

---

## 4. LinkedIn Developer App Creation

1. Visit the [LinkedIn Developer Portal](https://developer.linkedin.com/).
2. Click **Create App**.
3. Associate your app with a LinkedIn Company Page (mandatory verification step required by LinkedIn).
4. Fill in App details, upload a logo, and verify legal ownership.

---

## 5. "Share on LinkedIn" Product & Permissions

1. In your LinkedIn Developer App dashboard, open the **Products** tab.
2. Select **Share on LinkedIn** and request access.
3. The self-service product grants the required member posting permission:
   - `w_member_social`: Allows the application to post content on behalf of the authorized LinkedIn member.
4. If your app only has `openid`, `profile`, or `email` permissions, publishing will fail with HTTP 403 Forbidden. The system requires `w_member_social`.

---

## 6. OAuth Authorization & Token Lifecycle

1. Generate the authorization URL:
   ```
   https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=YOUR_REDIRECT_URI&scope=w_member_social%20openid%20profile
   ```
2. Authorize the application in your browser and retrieve the returned authorization code (`code=...`).
3. Exchange the code for an Access Token:
   ```bash
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -d "grant_type=authorization_code" \
     -d "code=YOUR_AUTH_CODE" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "redirect_uri=YOUR_REDIRECT_URI"
   ```
4. **Token Expiration:** LinkedIn member access tokens typically expire in **60 days**.
5. **Token Refresh:** If your developer application supports the `refresh_token` grant type, configure `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, and `LINKEDIN_REFRESH_TOKEN`. If programmatic refresh is unavailable for your app tier, calendar a manual reauthorization before the 60-day window closes.

---

## 7. How to Obtain the Author Member URN

The author URN must be in the format: `urn:li:person:MEMBER_ID`.

To find your Member ID:
1. Make an authenticated call using your access token to the userinfo endpoint:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" https://api.linkedin.com/v2/userinfo
   ```
2. The returned JSON contains the `"sub"` field (e.g., `"sub": "abcde12345"`).
3. Your `LINKEDIN_AUTHOR_URN` is:
   ```env
   LINKEDIN_AUTHOR_URN=urn:li:person:abcde12345
   ```

---

## 8. Selecting the API Endpoint Style

Configured via `LINKEDIN_ENDPOINT_STYLE`:
- `rest/posts` (Default & Modern):
  - Uses `POST https://api.linkedin.com/rest/posts`.
  - Requires `Linkedin-Version` header (e.g., `202501`) and `X-Restli-Protocol-Version: 2.0.0`.
- `v2/ugcposts` (Legacy Self-Serve):
  - Uses `POST https://api.linkedin.com/v2/ugcPosts`.
  - Formats content as `com.linkedin.ugc.ShareContent`.

---

## 9. GitHub Fine-Grained Token Permissions

Durable state is persisted directly in your GitHub repository on a dedicated branch (`automation-state`).

1. In GitHub, go to **Settings > Developer Settings > Personal Access Tokens > Fine-grained tokens**.
2. Create a token scoped to your target repository.
3. Grant **Repository permissions**:
   - `Contents`: **Read and write**
4. Store the token securely as `GITHUB_TOKEN`.

---

## 10. State Branch Initialization

Run the included bootstrap script to create the dedicated `automation-state` branch:
```bash
python scripts/bootstrap_state_branch.py
```
This ensures daily drafts, outbox markdown, and execution states are kept completely isolated from your main deployment code branch.

---

## 11. Render Blueprint Deployment

1. Push your repository to GitHub.
2. In [Render Dashboard](https://dashboard.render.com/), click **New > Blueprint**.
3. Select your repository. Render will automatically parse `render.yaml`.
4. Render schedules the Cron Job:
   - Schedule: `30 3 * * *` (03:30 UTC = 09:00 Asia/Kolkata).
   - Command: `python -m app.main --publish`.
5. Under the Cron Job settings in Render, populate the secret environment variables (`sync: false`):
   - `GROQ_API_KEY`
   - `GITHUB_TOKEN`
   - `GITHUB_REPOSITORY`
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_AUTHOR_URN`

---

## 12. Safe CLI Testing Modes

The CLI supports 4 operational modes:

### 1. Configuration Check
```bash
python -m app.main --check-config
```
Validates required settings across all modes and verifies secret hygiene without printing any sensitive credentials.

### 2. Dry Run (No Writes)
```bash
python -m app.main --dry-run
```
Runs the 30-day rotation, conducts research, generates a post via Groq, executes the safety audit, and prints the result to stdout. **Makes zero calls to GitHub or LinkedIn.**

### 3. Draft Mode (Save to GitHub Only)
```bash
python -m app.main --draft
```
Generates and audits the daily post, then records the draft and outbox markdown into the `automation-state` GitHub branch (`automation_state/YYYY-MM-DD.json` and `automation_outbox/YYYY-MM-DD.md`). **Makes zero calls to LinkedIn.**

### 4. Publish Mode
```bash
python -m app.main --publish
```
Only permitted when `AUTO_PUBLISH=true` and `DRY_RUN=false`. Claims the state in GitHub before calling LinkedIn, calls LinkedIn once, and confirms publication.

---

## 13. Explicitly Enabling Live Publishing

By default, the system is strictly locked to prevent accidental publishing:
- `AUTO_PUBLISH=false`
- `DRY_RUN=true`

To activate live daily publishing in Render:
1. In the Render Dashboard under **Environment**, set:
   - `AUTO_PUBLISH=true`
   - `DRY_RUN=false`
2. Save changes.

---

## 14. Emergency Pause via AUTO_PUBLISH=false

To immediately pause all publishing across all runs without redeploying code:
- In Render Dashboard or `.env`, set `AUTO_PUBLISH=false`.
- The runner will exit immediately with an audit log and make no LinkedIn API calls.

---

## 15. Duplicate Prevention & Ambiguous Timeout Reconciliation

### At-Most-Once Safety Model
When interacting with separate cloud services (Render, GitHub, and LinkedIn), distributed network timeouts can be ambiguous. The system guarantees **at-most-once** publication:

1. **Daily Claim:** Before making any HTTP request to LinkedIn, the system persists a `claimed` status to GitHub.
2. **Duplicate Check:** If today's state is already `claimed`, `published`, or `unknown`, the runner halts immediately.
3. **Ambiguous Timeout Safety:** If a network timeout occurs while waiting for LinkedIn's response:
   - The system **NEVER retries automatically**.
   - The state is marked as `unknown`.
   - The run exits with an alert for manual reconciliation.

### Manual Reconciliation Steps
If a state is marked `unknown`:
1. Check your personal LinkedIn profile to verify if the post was published.
2. If published: Update `automation_state/YYYY-MM-DD.json` on the `automation-state` branch: set `publication_status: "published"` and record the post URL/ID.
3. If not published: Update `publication_status: "failed"` to allow a retry on the next manual run.

---

## 16. Service Quotas, Free-Tier Conditions & Costs

| Service | Free-Tier Limits | Notes & Potential Costs |
| :--- | :--- | :--- |
| **Groq API** | Free beta tier with rate limits (RPM / TPM per model) | Subject to Groq's usage policies. Pay-as-you-go tiers apply if quotas are exceeded. |
| **LinkedIn API** | Standard Developer Quota (Share on LinkedIn) | Personal profile posting is generally free within reasonable rate limits (~100 posts/day). |
| **GitHub REST API**| 5,000 requests/hour with PAT | More than sufficient for daily state persistence (uses ~5 requests/day). |
| **Render** | Cron Jobs on Render require a paid plan or Starter instance | Free web services sleep; Cron Jobs may incur Render compute charges. Always verify Render pricing before deployment. |

---

## Attribution & Upstream Frameworks

This project adapts editorial concepts, hook formulas (F1–F20), founder angles (A1–A10), and the V3 humanizer audit rules from:
- **Repository:** [https://github.com/sergebulaev/linkedin-skills](https://github.com/sergebulaev/linkedin-skills)
- **Author:** Sergey Bulaev
- **License:** MIT License

*The LinkedIn API integration, GitHub state persistence, Groq tool-use research, and Render Cron Job automation in this repository are independent implementations developed without proprietary publishing intermediaries.*
