# Video Game Industry Job Sources Directory

Curated game development job boards, studio directories, and interactive maps integrated into **TalentScout** for automated scouring (`scripts/auto_scour.py`), ATS harvesting, and deduplication (`job_tracker.db`).

---

## 1. Game Development Job Boards & Aggregators

Configured in `site_selectors.json`, `job_search_sites.json`, and the SQLite `sites` and `search_configs` tables:

| Source | Description | Scour URL | Status |
|---|---|---|---|
| **ASGC (All Star Games Careers)** | Amir Satvat's global consolidated games career table linking directly to studio ATS postings. | `https://jobs.asgc.gg/` | Active |
| **Games Jobs Index** | 10,000+ live roles across the games industry with Workday/Greenhouse/Lever tracking. | `https://gamesjobsindex.com/?q={search_term}` | Active |
| **Hitmarker** | Premier video game, esports, and gaming content job platform. | `https://hitmarker.net/jobs?keyword={search_term}` | Active |
| **DevQuest** | Filtered game dev feed linking directly to studio ATS systems. | `https://devquest.gg/?q={search_term}` | Active |
| **Games Jobs Direct** | UK, USA, Europe & international game industry vacancy network. | `https://www.gamesjobsdirect.com/` | Active |
| **Remote Game Jobs** | Dedicated remote games work across programming, art, design, and QA. | `https://remotegamejobs.com/search?q={search_term}` | Active |
| **Work With Indies** | Indie game studios, co-dev teams, and remote indie opportunities. | `https://www.workwithindies.com/search?query={search_term}` | Active |

---

## 2. Interactive Maps & Studio Directories

- **Hitmarker World Map**: `https://hitmarker.net/world-map` (Interactive global map of gaming, esports, and tech studios).
- **Hitmarker Companies Directory**: `https://hitmarker.net/companies` (Directory of 48+ major game companies including NVIDIA, AMD, Gameloft, Unity, EA, Xsolla).
- **DevQuest Studio Directory**: `https://devquest.gg/` (91 curated studio career sites).

---

## 3. Curated Direct Game Studios in `base_companies.json`

Seeded into the SQLite `companies` table for automated direct ATS/careers harvesting in Phase 1b:

- **4A Games**: `https://www.4a-games.com.mt/careers` (Metro series)
- **4J Studios**: `https://4jstudios.com/careers/` (Minecraft console editions)
- **Arcanaut Studios**: `https://www.arcanautstudios.com/careers`
- **Archetype Entertainment**: `https://www.archetype-entertainment.com/en-US` (Exodus)
- **Awaceb**: `https://www.awaceb.com/` (Tchia)
- **BKOM Studios**: `https://jobs.bkom.com/`
- **Blowfish Studios**: `https://www.blowfishstudios.com/careers`
- **Bossa Studios**: `https://www.bossagames.com/jobs` (Surgeon Simulator, I am Bread)
- **Cyanide Studios**: `https://cyanide-studio.com/en/join-us/`
- **Deck Nine Games**: `https://www.deckninegames.com/careers` (Life is Strange)
- **Enduring Games**: `https://enduring.games/jobs/`
- **Crytek**: `https://www.crytek.com/career` (Hunt: Showdown, CryEngine)
- **Virtuos**: `https://www.virtuosgames.com/careers/`
- **Keywords Studios**: `https://www.keywordsstudios.com/careers/` (QA, Co-dev, Localization)
- **Scopely**: `https://scopely.com/join-us/`
- **Riot Games**: `https://www.riotgames.com/en/work-with-us` (League of Legends, VALORANT)
- **Light & Wonder**: `https://www.lnw.com/careers/`
- **Sony PlayStation Studios**: `https://www.playstation.com/en-us/corporate/playstation-jobs/`
- **Super Spline Studios**: `https://supersplinestudios.com/careers/`
- **Roboto Games**: `https://robotogames.com/careers`
- **iam8bit**: `https://www.iam8bit.com/pages/careers`
