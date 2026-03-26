# 🎯 PROMPT PLAYBOOK — Free Tier Workflow
## Paste these into Claude.ai when your phone buzzes

---

## ⚡ STEP 1: THE MAIN PROMPT (paste from Discord alert)

When your Discord pings with a new job, it now includes a **ready-to-paste prompt**.
Just copy it from Discord → paste into Claude.ai → get everything back.

If you want to paste the job description manually instead:

```
I found this job posting. Help me apply.

Company: [COMPANY]
Role: [TITLE]
URL: [URL]
Job Description: [PASTE JD HERE]

Do ALL of these:
1. Tell me: DE or DA resume lane?
2. Rewrite my Flipkart title for this JD
3. Write 4 tailored resume bullets (metrics first 8 words, 15-25 words, result-first XYZ)
4. Reorder my skills to match JD priority
5. Pick my top 3 projects ranked by relevance to this role
6. Give me an ATS score /100 with reasoning
7. 6-second recruiter scan verdict — would you keep or reject?
8. Cover letter (200 words, hook opening NOT "I am applying for", mention company specifically)
9. LinkedIn message to an engineer on their DE team (80 words — see networking rules below)
10. LinkedIn message to their recruiter (60 words)
11. Follow-up message for day 5 if no response
12. Cold email to hiring manager (subject line + 150 words)
13. Red flags — any visa issues, overqualification, stack mismatches?
```

---

## 🤝 STEP 2: LINKEDIN NETWORKING (the warm approach)

### Finding the right people

Your Discord alert now includes 3 LinkedIn search queries. Use them on Google:
```
"[Company]" "data engineer" site:linkedin.com/in
"[Company]" "recruiter" OR "talent acquisition" site:linkedin.com/in
"[Company]" "hiring manager" "data" site:linkedin.com/in
```

### Who to connect with (priority order):
1. **A data engineer on the team** — peer-level, most likely to respond
2. **The hiring manager** — usually "Engineering Manager, Data" or "Director, Data Engineering"
3. **The recruiter** — usually has "Technical Recruiter" or "Talent Acquisition" in title

### The networking philosophy: DON'T ask for referrals directly

The connection request message should:
- ✅ Show you've researched what THEY specifically work on
- ✅ Mention what excites you about their team's technical stack
- ✅ Briefly state what you bring to the table (1 sentence)
- ✅ End with a low-friction ask (coffee chat, not referral)
- ❌ Never say "Can you refer me?"
- ❌ Never lead with "I'm looking for a job"
- ❌ Never send a generic template that could go to anyone

### Prompt for generating networking messages:

```
I want to connect with [PERSON'S NAME], who is a [THEIR TITLE] at [COMPANY].
Their LinkedIn shows they work on [WHAT YOU CAN SEE FROM THEIR PROFILE].
The company is hiring for [ROLE] which uses [TECH STACK FROM JD].

Write me a LinkedIn connection request note (300 char limit) that:
- Opens with genuine curiosity about something specific they work on
- Shows I understand their tech stack (mention 1-2 specific tools)
- Briefly mentions I'm a MS Data Science student at UB graduating June 2026
  with production experience from Flipkart (Walmart subsidiary)
- Ends with a soft ask: "Would love to hear about your experience" NOT "Can you refer me"
- Feels like a real person wrote it, not a template
```

### Prompt for the follow-up message (after they accept):

```
[PERSON'S NAME] at [COMPANY] accepted my LinkedIn connection. They're a [TITLE].
The company is hiring for [ROLE].

Write a follow-up DM that:
- Thanks them for connecting (1 sentence, not gushy)
- Asks ONE specific technical question about their team's work
  (e.g., "I noticed your team uses dbt + Snowflake — curious how you handle
  incremental models at scale?" or "I saw the team works on real-time pipelines —
  are you using Kafka or something else for streaming?")
- Briefly mentions what I could bring: $1.8M revenue impact at Flipkart,
  10M+ daily transactions, production data pipeline experience
- Naturally mentions I'd love to explore opportunities on their team
- Keep it under 150 words
- The referral should come NATURALLY from them after seeing my value — don't ask for it
```

