#!/usr/bin/env python3
"""
🎯 NIDHI'S JOB SNIPER v2 — Scans 200+ companies across 5 ATS platforms
Finds DE/DA/BI/new-grad roles at Hour 0, before LinkedIn/Indeed.
Discord alerts + Claude auto-drafts application materials.

ATS Platforms: Greenhouse, Lever, Ashby, SmartRecruiters, Workable
Includes: YC startups, Series A-D companies, major tech employers

Usage:
  python job_sniper.py          # Continuous local loop (every 5 min)
  python job_sniper.py --once   # Single scan pass (for GitHub Actions)
"""

import os, json, time, hashlib, logging, re, sys
import requests
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

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
# FILTERING — Two lanes: DE and DA + Junior/New Grad
# ═══════════════════════════════════════════════════════════

TITLE_INCLUDE = [
    # Core DE/DA roles
    "data engineer", "analytics engineer", "data analyst",
    "business intelligence", "bi engineer", "bi analyst",
    "bi developer", "bi specialist",
    "etl developer", "elt engineer", "pipeline engineer",
    "data platform", "data infrastructure",
    # Junior / New Grad / Entry-level signals
    "junior data", "associate data",
    "junior analytics", "associate analytics",
    "new grad data", "new grad analytics",
    "entry level data", "early career data",
    "data engineer i", "data analyst i",
    "data engineer ii", "data analyst ii",
    "analytics engineer i", "analytics engineer ii",
    # Adjacent data roles
    "data operations", "data ops", "dataops",
    "database engineer", "data quality",
    "data governance", "data warehouse",
    "reporting analyst", "insights analyst",
    "quantitative analyst", "decision scientist",
    "implementation engineer",
    # Agentic / AI-adjacent data roles (emerging 2026)
    "agentic analytics", "ai analytics engineer",
]

TITLE_EXCLUDE = [
    # Seniority (too senior)
    "senior", "sr.", "sr ", "staff", "principal", "lead",
    "manager", "director", "vp", "head of",
    "distinguished", "iii", " iv", " v ",
    # Wrong role type
    "machine learning engineer", "mle",
    "software engineer", "sde", "swe",
    "frontend", "backend", "full stack", "fullstack",
    "ios", "android", "security", "devops", "sre",
    "product designer", "product manager", "ux ",
    "distributed systems", "systems engineer",
    "solutions engineer", "solutions architect",
    "sales engineer", "customer engineer",
    "people team", "people analyst", "talent acquisition",
    "recruiter", "hr ", "marketing manager",
    "account executive", "customer success",
    # Too specialized / academic
    "ph.d", "phd", "research scientist",
    # Intern (separate from new grad)
    "intern ",
]

LOCATIONS_INCLUDE = [
    # US cities and states
    "remote", "united states", "new york", "nyc",
    "san francisco", "bay area", "seattle", "austin",
    "chicago", "boston", "denver", "los angeles",
    "washington", "atlanta", "dallas", "houston",
    "portland", "minneapolis", "philadelphia", "pittsburgh",
    "buffalo", "anywhere", "hybrid",
    "california", "texas", "colorado", "virginia",
    "massachusetts", "georgia", "illinois", "oregon",
    "pennsylvania", "minnesota", "arizona", "nevada",
    "las vegas", "phoenix", "san jose", "san diego",
    "raleigh", "charlotte", "nashville", "miami",
    "detroit", "salt lake", "indianapolis",
    "north carolina", "florida", "ohio", "michigan",
    "maryland", "connecticut", "new jersey", "utah",
    "wisconsin", "missouri", "tennessee", "kentucky",
    ", us", "usa", " us ", "(us)", "u.s.",
    ", ca", ", ny", ", tx", ", wa", ", co", ", il",
    ", ma", ", ga", ", va", ", or", ", pa", ", mn",
    ", az", ", nv", ", nc", ", fl", ", oh", ", mi",
]

