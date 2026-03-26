#!/usr/bin/env python3
"""
🎯 NIDHI'S JOB SNIPER — Scans 110+ company ATS feeds every 5 min
Finds DE/DA roles at Hour 0, before LinkedIn/Indeed.
Discord alerts + Claude auto-drafts application materials.

Usage:
  python job_sniper.py          # Continuous local loop (every 5 min)
  python job_sniper.py --once   # Single scan pass (for GitHub Actions)
"""

import os, json, time, hashlib, logging, re, sys
import requests
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ═══════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
SEEN_FILE = Path("seen_jobs.json")
DRAFTS_DIR = Path("job_drafts")
DRAFTS_DIR.mkdir(exist_ok=True)

log = logging.getLogger("sniper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

# ═══════════════════════════════════════════════════════════
# FILTERING — Two lanes: DE and DA
# ═══════════════════════════════════════════════════════════

TITLE_INCLUDE = [
    "data engineer", "analytics engineer", "data analyst",
    "business intelligence", "bi engineer", "bi analyst",
    "etl developer", "elt engineer", "pipeline engineer",
    "data platform", "data infrastructure",
]

TITLE_EXCLUDE = [
    "senior", "staff", "principal", "lead", "manager", "director",
    "vp", "head of", "machine learning engineer", "mle",
    "software engineer", "sde", "swe", "frontend", "backend",
    "ios", "android", "security", "devops", "sre", "intern",
    "ph.d", "phd", "distinguished", "iii", " iv", " v ",
]

LOCATIONS_INCLUDE = [
    "remote", "united states", "usa", "us", "new york", "nyc",
    "san francisco", "sf", "bay area", "seattle", "austin",
    "chicago", "boston", "denver", "los angeles", "la",
    "washington", "dc", "atlanta", "dallas", "houston",
    "portland", "minneapolis", "philadelphia", "pittsburgh",
    "buffalo", "anywhere", "hybrid",
]

# ═══════════════════════════════════════════════════════════
# 110+ COMPANIES BY ATS PLATFORM
# ═══════════════════════════════════════════════════════════

GREENHOUSE = [
    "airbnb", "airtable", "brex", "canva", "chime", "cloudflare",
    "cockroachlabs", "coinbase", "confluent", "coursera",
    "databricks", "datadog", "discord", "doordash", "dropbox",
    "duolingo", "figma", "gusto", "hubspot", "instacart",
    "intercom", "klarna", "lyft", "mapbox", "medium",
    "netlify", "newrelic", "notion", "okta",
    "opendoor", "openai", "pagerduty", "palantir", "pinterestcareers",
    "plaid", "postman", "quora", "ramp", "readme",
    "reddit", "relativityhq", "retool", "rippling", "robinhood",
    "scale", "sentry", "shopify", "smartsheet",
    "snap", "snowflake", "snyk", "sourcegraph",
    "spotify", "square", "stripe", "supabase",
    "tableau", "tiktok", "toast", "twilio", "twitch",
    "uber", "vercel", "wayfair", "webflow", "wiz",
    "zapier", "zendesk", "zscaler", "chewy",
]

LEVER = [
    "netflix", "dbtlabs", "fivetran", "prefect", "anduril",
    "samsara", "benchling", "faire", "lacework", "mux",
    "nerdwallet", "orca-security", "replit",
    "tempus", "truelayer", "vanta",
]

ASHBY = [
    "anthropic", "cursor", "perplexity", "pinecone", "posthog",
    "runway", "weights-and-biases", "linear", "beamery",
    "clay", "coreweave", "deepgram", "eleven-labs", "glean",
    "labelbox", "materialize", "modal", "motherduck", "neon",
    "qdrant", "resend", "stainless",
    "together-ai", "trigger-dev", "turso",
    "upstash", "val-town", "warp",
]

# ═══════════════════════════════════════════════════════════
# NIDHI'S PROFILE — For auto-drafting
# ═══════════════════════════════════════════════════════════

PROFILE = """Name: Nidhi Rajani
Target: Data Engineer / Data Analyst / Analytics DS
Visa: F1 STEM OPT (3-year work authorization from June 2026)

EXPERIENCE:
Flipkart (Walmart subsidiary) | Feb–Dec 2024
• $1.8M revenue impact — PAN-India SIM card delivery platform, Best Innovation Award
• 99.2% uptime across 10M+ daily transactions
• Power BI dashboards, Pareto analysis improving delivery rates 35%→68%
• API orchestration with Airtel KYC portal, open-box fraud prevention
• B2B logistics coordination for Paytm device collection

Teaching Assistant | University at Buffalo | Jan 2026–Present

EDUCATION: MS-ESDS, University at Buffalo (June 2026) | BTech CS, NIT Bhopal

PROJECTS:
• Two-Tower Rec System (HR@10=0.7285, FAISS 29μs/query, 98K users)
• Global Food Platform (PostgreSQL, dbt, Airflow, Streamlit)
• IoT Malware Detection (99.56% accuracy, GNN+GAN, 76K flows)

SKILLS: Python, SQL, PySpark, Airflow, dbt, PostgreSQL, Snowflake,
Docker, Git, Spark, Pandas, TensorFlow, PyTorch, Power BI, AWS

RESUME RULES:
- Metrics in first 8 words of every bullet
- 15-25 words max per bullet
- Format: [Metric/Result] — [How] — [Scale/Context]
"""

# ═══════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════

@dataclass
class Job:
    title: str
    company: str
    location: str
    url: str
    description: str = ""
    posted_at: str = ""
    source: str = ""
    job_id: str = ""

    @property
    def uid(self) -> str:
        return hashlib.md5(f"{self.company}:{self.title}:{self.url}".encode()).hexdigest()

    def matches(self) -> bool:
        t = self.title.lower()
        loc = self.location.lower()
        title_ok = any(kw in t for kw in TITLE_INCLUDE)
        title_blocked = any(ex in t for ex in TITLE_EXCLUDE)
        loc_ok = not self.location or any(l in loc for l in LOCATIONS_INCLUDE)
        return title_ok and not title_blocked and loc_ok

# ═══════════════════════════════════════════════════════════
# SEEN TRACKER (persists to JSON)
# ═══════════════════════════════════════════════════════════

class SeenTracker:
    def __init__(self):
        self.seen: set = set()
        if SEEN_FILE.exists():
            self.seen = set(json.loads(SEEN_FILE.read_text()).get("seen", []))

    def is_new(self, job: Job) -> bool:
        if job.uid in self.seen:
            return False
        self.seen.add(job.uid)
        SEEN_FILE.write_text(json.dumps({"seen": list(self.seen)}))
        return True

# ═══════════════════════════════════════════════════════════
# ATS FETCHERS
# ═══════════════════════════════════════════════════════════

def fetch_greenhouse(slug: str) -> list:
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=10)
        if r.status_code != 200: return []
        jobs = []
        for j in r.json().get("jobs", []):
            job = Job(
                title=j.get("title", ""),
                company=slug,
                location=j.get("location", {}).get("name", ""),
                url=j.get("absolute_url", ""),
                posted_at=j.get("updated_at", ""),
                source="greenhouse",
                job_id=str(j.get("id", "")),
            )
            if job.matches(): jobs.append(job)
        return jobs
    except: return []