### Prompt for when they respond positively:

```
[PERSON] at [COMPANY] responded positively to my LinkedIn message and seems open
to chatting. They said: "[THEIR RESPONSE]"

Write my reply that:
- Matches their energy/tone
- Proposes a specific 15-min virtual coffee this week
- Mentions I have my resume ready if they'd like to see it
- Still doesn't directly ask for referral — let them offer
- Under 100 words
```

---

## 📧 STEP 3: RECRUITER EMAIL PROSPECTING

### How to find recruiter emails (free tools):

| Tool | Free Tier | How to Use |
|---|---|---|
| **Hunter.io** | 25 searches/mo | Search "[company].com" → find email pattern |
| **Apollo.io** | 50 credits/mo | Filter by company + "recruiter" title |
| **Lusha** | 5 credits/mo | Chrome extension, shows emails on LinkedIn profiles |
| **RocketReach** | 5 lookups/mo | Search by name + company |
| **Clearbit Connect** | 100/mo | Gmail extension, finds emails while composing |
| **Snov.io** | 50 credits/mo | Email finder + verifier |
| **SignalHire** | 5 credits/mo | Chrome extension on LinkedIn |

### The email pattern hack (no tools needed):
Most companies use predictable email formats:
- `firstname@company.com` (most startups)
- `firstname.lastname@company.com` (most enterprises)
- `flastname@company.com`

Find the pattern: Search `"@company.com" site:linkedin.com` or check Hunter.io's free domain search.
Then verify with `mail.google.com` — compose an email, type the address, if Google shows a profile pic it's valid.

### Prompt for cold recruiter/HM emails:

```
I want to email [RECRUITER/HM NAME] at [COMPANY] about the [ROLE] position.
Their email is [EMAIL]. The JD mentions [KEY REQUIREMENTS FROM JD].

Write a cold email that:
- Subject line: specific, not generic (not "Application for..." or "Interested in...")
- Opens with a hook about the company — a recent product launch, blog post,
  funding round, or technical decision that excites me as a DE
- Connects my Flipkart experience (Walmart subsidiary, $1.8M impact, 10M+
  daily transactions) directly to what they need
- Mentions I'm graduating from UB's MS Data Science program in June 2026
- States I'm on STEM OPT (3-year work authorization, no sponsorship needed initially)
- Ends with a clear, specific ask: "I'd love 15 minutes to discuss how my
  pipeline experience could contribute to [specific team/project]"
- Under 200 words total
- Attach resume? Yes, mention "I've attached my resume for context"
```

### Batch prospecting prompt (10 recruiters at once):

```
I'm targeting these 10 companies for DE/DA roles: [LIST COMPANIES]

For each company:
1. Give me the likely recruiter title to search for on LinkedIn
   (e.g., "Technical Recruiter" vs "University Recruiter" vs "Talent Partner")
2. Give me the likely email format (firstname@, firstname.lastname@, etc.)
3. Write a 1-sentence personalized hook specific to that company
   (reference their product, tech stack, or recent news)
4. Rate the likelihood they sponsor OPT/H1B (High/Medium/Low) based on company size and history

Format as a table I can work through one by one.
```

---

## 📄 STEP 4: RESUME TRANSFORMATION ENGINE

### After getting the tailored bullets from Step 1, use this for a full rewrite:

```
Act as a hiring manager who screens 200 resumes daily for [ROLE] at [COMPANY TYPE].

Here's the job description: [PASTE JD]

Rewrite my resume following these STRICT rules:
- Front-load metrics in the FIRST 8 words of every bullet
- Keep every bullet 15-25 words max
- Format: [Metric/Result] — [How] — [Scale/Context]
- Convert ALL responsibilities into measurable achievements
- Remove any weak wording: "assisted", "helped", "participated", "responsible for"
- Reorder Flipkart bullets to match JD keyword priority
- Reorder skills section to match JD order
- Reorder projects by relevance to this specific role
- For DE roles: Flipkart title = "Data Engineer — Operations & Platform Engineering"
- For DA roles: Flipkart title = "Data Analyst — Operations Analytics & Program Management"

Also:
- ATS keyword match score /100
- Highlight any missing keywords I should add
- 6-second recruiter scan: would you keep or reject? Why?

My current resume bullets:

FLIPKART (Walmart subsidiary) | Feb–Dec 2024
• $1.8M revenue impact — PAN-India SIM card delivery platform, Best Innovation Award
• 99.2% uptime across 10M+ daily transactions
• Power BI dashboards, Pareto analysis improving delivery rates 35%→68%
• API orchestration with Airtel KYC portal, open-box fraud prevention
• B2B logistics coordination for Paytm device collection

TA | University at Buffalo | Jan 2026–Present
• Statistical Learning & Data Mining under Prof. Khinkis and Prof. Chandola

Projects: Two-Tower RecSys (HR@10=0.7285, FAISS 29μs/query), Global Food Platform
(PostgreSQL, dbt, Airflow), IoT Malware Detection (99.56% accuracy, GNN+GAN)

Skills: Python, SQL, PySpark, Airflow, dbt, PostgreSQL, Snowflake, Docker, Git,
Spark, Pandas, TensorFlow, PyTorch, Power BI, AWS (S3/Lambda/Glue)
```

---

## 💼 STEP 5: LINKEDIN PROFILE OPTIMIZATION

```
Rewrite my LinkedIn profile so recruiters searching for "Data Engineer" and
"Data Analyst" find me immediately.

Current headline: [YOUR CURRENT HEADLINE]
Target roles: Data Engineer, Analytics Engineer, Data Analyst

Rewrite these sections:
1. HEADLINE (220 char max) — keyword-rich, not cute
   Must include: Data Engineer | Flipkart/Walmart | specific tech stack
2. ABOUT SECTION (2600 char max) — not a resume summary, a narrative that:
   - Opens with my strongest metric ($1.8M revenue impact at Flipkart)
   - Tells the Flipkart → UB → DE career arc in 3 sentences
   - Lists my tech stack naturally (not a bullet dump)
   - Mentions STEM OPT (3-year US work auth) without making it the focus
   - Ends with what I'm looking for: "Open to DE/DA roles starting June 2026"
3. EXPERIENCE — top 3 entries rewritten with achievement-first bullets
4. SKILLS ORDER — which 50 skills to list and in what order for DE search ranking

Make every word earn its place. Recruiters scan in 6 seconds.
```

---

## 🎤 STEP 6: INTERVIEW PREP

### Before any interview:

```
I have an interview for [ROLE] at [COMPANY] in [X] days.

Based on the JD: [PASTE JD]

Give me:
1. The 8 most likely technical questions they'll ask
   (SQL, pipeline design, data modeling, specific tools from JD)
2. The 5 most likely behavioral questions
3. For each question: a STAR-format answer framework using my Flipkart experience
4. 3 smart questions I should ask that signal I've done my homework
   (reference something specific about their engineering blog, tech stack choice, or recent product)
5. A 2-minute "tell me about yourself" script that:
   - Opens with Flipkart impact (not "I'm a student at UB")
   - Connects to why this specific role
   - Ends with what I bring on day 1

Also flag any gaps between my experience and their requirements that
I should proactively address.
```

### Mock interview prompt:

```
Act as the hiring manager for [ROLE] at [COMPANY]. Conduct a realistic
30-minute mock interview. Ask me one question at a time.

After each of my answers, score me 1-10 and give specific feedback on:
- Clarity: Did I answer the actual question?
- Structure: Did I use STAR format properly?
- Confidence: Did I sound like I've done this before?
- Specifics: Did I use numbers and concrete examples?

Start with "Tell me about yourself."
```

