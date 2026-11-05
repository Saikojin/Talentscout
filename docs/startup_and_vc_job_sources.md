# Startup & VC Job Sources Directory

Extracted and resolved from Jordan Mazer's (Partner @ a16z) curated directory: *"Most startup jobs are not posted on LinkedIn — Resources / Job Boards / Aggregators / Newsletters for finding amazing unposted jobs."*

Integrated into **TalentScout** for automated multi-site scraping (`scripts/auto_scour.py`), SQLite deduplication (`job_tracker.db`), and ATS direct ingestion.

---

## 1. VC Firm Job Boards (Getro, Ashby, & Custom Engines)

Configured in `site_selectors.json`, `job_search_sites.json`, and the SQLite `sites` and `search_configs` tables.

| Firm / Resource | Platform | Scour URL | Status |
|---|---|---|---|
| **Andreessen Horowitz (a16z)** | Getro | `https://portfoliojobs.a16z.com/jobs?q={search_term}&locations={location}` | Active |
| **Sequoia Capital** | Getro | `https://jobs.sequoiacap.com/jobs?q={search_term}&locations={location}` | Active |
| **General Catalyst** | Getro | `https://jobs.generalcatalyst.com/jobs?q={search_term}&locations={location}` | Active |
| **Khosla Ventures** | Getro | `https://jobs.khoslaventures.com/jobs?q={search_term}&locations={location}` | Active |
| **Kleiner Perkins** | Getro | `https://jobs.kleinerperkins.com/jobs?q={search_term}&locations={location}` | Active |
| **Accel** | Getro | `https://jobs.accel.com/jobs?q={search_term}&locations={location}` | Active |
| **Lightspeed (LSVP)** | Getro | `https://jobs.lsvp.com/jobs?q={search_term}&locations={location}` | Active |
| **Thrive Capital** | Getro | `https://jobs.thrivecap.com/jobs?q={search_term}&locations={location}` | Active |
| **Bessemer Venture Partners** | Getro | `https://jobs.bvp.com/jobs?q={search_term}&locations={location}` | Active |
| **Felicis Ventures** | Getro | `https://jobs.felicis.com/jobs?q={search_term}&locations={location}` | Active |
| **Lux Capital** | Getro | `https://jobs.luxcapital.com/jobs?q={search_term}&locations={location}` | Active |
| **Contrary Capital** | Getro | `https://jobs.contrary.com/jobs?q={search_term}&locations={location}` | Active |
| **Battery Ventures** | Getro | `https://jobs.battery.com/jobs?q={search_term}&locations={location}` | Active |
| **NEA (New Enterprise Associates)** | Getro | `https://careers.nea.com/jobs?q={search_term}&locations={location}` | Active |
| **Insight Partners** | Getro | `https://jobs.insightpartners.com/jobs?q={search_term}&locations={location}` | Active |
| **Menlo Ventures** | Getro | `https://jobs.menlovc.com/jobs?q={search_term}&locations={location}` | Active |
| **Bain Capital Ventures** | Getro | `https://jobs.baincapitalventures.com/jobs?q={search_term}&locations={location}` | Active |
| **Notable Capital (fka GGV)** | Getro | `https://jobs.ggvc.com/jobs?q={search_term}&locations={location}` | Active |
| **Antler** | Getro | `https://careers.antler.co/jobs?q={search_term}&locations={location}` | Active |
| **BITKRAFT Ventures** | Getro | `https://careers.bitkraft.vc/jobs?q={search_term}&locations={location}` | Active |
| **8VC** | Getro | `https://jobs.8vc.com/jobs?q={search_term}&locations={location}` | Active |
| **CRV** | Consider | `https://consider.com/boards/crv?q={search_term}` | Active |
| **Greylock Partners** | Custom | `https://greylock.com/jobs/portfolio-jobs/?query={search_term}` | Active |
| **Index Ventures** | Custom | `https://www.indexventures.com/startup-jobs?search={search_term}` | Active |
| **Pear VC** | Ashby | `https://jobs.ashbyhq.com/Pear-VC` | Active |

---

## 2. Startup Job Aggregators

| Platform | Type | Scour URL | Status |
|---|---|---|---|
| **Speedrun Talent Network** | Specialized Portal | `https://speedrun-talent-network.com/jobs?remote=1&scope=everywhere&search={search_term}` | Active |
| **YC Work at a Startup** | Y Combinator Aggregator | `https://www.workatastartup.com/jobs/v2?query={search_term}` | Active |
| **Top Startups** | Funded Startup Aggregator | `https://topstartups.io/jobs/?q={search_term}` | Active |
| **Wellfound (fka AngelList)** | Startup Portal | `https://wellfound.com/jobs?q={search_term}` | Active |
| **Startups Gallery** | Curated Startup List | `https://startups.gallery` | Active |
| **OutGeek: Women in Tech** | Curated Tech Aggregator | `https://outgeek.org` | Active |

---

## 3. Fellowships, Direct Opportunities & Talent Networks

Configured in `base_companies.json` and the SQLite `companies` table for direct career/ATS harvesting:

- **Speedrun Product Engineer (Jordan Mazer's Team)**: `https://speedrun-talent-network.com/product-engineer/`
- **Neo Scholars**: `https://neo.com/scholars`
- **Z Fellows**: `https://www.zfellows.com/`
- **Kleiner Perkins Fellows**: `https://www.kleinerperkins.com/fellows/`
- **Pear Fellows**: `https://pear.vc/fellows/`
- **a16z College Talent**: `https://a16z.com/college-talent/`
- **Underdog.io**: `https://underdog.io/`
- **Cosign**: `https://cosign.co/`
- **Jobbie**: `https://jobbie.bot/`

---

## 4. Curated Newsletters & Substack Feeds

Stored in `newsletters_to_scour.json`:

- **job hunting sux** (Jordan Mazer): `https://www.jobhuntingsux.com/`
- **a16z Jobs**: `https://a16zjobs.substack.com/` (`/feed` available)
- **Ali Rohde Jobs**: `https://alirohdejobs.substack.com/` (`/feed` available)
- **next play**: `https://nextplayso.substack.com/` (`/feed` available)
- **Nonlinear News**: `https://nonlinearnews.com/`
- **Beyond Bay St.**: `https://beyondbayst.substack.com/` (`/feed` available)
- **Why You Should Join**: `https://whyyoushouldjoin.substack.com/` (`/feed` available)
- **Web of Jobs**: `https://webofjobs.substack.com/` (`/feed` available)