def fetch_lever(slug: str) -> list:
    try:
        r = requests.get(f"https://api.lever.co/v0/postings/{slug}", timeout=10)
        if r.status_code != 200: return []
        jobs = []
        for j in r.json():
            job = Job(
                title=j.get("text", ""),
                company=slug,
                location=j.get("categories", {}).get("location", ""),
                url=j.get("hostedUrl", ""),
                posted_at=str(j.get("createdAt", "")),
                source="lever",
                job_id=str(j.get("id", "")),
            )
            if job.matches(): jobs.append(job)
        return jobs
    except: return []


def fetch_ashby(slug: str) -> list:
    try:
        r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}", timeout=10)
        if r.status_code != 200: return []
        jobs = []
        for j in r.json().get("jobs", []):
            loc = j.get("location", "")
            if isinstance(loc, dict): loc = loc.get("name", "")
            job = Job(
                title=j.get("title", ""),
                company=slug,
                location=str(loc),
                url=j.get("jobUrl", j.get("applyUrl", "")),
                posted_at=j.get("publishedAt", ""),
                source="ashby",
                job_id=str(j.get("id", "")),
            )
            if job.matches(): jobs.append(job)
        return jobs
    except: return []

# ═══════════════════════════════════════════════════════════
# JOB DESCRIPTION FETCHER
# ═══════════════════════════════════════════════════════════