---

## 📊 STEP 7: JOB DESCRIPTION MATCHING

### Use this to analyze any JD before applying:

```
Analyze this job description and tell me:

JD: [PASTE]

1. EXACT SKILLS REQUIRED — list every technology, tool, and framework mentioned
2. IMPLICIT SKILLS — what they expect but didn't list (infer from context)
3. CULTURE SIGNALS — what kind of person are they looking for?
4. MY MATCH SCORE — /100, which of my skills map directly vs which are gaps
5. KEYWORD MAP — table with columns: JD Keyword | My Matching Experience | Where on Resume
6. DANGER ZONES — any requirements I clearly don't meet
7. VISA RISK — does the JD say anything about sponsorship/authorization?
8. SALARY ESTIMATE — based on title, location, company stage
9. RECOMMENDED STRATEGY — should I apply? If yes, which resume lane (DE/DA)?
   How to position Flipkart experience for this specific role?
```

---

## 🔄 DAILY WORKFLOW (Free Tier, ~25 min per job)

```
📱 Phone buzzes — Discord: "🎯 NEW: Data Engineer @ Snowflake"
│
├── Discord message 1: Job link + LinkedIn search queries
├── Discord message 2: Ready-to-paste Claude.ai prompt
│
▼ (Open Claude.ai on laptop)
│
├── [0:00]  Paste the prompt from Discord
├── [0:02]  Claude generates: bullets, cover letter, LinkedIn msgs, emails
├── [0:05]  Copy tailored bullets → paste into LaTeX resume
├── [0:10]  Submit application on Snowflake careers
├── [0:12]  Google the LinkedIn search queries from Discord
├── [0:15]  Find 2-3 people: 1 engineer, 1 recruiter, 1 HM
├── [0:18]  Send connection requests with the generated note
├── [0:20]  If you have recruiter email: send cold email + resume
├── [0:25]  Done. You're applicant #5. Move to next job.
│
▼ (Repeat for next Discord alert)
```

---

## 💡 PRO TIPS

### 1. Batch your networking
Don't send 1 message per job. Batch: apply to 5 jobs, THEN send 15 LinkedIn messages (3 per company). Networking is less urgent than the application itself.

### 2. The "I noticed your team" trick
Before messaging an engineer, check if they've:
- Written a blog post on the company engineering blog
- Given a conference talk (search YouTube)
- Contributed to an open-source project

Reference it: "I read your post on migrating to dbt from Airflow — the incremental strategy you described is exactly what I implemented at Flipkart for our delivery analytics pipeline."

This one line does more than any referral ask ever will.

### 3. Track everything
In your Job Command Center, log:
- Company | Role | Date Applied | People Contacted | Status
- Follow up on Day 5 if no response from networking
- Follow up on Day 10 if no response from application

### 4. The Walmart backdoor
For any Walmart Group company (Walmart, Sam's Club, Flipkart US teams, Walmart Global Tech):
- You have an INSIDER story. You literally worked there.
- Lead EVERY message with: "Former Flipkart team member"
- This gets you past the "who is this person" filter instantly

### 5. Weekly LinkedIn content
Post once a week (takes 10 min with Claude):
```
Write me a LinkedIn post about [TOPIC] that:
- Opens with a contrarian take or surprising number
- Shares a real lesson from my Flipkart experience
- Tags relevant people/companies
- Ends with a question to drive engagement
- Under 200 words
- Doesn't sound like AI wrote it

Topics to rotate:
Week 1: "Just earned my dbt certification — here's what surprised me"
Week 2: "From 35% to 68% delivery rate — a Pareto analysis story"
Week 3: "Why I chose Data Engineering over ML after working at Flipkart"
Week 4: "The SQL pattern that saved us hours at 10M daily transactions"
```
