# Garmini (gar-mini) 🏃‍♂️💨

> Personal Garmin API Marathon Training Command Center & PWA Dashboard.
> Designed for Sub-3:28 marathon prep, training load monitoring, polarized 80/20 intensity breakdown, and recovery biomarkers.

**Live Deployment:** [https://garmini.nmanjuonline.workers.dev](https://garmini.nmanjuonline.workers.dev)

---

## ✨ Features

- **Dual Marathon Countdown & Goal Pacing:**
  - **Target A:** Tata Mumbai Marathon (Jan 17, 2027) — Target 3:28:00 (4:56/km)
  - **Target B:** New Delhi Marathon (Feb 28, 2027) — Target 3:28:00 (4:56/km)
- **Compact Athletic Vital Metrics (70% Height Optimized for Mobile):**
  - Weekly Volume & 4-Week Rolling Average
  - Acute:Chronic Workload Ratio (ACWR) injury risk tracking
  - Resting Heart Rate (RHR) & 7-Day Rolling Baseline
  - Nightly Heart Rate Variability (HRV) Status
  - Sleep Recovery Score & Total Hours
- **Sub-3:28 Interactive Pacing Matrix:**
  - Negative Split Strategy (Conservative start, aerobic cruise, strong second-half kick)
  - Even Split Strategy (Flat 4:56/km baseline)
- **80/20 Polarized Training Distribution:**
  - Garmin Heart Rate zone calculation (~80% Zone 1–2 aerobic base vs. ~20% Zone 3–5 tempo/threshold)
- **Recovery Trends & Dynamics (90 Days):**
  - Interactive dual-axis Chart.js visualizations for RHR vs. HRV and Sleep Score vs. Hours
  - 26-Week mileage progression with longest run overlays
- **Running Session Log with Live Filtering:**
  - Interactive category filters (*All Runs*, *Long Runs 15k+*, *Target Pace ≤ 4:56*, *Aerobic Base*)
  - Real-time client-side search by session title or date
- **PWA & Offline Capability:**
  - Full Progressive Web App support with service worker caching (`sw.js`)
  - Custom maskable app icons and standalone display mode
- **Accessible & Adaptive Design:**
  - **Midnight Athletic Dark Theme** & **Athletic Daylight Light Theme** with live toggle
  - Tabular numerals (`tabular-nums`) for numeric data alignment
  - WCAG 2.1 AA/AAA contrast ratios and keyboard `:focus-visible` outlines

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ (for deployment via Wrangler)

### 2. Configuration
Create `.env.local` with your Garmin Personal API token:
```bash
GARMIN_PERSONAL_API_KEY="your-garmin-personal-api-token"
```

### 3. Sync & Build
```bash
# Pull latest activities from Garmin Connect API
python pull.py

# Build standalone HTML dashboard and PWA site
npm run build

# Start local preview server
npm run dev
# Opens at http://localhost:3000
```

### 4. Deploy to Cloudflare Workers
```bash
npm run deploy
```

---

## 🛠️ Automated CI/CD
This repository includes a scheduled GitHub Actions workflow in `.github/workflows/scheduled-refresh.yml` that runs daily at 00:30 UTC to automatically pull the latest Garmin health metrics, rebuild the site, and deploy to Cloudflare Workers.

---

## 📄 License
MIT © Manju Narasimha