LOCATIONS_EXCLUDE = [
    "mexico", "canada", "ireland", "ukraine", "india",
    "uk", "united kingdom", "london", "germany", "berlin",
    "france", "paris", "spain", "brazil", "singapore",
    "australia", "japan", "tokyo", "korea", "seoul",
    "china", "beijing", "shanghai", "hong kong", "taiwan",
    "israel", "tel aviv", "netherlands", "amsterdam",
    "sweden", "stockholm", "poland", "czech", "romania",
    "argentina", "colombia", "chile", "nigeria",
    "south africa", "kenya", "indonesia", "vietnam",
    "philippines", "thailand", "malaysia", "portugal",
    "remote - ireland", "remote - canada", "remote - mexico",
    "remote - uk", "remote - india", "remote - germany",
    "remote - brazil", "remote - australia",
    "remote - europe", "remote - apac", "remote - latam",
    "remote - emea", "remote - asia",
    "ontario", "toronto", "vancouver", "montreal",
    "bangalore", "hyderabad", "mumbai", "pune", "delhi",
]

# ═══════════════════════════════════════════════════════════
# VISA / EXPERIENCE BLOCKERS (checked in JD text)
# ═══════════════════════════════════════════════════════════

VISA_BLOCKERS = [
    "us citizen", "u.s. citizen", "united states citizen",
    "permanent resident only", "green card required",
    "security clearance required", "top secret",
    "ts/sci", "secret clearance", "dod clearance",
    "must be a citizen", "citizenship required",
    "no opt", "no visa sponsorship",
    "not eligible for visa", "cannot sponsor",
    "only us citizens", "us persons",
]

# These are OK — she qualifies for these
VISA_OK_SIGNALS = [
    "authorized to work", "work authorization",
    "legally authorized", "opt", "stem opt",
    "sponsorship not required",
    "must be authorized to work in the us",
]

EXPERIENCE_BLOCKERS = [
    "5+ years", "6+ years", "7+ years", "8+ years",
    "10+ years", "5-7 years", "5-10 years", "7-10 years",
    "8-10 years", "10-15 years", "5 years of experience",
    "6 years of experience", "7 years of experience",
    "8 years of experience", "10 years of experience",
    "minimum 5 years", "minimum 6 years", "at least 5 years",
    "at least 6 years",
]

# ═══════════════════════════════════════════════════════════
# 200+ COMPANIES BY ATS PLATFORM
# ═══════════════════════════════════════════════════════════

GREENHOUSE = [
    # Major tech
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
    # Additional major companies
    "asana", "atlassian", "box", "coda", "elastic",
    "fastly", "grammarly", "hashicorp", "loom",
    "mixpanel", "mongodb", "miro", "navan",
    "onepassword", "segment", "servicetitan",
    "squarespace", "taskrabbit", "thumbtack",
    "unity", "vimeo", "vonage", "yext",
    # YC companies on Greenhouse
    "gofundme", "gitlab", "flexport", "faire",
    "checkr", "lattice", "ironclad", "webflow",
    "whatnot", "razorpay", "meesho", "zepto",
    "groww", "cred-club",
    # Fintech / Finance
    "affirm", "marqeta", "mercury", "sofi",
    "upstart", "wealthsimple", "betterment",
    # Healthcare / Biotech
    "flatiron", "tempus", "veracyte", "color",
    # E-commerce / Consumer
    "etsy", "farfetch", "glossier", "allbirds",
    "warbyparker", "stitch-fix",
]

LEVER = [
    # Original
    "netflix", "dbtlabs", "fivetran", "prefect", "anduril",
    "samsara", "benchling", "faire", "lacework", "mux",
    "nerdwallet", "orca-security", "replit",
    "tempus", "truelayer", "vanta",
    # Additional
    "calm", "cockroach-labs", "cruise", "drata",
    "exafunction", "grafana", "hasura", "hex",
    "komodor", "launchdarkly", "lightstep",
    "meilisearch", "metabase", "modern-treasury",
    "neon-inc", "observe-ai", "optic",
    "readme", "redpanda-data", "split",
    "starburst", "teleport", "temporal",
    "tigera", "vercel", "voxel51",
    # YC companies on Lever
    "amplitude", "brex", "deel", "gusto",
    "loom", "messagebird", "monzo",
    "plaid", "segment", "sendbird", "weave",
]