def fetch_description(job: Job) -> str:
    try:
        if job.source == "greenhouse" and job.job_id:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{job.company}/jobs/{job.job_id}",
                timeout=10
            )
            if r.status_code == 200:
                return re.sub(r'<[^>]+>', ' ', r.json().get("content", ""))[:3000]
        elif job.source == "lever" and job.job_id:
            r = requests.get(
                f"https://api.lever.co/v0/postings/{job.company}/{job.job_id}",
                timeout=10
            )
            if r.status_code == 200:
                parts = []
                for lst in r.json().get("lists", []):
                    parts.append(lst.get("text", ""))
                    for item in lst.get("content", ""):
                        parts.append(f"  - {item}")
                return "\n".join(parts)[:3000]
    except: pass
    return ""

# ═══════════════════════════════════════════════════════════
# CLAUDE AUTO-DRAFTER
# ═══════════════════════════════════════════════════════════

def draft_materials(job: Job) -> str:
    if not ANTHROPIC_API_KEY:
        return "⚠️ Set ANTHROPIC_API_KEY in .env for auto-drafting"

    desc = fetch_description(job)

    prompt = f"""You are a job application strategist for Nidhi Rajani.

PROFILE:
{PROFILE}

JOB:
Company: {job.company} | Title: {job.title} | Location: {job.location}
URL: {job.url}
Description: {desc if desc else 'Not available — infer from title/company'}

Generate ALL of the following (be specific, not generic):

1. **RESUME LANE**: DE or DA?
2. **FLIPKART TITLE REWRITE** for this JD
3. **4 TAILORED RESUME BULLETS** (metrics first 8 words, 15-25 words, result-first)
4. **SKILLS ORDER** reordered to match JD
5. **TOP 3 PROJECTS** ranked by relevance
6. **ATS SCORE** /100 with reasoning
7. **6-SEC SCAN VERDICT**: Keep or reject?
8. **COVER LETTER** (200 words, company-specific hook)
9. **LINKEDIN MSG TO ENGINEER** (80 words)
10. **LINKEDIN MSG TO RECRUITER** (60 words)
11. **FOLLOW-UP** (for day 5)
12. **HIRING MANAGER EMAIL** (subject + 150 words)
13. **LINKEDIN SEARCH QUERIES** (3 exact queries to find people)
14. **RED FLAGS**: Visa issues, mismatches?
"""

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2500,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["content"][0]["text"]
        return f"⚠️ Claude API error {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return f"⚠️ Draft failed: {e}"

# ═══════════════════════════════════════════════════════════
# DISCORD ALERT
# ═══════════════════════════════════════════════════════════

def send_discord(job: Job):
    if not DISCORD_WEBHOOK_URL: return

    # Build LinkedIn search queries
    company_clean = job.company.replace("-", " ").title()
    linkedin_searches = (
        f'1) "{company_clean}" "data engineer" site:linkedin.com/in\n'
        f'2) "{company_clean}" "recruiter" OR "talent" site:linkedin.com/in\n'
        f'3) "{company_clean}" "hiring manager" "data" site:linkedin.com/in'
    )

    # Build ready-to-paste Claude.ai prompt
    claude_prompt = (
        f"I found a new job posting. Help me apply.\n\n"
        f"Company: {company_clean}\n"
        f"Role: {job.title}\n"
        f"Location: {job.location}\n"
        f"URL: {job.url}\n\n"
        f"Do ALL of these:\n"
        f"1. Tell me: DE or DA resume lane?\n"
        f"2. Rewrite my Flipkart title for this JD\n"
        f"3. Write 4 tailored resume bullets (metrics first 8 words)\n"
        f"4. Reorder my skills to match JD\n"
        f"5. Pick top 3 projects by relevance\n"
        f"6. ATS score /100\n"
        f"7. 6-second recruiter scan verdict\n"
        f"8. Cover letter (200 words, hook opening, mention company)\n"
        f"9. LinkedIn message to an engineer on their DE team (80 words, "
        f"DON'T ask for referral directly — show genuine interest in their "
        f"work, mention what excites me about their stack, and what I bring)\n"
        f"10. LinkedIn message to recruiter (60 words)\n"
        f"11. Follow-up message for day 5\n"
        f"12. Hiring manager cold email (subject + 150 words)\n"
        f"13. Red flags / visa issues?"
    )

    try:
        # Message 1: Alert embed
        requests.post(DISCORD_WEBHOOK_URL, json={
            "embeds": [{
                "title": f"🎯 NEW: {job.title} @ {company_clean}",
                "url": job.url,
                "color": 0x00FF00,
                "fields": [
                    {"name": "📍 Location", "value": job.location or "N/A", "inline": True},
                    {"name": "🏗️ ATS", "value": job.source.upper(), "inline": True},
                    {"name": "⏰ Found", "value": datetime.now().strftime("%I:%M %p"), "inline": True},
                    {"name": "🔍 LinkedIn searches", "value": linkedin_searches, "inline": False},
                ],
                "footer": {"text": "⚡ Apply within 1 hour!"},
            }]
        }, timeout=10)

        # Message 2: Ready-to-paste Claude.ai prompt (plain text so she can copy)
        requests.post(DISCORD_WEBHOOK_URL, json={
            "content": f"📋 **Paste this into Claude.ai:**\n```\n{claude_prompt}\n```"
        }, timeout=10)

    except: pass

# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def scan_all():
    tracker = SeenTracker()
    new_jobs = []
    total = len(GREENHOUSE) + len(LEVER) + len(ASHBY)
    log.info(f"Scanning {total} companies...")

    for slug in GREENHOUSE:
        for job in fetch_greenhouse(slug):
            if tracker.is_new(job): new_jobs.append(job)

    for slug in LEVER:
        for job in fetch_lever(slug):
            if tracker.is_new(job): new_jobs.append(job)

    for slug in ASHBY:
        for job in fetch_ashby(slug):
            if tracker.is_new(job): new_jobs.append(job)

    return new_jobs


def process_job(job: Job):
    log.info(f"🎯 NEW: {job.title} @ {job.company} ({job.location})")
    log.info(f"   🔗 {job.url}")

    draft = draft_materials(job)

    safe = f"{job.company}_{job.title}".replace(" ", "_").replace("/", "-")[:60]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = DRAFTS_DIR / f"{ts}_{safe}.md"
    path.write_text(
        f"# {job.title} @ {job.company}\n"
        f"**URL:** {job.url}\n"
        f"**Location:** {job.location}\n"
        f"**Found:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
        f"**Source:** {job.source}\n\n---\n\n{draft}\n"
    )
    log.info(f"   📄 Saved: {path}")
    send_discord(job)


def run_once():
    log.info("=" * 50)
    log.info(f"🔍 SCAN — {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    new_jobs = scan_all()
    if new_jobs:
        log.info(f"🚨 {len(new_jobs)} NEW matches!")
        for job in new_jobs:
            process_job(job)
    else:
        log.info("No new jobs this scan.")
    return new_jobs


def run_loop():
    total = len(GREENHOUSE) + len(LEVER) + len(ASHBY)
    log.info("🛰️  JOB SNIPER ACTIVATED")
    log.info(f"📡 Monitoring {total} companies across 3 ATS platforms")
    log.info(f"📁 Drafts → {DRAFTS_DIR.absolute()}")
    log.info(f"🔔 Discord: {'✅' if DISCORD_WEBHOOK_URL else '❌ Set DISCORD_WEBHOOK_URL'}")
    log.info(f"🤖 Auto-draft: {'✅' if ANTHROPIC_API_KEY else '❌ Set ANTHROPIC_API_KEY'}")
    log.info("")
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Error: {e}")
        time.sleep(300)


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        run_loop()