ASHBY = [
    # Original
    "anthropic", "cursor", "perplexity", "pinecone", "posthog",
    "runway", "weights-and-biases", "linear", "beamery",
    "clay", "coreweave", "deepgram", "eleven-labs", "glean",
    "labelbox", "materialize", "modal", "motherduck", "neon",
    "qdrant", "resend", "stainless",
    "together-ai", "trigger-dev", "turso",
    "upstash", "val-town", "warp",
    # Additional AI / Data companies
    "arize-ai", "cohere", "dbt-labs", "determined-ai",
    "hex-technologies", "langchain", "lancedb",
    "marqo", "milvus", "nomic", "ollama",
    "qdrant", "replicate", "scale-ai",
    "snorkel-ai", "wandb", "zilliz",
    # YC companies on Ashby
    "airtable", "ashby", "baseten",
    "browserbase", "e2b", "helicone",
    "humanloop", "instructor-ai",
    "mem", "mintlify", "orb",
    "pieces-app", "polytomic", "prefect",
    "relevance-ai", "retool",
    "supabase", "tinybird", "windmill",
]

# SmartRecruiters — public unauthenticated Posting API
# Endpoint: GET https://api.smartrecruiters.com/v1/companies/{id}/postings
SMARTRECRUITERS = [
    "Visa", "KPMG", "Equinix", "Bosch", "McDonald's",
    "Skechers", "TomTom", "Delivery-Hero", "trivago",
    "SoundCloud", "HelloFresh", "N26", "Zalando",
    "TradeRepublic", "Personio1", "CelonisHR",
    "Adevinta", "ING", "ABInBev",
    # US-focused companies on SmartRecruiters
    "Visa1", "LinkedIn1", "T-Mobile",
    "CrowdStrike", "Palo-Alto-Networks",
]

# Workable — public widget API
# Endpoint: GET https://apply.workable.com/api/v1/widget/accounts/{subdomain}
WORKABLE = [
    "niantic", "taxjar", "pipe", "metaview",
    "sardine", "causal", "coefficient",
    "hightouch", "hyperscience", "incident-io",
    "jam-dev", "jellyfish", "launchnotes",
    "lightyear", "localstack", "neuralink",
    "orbit", "primer", "rainbow",
    "render", "sidekick", "skio",
    "swiftly", "whalesync", "woodruff-sawyer",
]

# ═══════════════════════════════════════════════════════════
# NIDHI'S PROFILE — For auto-drafting
# ═══════════════════════════════════════════════════════════

PROFILE = """Name: Nidhi Rajani
Target: Data Engineer / Data Analyst / Analytics DS (0-2 years exp)
Visa: F1 STEM OPT — 3-year work authorization starting June 2026.
      NO H-1B sponsorship needed. Authorized to work in US on Day 1.

EXPERIENCE:
Flipkart (Walmart subsidiary) | Data Engineer | Feb–Dec 2024
• $1.8M revenue impact — PAN-India SIM card delivery platform, Best Innovation Award
• 99.2% uptime across 10M+ daily transactions
• Power BI dashboards, Pareto analysis improving delivery rates 35%→68%
• API orchestration with Airtel KYC portal, open-box fraud prevention
• B2B logistics coordination for Paytm device collection

Teaching Assistant — Statistical Learning & Data Mining | University at Buffalo | Jan 2026–Present

EDUCATION: MS Data Science, University at Buffalo GPA 3.83 (June 2026) | BTech CS, NIT Bhopal

PROJECTS:
• Two-Tower Rec System (HR@10=0.7285, FAISS 29μs/query, 98K users)
• Global Food Platform (PostgreSQL, dbt, Airflow, Snowflake, Streamlit)
• CVE Lakehouse Pipeline (Spark, medallion architecture, 75M rows, 3.5x speedup)
• IoT Malware Detection (99.56% accuracy, GNN+GAN, 76K flows)

SKILLS: Python, SQL, PySpark, Airflow, dbt, PostgreSQL, Snowflake,
Docker, Git, Spark, Pandas, TensorFlow, PyTorch, Power BI, AWS (S3/Lambda/Glue),
Schema Design, Orchestration, Incremental Loads, CI/CD, Data Lineage

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
    visa_flag: str = ""
    exp_flag: str = ""

    @property
    def uid(self) -> str:
        return hashlib.md5(f"{self.company}:{self.title}:{self.url}".encode()).hexdigest()

    def matches(self) -> bool:
        t = f" {self.title.lower()} "  # pad for word boundary
        loc = self.location.lower()

        # Title must contain at least one include keyword
        title_ok = any(kw in t for kw in TITLE_INCLUDE)

        # Title must NOT contain any exclude keyword
        title_blocked = any(ex in t for ex in TITLE_EXCLUDE)

        # Location: reject if explicitly excluded country/region
        loc_blocked = any(ex in loc for ex in LOCATIONS_EXCLUDE)

        # Location: accept if matches US location OR location is empty
        loc_ok = (not self.location) or any(l in loc for l in LOCATIONS_INCLUDE)

        return title_ok and not title_blocked and loc_ok and not loc_blocked

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
        return True

    def save(self):
        SEEN_FILE.write_text(json.dumps({"seen": list(self.seen)}))

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


def fetch_smartrecruiters(slug: str) -> list:
    """SmartRecruiters public Posting API — unauthenticated"""
    try:
        url = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
        r = requests.get(url, params={"limit": 100}, timeout=10)
        if r.status_code != 200: return []
        jobs = []
        for j in r.json().get("content", []):
            loc_obj = j.get("location", {})
            loc_str = ", ".join(filter(None, [
                loc_obj.get("city", ""),
                loc_obj.get("region", ""),
                loc_obj.get("country", ""),
            ]))
            job = Job(
                title=j.get("name", ""),
                company=slug,
                location=loc_str,
                url=j.get("ref", j.get("applyUrl", "")),
                posted_at=j.get("releasedDate", ""),
                source="smartrecruiters",
                job_id=str(j.get("id", j.get("uuid", ""))),
            )
            if job.matches(): jobs.append(job)
        return jobs
    except: return []


def fetch_workable(slug: str) -> list:
    """Workable public widget API — unauthenticated"""
    try:
        url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return []
        jobs = []
        for j in r.json().get("jobs", []):
            job = Job(
                title=j.get("title", ""),
                company=slug,
                location=j.get("location", ""),
                url=f"https://apply.workable.com/{slug}/j/{j.get('shortcode', '')}/",
                posted_at=j.get("published_on", ""),
                source="workable",
                job_id=str(j.get("shortcode", "")),
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
                return re.sub(r'<[^>]+>', ' ', r.json().get("content", ""))[:4000]

        elif job.source == "lever" and job.job_id:
            r = requests.get(
                f"https://api.lever.co/v0/postings/{job.company}/{job.job_id}",
                timeout=10
            )
            if r.status_code == 200:
                parts = []
                desc = r.json().get("descriptionPlain", "")
                if desc: parts.append(desc)
                for lst in r.json().get("lists", []):
                    parts.append(lst.get("text", ""))
                    for item in lst.get("content", ""):
                        parts.append(f"  - {item}")
                return "\n".join(parts)[:4000]

        elif job.source == "ashby" and job.job_id:
            r = requests.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{job.company}",
                timeout=10
            )
            if r.status_code == 200:
                for j in r.json().get("jobs", []):
                    if str(j.get("id", "")) == job.job_id:
                        desc = j.get("descriptionHtml", j.get("descriptionPlain", ""))
                        return re.sub(r'<[^>]+>', ' ', desc)[:4000]

        elif job.source == "smartrecruiters" and job.job_id:
            r = requests.get(
                f"https://api.smartrecruiters.com/v1/companies/{job.company}/postings/{job.job_id}",
                timeout=10
            )
            if r.status_code == 200:
                sections = r.json().get("jobAd", {}).get("sections", {})
                parts = []
                for key in ["companyDescription", "jobDescription", "qualifications", "additionalInformation"]:
                    sec = sections.get(key, {})
                    if sec.get("text"):
                        parts.append(re.sub(r'<[^>]+>', ' ', sec["text"]))
                return "\n".join(parts)[:4000]

    except: pass
    return ""


# ═══════════════════════════════════════════════════════════
# VISA + EXPERIENCE CHECKER (runs on JD text)
# ═══════════════════════════════════════════════════════════

def check_visa_and_experience(job: Job, desc: str) -> tuple:
    """Returns (visa_flag, exp_flag) — empty string means OK"""
    desc_lower = desc.lower()

    # Check visa blockers
    visa_flag = ""
    for blocker in VISA_BLOCKERS:
        if blocker in desc_lower:
            # Check if it's actually saying "sponsorship not required" (which is OK for her)
            context_ok = any(ok in desc_lower for ok in VISA_OK_SIGNALS)
            if not context_ok:
                visa_flag = f"⚠️ VISA BLOCKER: '{blocker}' found in JD"
                break

    # Check experience requirements
    exp_flag = ""
    for blocker in EXPERIENCE_BLOCKERS:
        if blocker in desc_lower:
            exp_flag = f"⚠️ OVERQUALIFIED: '{blocker}' found — may be too senior"
            break

    return visa_flag, exp_flag


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
14. **RED FLAGS**: Visa issues, experience mismatch, stack gaps?

IMPORTANT VISA CONTEXT:
Nidhi has STEM OPT = 3-year work authorization. She does NOT need H-1B sponsorship
to start working. If the JD says "must be authorized to work in US" that's FINE —
she IS authorized. Only flag if JD says "US citizen only" or "security clearance required".
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

    company_clean = job.company.replace("-", " ").title()
    linkedin_searches = (
        f'1) "{company_clean}" "data engineer" site:linkedin.com/in\n'
        f'2) "{company_clean}" "recruiter" OR "talent" site:linkedin.com/in\n'
        f'3) "{company_clean}" "hiring manager" "data" site:linkedin.com/in'
    )

    # Build flags string
    flags = ""
    if job.visa_flag: flags += f"\n{job.visa_flag}"
    if job.exp_flag: flags += f"\n{job.exp_flag}"
    if not flags: flags = "\n✅ No visa/experience blockers detected"

    claude_prompt = (
        f"I found a new job posting. Help me apply.\n\n"
        f"Company: {company_clean}\n"
        f"Role: {job.title}\n"
        f"Location: {job.location}\n"
        f"URL: {job.url}\n\n"
        f"IMPORTANT: I have STEM OPT (3-year US work authorization). "
        f"I do NOT need H-1B sponsorship. If JD says 'authorized to work in US' "
        f"that's fine — I qualify. Only flag 'US citizen only' or 'security clearance'.\n\n"
        f"Do ALL of these:\n"
        f"1. Tell me: DE or DA resume lane?\n"
        f"2. Rewrite my Flipkart title for this JD\n"
        f"3. Write 4 tailored resume bullets (metrics first 8 words)\n"
        f"4. Reorder my skills to match JD\n"
        f"5. Pick top 3 projects by relevance\n"
        f"6. ATS score /100\n"
        f"7. 6-second recruiter scan verdict\n"
        f"8. Cover letter (200 words, hook opening, mention company)\n"
        f"9. LinkedIn message to an engineer (80 words, genuine interest, "
        f"DON'T ask for referral)\n"
        f"10. LinkedIn message to recruiter (60 words)\n"
        f"11. Follow-up message for day 5\n"
        f"12. Hiring manager cold email (subject + 150 words)\n"
        f"13. Red flags / visa / experience mismatch?"
    )

    try:
        # Determine color: green = clean, yellow = warning, red = blocker
        color = 0x00FF00  # green
        if job.exp_flag: color = 0xFFAA00  # yellow
        if job.visa_flag: color = 0xFF0000  # red

        # Message 1: Alert embed
        requests.post(DISCORD_WEBHOOK_URL, json={
            "embeds": [{
                "title": f"🎯 NEW: {job.title} @ {company_clean}",
                "url": job.url,
                "color": color,
                "fields": [
                    {"name": "📍 Location", "value": job.location or "N/A", "inline": True},
                    {"name": "🏗️ ATS", "value": job.source.upper(), "inline": True},
                    {"name": "⏰ Found", "value": datetime.now().strftime("%I:%M %p"), "inline": True},
                    {"name": "🛂 Visa/Exp Check", "value": flags.strip(), "inline": False},
                    {"name": "🔍 LinkedIn searches", "value": linkedin_searches, "inline": False},
                ],
                "footer": {"text": "⚡ Apply within 1 hour!"},
            }]
        }, timeout=10)

        # Message 2: Ready-to-paste Claude.ai prompt
        requests.post(DISCORD_WEBHOOK_URL, json={
            "content": f"📋 **Paste this into Claude.ai:**\n```\n{claude_prompt}\n```"
        }, timeout=10)

    except: pass

# ═══════════════════════════════════════════════════════════
# CONCURRENT SCANNER
# ═══════════════════════════════════════════════════════════

def _fetch_wrapper(fetcher, slug):
    """Wrapper for thread pool execution"""
    return fetcher(slug)

def scan_all():
    tracker = SeenTracker()
    new_jobs = []

    all_tasks = []
    all_tasks += [(fetch_greenhouse, s) for s in GREENHOUSE]
    all_tasks += [(fetch_lever, s) for s in LEVER]
    all_tasks += [(fetch_ashby, s) for s in ASHBY]
    all_tasks += [(fetch_smartrecruiters, s) for s in SMARTRECRUITERS]
    all_tasks += [(fetch_workable, s) for s in WORKABLE]

    log.info(f"Scanning {len(all_tasks)} companies across 5 ATS platforms...")

    # Use thread pool for 5x faster scanning
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(_fetch_wrapper, fetcher, slug): slug
            for fetcher, slug in all_tasks
        }
        for future in as_completed(futures):
            try:
                jobs = future.result()
                for job in jobs:
                    if tracker.is_new(job):
                        new_jobs.append(job)
            except Exception as e:
                pass  # Individual company failures don't crash the scan

    tracker.save()
    return new_jobs


def process_job(job: Job):
    log.info(f"🎯 NEW: {job.title} @ {job.company} ({job.location})")
    log.info(f"   🔗 {job.url}")

    # Fetch JD and check visa/experience
    desc = fetch_description(job)
    if desc:
        job.visa_flag, job.exp_flag = check_visa_and_experience(job, desc)
        if job.visa_flag:
            log.info(f"   🛂 {job.visa_flag}")
        if job.exp_flag:
            log.info(f"   📊 {job.exp_flag}")

    # Skip auto-drafting for visa-blocked jobs (still alert on Discord)
    draft = ""
    if not job.visa_flag:
        draft = draft_materials(job)
    else:
        draft = f"⚠️ VISA BLOCKER DETECTED — Review JD manually before applying.\n{job.visa_flag}"

    safe = f"{job.company}_{job.title}".replace(" ", "_").replace("/", "-")[:60]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    path = DRAFTS_DIR / f"{ts}_{safe}.md"
    path.write_text(
        f"# {job.title} @ {job.company}\n"
        f"**URL:** {job.url}\n"
        f"**Location:** {job.location}\n"
        f"**Found:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}\n"
        f"**Source:** {job.source}\n"
        f"**Visa:** {job.visa_flag or '✅ OK'}\n"
        f"**Experience:** {job.exp_flag or '✅ OK'}\n"
        f"\n---\n\n{draft}\n"
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
    total = len(GREENHOUSE) + len(LEVER) + len(ASHBY) + len(SMARTRECRUITERS) + len(WORKABLE)
    log.info("🛰️  JOB SNIPER v2 ACTIVATED")
    log.info(f"📡 Monitoring {total} companies across 5 ATS platforms")
    log.info(f"   Greenhouse: {len(GREENHOUSE)} | Lever: {len(LEVER)} | Ashby: {len(ASHBY)}")
    log.info(f"   SmartRecruiters: {len(SMARTRECRUITERS)} | Workable: {len(WORKABLE)}")
    log.info(f"📁 Drafts → {DRAFTS_DIR.absolute()}")
    log.info(f"🔔 Discord: {'✅' if DISCORD_WEBHOOK_URL else '❌ Set DISCORD_WEBHOOK_URL'}")
    log.info(f"🤖 Auto-draft: {'✅' if ANTHROPIC_API_KEY else '❌ Set ANTHROPIC_API_KEY (optional)'}")
    log.info(f"🛂 Visa filter: ✅ (STEM OPT — blocks US-citizen-only roles)")
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
