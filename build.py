"""
Garmini - Advanced Runner Dashboard Builder
Generates a standalone, PWA-enabled marathon command center
Includes 3 Live Dark Themes (Carbon, Midnight, Arctic),
ACWR Training Load, 80/20 Polarized Distribution, Running Dynamics,
and Sub-3:28 Marathon Pacing Matrix.
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_HTML = BASE_DIR / "dashboard.html"
INDEX_HTML = BASE_DIR / "index.html"
SITE_DIR = BASE_DIR / "site"
MANIFEST_FILE = BASE_DIR / "manifest.json"
SW_FILE = BASE_DIR / "sw.js"
DATA_CACHE_FILE = BASE_DIR / "data_cache.json"

def load_json(name, default):
    path = DATA_DIR / name
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def format_pace(duration_s, distance_m):
    if not distance_m or distance_m <= 0 or not duration_s or duration_s <= 0:
        return "--:--"
    dist_km = distance_m / 1000.0
    pace_s = duration_s / dist_km
    m = int(pace_s // 60)
    s = int(pace_s % 60)
    return f"{m}:{s:02d}"

def format_duration(seconds):
    if not seconds:
        return "0m"
    s = int(seconds)
    hours = s // 3600
    minutes = (s % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"

def clean_te_label(label):
    if not label:
        return "Aerobic"
    return label.replace("_", " ").title()

def process_data():
    activities = load_json("activities.json", [])
    if not activities and DATA_CACHE_FILE.exists():
        try:
            with open(DATA_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached and cached.get("recent_activities"):
                    print("-> Loaded data from data_cache.json fallback")
                    return cached
        except Exception as e:
            print(f"Warning reading {DATA_CACHE_FILE}: {e}")
    daily_summaries = load_json("daily_summaries.json", [])
    sleep_records = load_json("sleep.json", [])
    hrv_records = load_json("hrv.json", [])
    hr_zones = load_json("hr_zones.json", [])
    meta = load_json("meta.json", {})

    now = datetime.now()
    mumbai_date = datetime(2027, 1, 17)
    delhi_date = datetime(2027, 2, 28)
    days_to_mumbai = max(0, (mumbai_date - now).days)
    days_to_delhi = max(0, (delhi_date - now).days)

    target_marathon_seconds = (3 * 3600) + (28 * 60) # 3:28:00
    target_marathon_pace_s = target_marathon_seconds / 42.195 # 295.77 s/km -> 4:56/km

    # 1. Activities Processing (Running Focus)
    running_activities = []
    other_activities = []
    lifetime_km = 0.0
    
    for a in activities:
        sport = (a.get("activityType") or {}).get("typeKey", "other")
        dist_m = a.get("distance") or 0.0
        dur_s = a.get("duration") or 0.0
        dist_km = dist_m / 1000.0
        
        lifetime_km += dist_km
        
        # Pace vs marathon target
        pace_s = (dur_s / dist_km) if dist_km > 0 else 0
        pace_diff_s = round(pace_s - target_marathon_pace_s) if pace_s > 0 else 0
        
        # Zones
        z1 = round((a.get("hrTimeInZone_1") or 0) / 60)
        z2 = round((a.get("hrTimeInZone_2") or 0) / 60)
        z3 = round((a.get("hrTimeInZone_3") or 0) / 60)
        z4 = round((a.get("hrTimeInZone_4") or 0) / 60)
        z5 = round((a.get("hrTimeInZone_5") or 0) / 60)

        cadence = round(a.get("averageRunningCadenceInStepsPerMinute") or 0)
        power = round(a.get("avgPower") or 0)
        te_label = clean_te_label(a.get("trainingEffectLabel") or a.get("aerobicTrainingEffectMessage"))
        
        act_obj = {
            "id": a.get("activityId"),
            "name": a.get("activityName") or "Run",
            "date": (a.get("startTimeLocal") or "")[:10],
            "time": (a.get("startTimeLocal") or "")[11:16],
            "datetime": a.get("startTimeLocal") or "",
            "sport": sport,
            "dist_km": round(dist_km, 2),
            "dur_s": int(dur_s),
            "dur_fmt": format_duration(dur_s),
            "pace": format_pace(dur_s, dist_m),
            "pace_diff_s": pace_diff_s,
            "avg_hr": round(a.get("averageHR") or 0),
            "max_hr": round(a.get("maxHR") or 0),
            "elev_gain": round(a.get("elevationGain") or 0),
            "training_load": round(a.get("activityTrainingLoad") or 0, 1),
            "aerobic_te": round(a.get("aerobicTrainingEffect") or 0, 1),
            "te_label": te_label,
            "cadence": cadence,
            "power": power,
            "z1_m": z1, "z2_m": z2, "z3_m": z3, "z4_m": z4, "z5_m": z5
        }
        
        if sport == "running":
            running_activities.append(act_obj)
        else:
            other_activities.append(act_obj)

    running_activities.sort(key=lambda x: x["datetime"], reverse=True)
    all_acts_sorted = sorted(running_activities + other_activities, key=lambda x: x["datetime"], reverse=True)

    # 2. ACWR & 80/20 Intensity Distribution
    d7_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    d28_str = (now - timedelta(days=28)).strftime("%Y-%m-%d")

    runs_7d = [a for a in running_activities if a["date"] >= d7_str]
    runs_28d = [a for a in running_activities if a["date"] >= d28_str]

    acute_load_7d = round(sum(a["training_load"] for a in runs_7d), 1)
    chronic_load_total = sum(a["training_load"] for a in runs_28d)
    chronic_load_weekly = round(chronic_load_total / 4.0, 1)

    if chronic_load_weekly > 0:
        acwr = round(acute_load_7d / chronic_load_weekly, 2)
    else:
        acwr = 1.0

    if acwr < 0.8:
        acwr_status = "Recovery / Tapering"
        acwr_color = "var(--accent-blue)"
    elif 0.8 <= acwr <= 1.3:
        acwr_status = "Optimal Build Zone"
        acwr_color = "var(--accent-primary)"
    elif 1.3 < acwr <= 1.5:
        acwr_status = "High Strain Caution"
        acwr_color = "var(--accent-orange)"
    else:
        acwr_status = "Overreaching / High Spike"
        acwr_color = "var(--accent-red)"

    # 80/20 Distribution (Last 28 Days)
    total_z_easy = sum(a["z1_m"] + a["z2_m"] for a in runs_28d)
    total_z_hard = sum(a["z3_m"] + a["z4_m"] + a["z5_m"] for a in runs_28d)
    total_z = total_z_easy + total_z_hard
    if total_z > 0:
        pct_easy = round((total_z_easy / total_z) * 100)
        pct_hard = round((total_z_hard / total_z) * 100)
    else:
        pct_easy = 80
        pct_hard = 20

    # 3. Weekly Aggregates
    weeks = {}
    for a in all_acts_sorted:
        dt_str = a["date"]
        if not dt_str:
            continue
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d")
        except Exception:
            continue
            
        iso_year, iso_week, iso_day = dt.isocalendar()
        key = f"{iso_year}-W{iso_week:02d}"
        if key not in weeks:
            mon = dt - timedelta(days=iso_day - 1)
            weeks[key] = {
                "week_key": key,
                "monday": mon.strftime("%Y-%m-%d"),
                "label": mon.strftime("%b %d"),
                "running_km": 0.0,
                "runs_count": 0,
                "long_run_km": 0.0,
                "training_load": 0.0,
                "days": {d: [] for d in range(1, 8)}
            }
        
        weeks[key]["days"][iso_day].append(a)
        weeks[key]["training_load"] += a["training_load"]
        
        if a["sport"] == "running":
            weeks[key]["running_km"] += a["dist_km"]
            weeks[key]["runs_count"] += 1
            if a["dist_km"] > weeks[key]["long_run_km"]:
                weeks[key]["long_run_km"] = a["dist_km"]

    sorted_week_keys = sorted(weeks.keys())
    for k in sorted_week_keys:
        weeks[k]["running_km"] = round(weeks[k]["running_km"], 1)
        weeks[k]["long_run_km"] = round(weeks[k]["long_run_km"], 1)
        weeks[k]["training_load"] = round(weeks[k]["training_load"])

    recent_26_weeks = [weeks[k] for k in sorted_week_keys[-26:]] if sorted_week_keys else []
    
    current_iso_year, current_iso_week, _ = now.isocalendar()
    current_week_key = f"{current_iso_year}-W{current_iso_week:02d}"
    current_week_data = weeks.get(current_week_key, {
        "running_km": 0.0,
        "runs_count": 0,
        "long_run_km": 0.0,
        "training_load": 0.0,
        "days": {d: [] for d in range(1, 8)}
    })
    
    prior_weeks = [weeks[k]["running_km"] for k in sorted_week_keys[-5:-1]] if len(sorted_week_keys) >= 5 else [0]
    avg_4_week_km = round(sum(prior_weeks) / max(1, len(prior_weeks)), 1)

    # 4. Long Runs (15 km+) Marathon Prep
    long_runs = [a for a in running_activities if a["dist_km"] >= 15.0]
    long_runs.sort(key=lambda x: x["datetime"], reverse=True)

    # Latest Run Dynamics
    latest_run = running_activities[0] if running_activities else {}

    # 5. Recovery Biomarkers (90 Days Timeline)
    daily_map = {d.get("calendarDate"): d for d in daily_summaries if d.get("calendarDate")}
    sleep_map = {s.get("calendarDate"): s for s in sleep_records if s.get("calendarDate")}
    hrv_map = {h.get("calendarDate"): h for h in hrv_records if h.get("calendarDate")}

    timeline_90d = []
    latest_rhr = 0
    latest_hrv = 0
    latest_hrv_status = "BALANCED"
    latest_sleep_score = 0
    latest_sleep_hrs = 0.0

    for i in range(89, -1, -1):
        day_dt = now - timedelta(days=i)
        d_str = day_dt.strftime("%Y-%m-%d")
        
        d_sum = daily_map.get(d_str, {})
        s_sum = sleep_map.get(d_str, {})
        h_sum = hrv_map.get(d_str, {})
        
        rhr = (d_sum.get("heartRate") or {}).get("restingValue")
        if rhr and 30 < rhr < 120:
            latest_rhr = rhr
            
        hrv_val = h_sum.get("lastNightAvg") or h_sum.get("weeklyAvg")
        if hrv_val:
            latest_hrv = hrv_val
            latest_hrv_status = h_sum.get("status") or "BALANCED"
            
        sleep_s = s_sum.get("sleepTimeSeconds") or 0
        sleep_hrs = round(sleep_s / 3600.0, 1)
        sleep_score = (s_sum.get("sleepScores") or {}).get("overall", {}).get("value") or 0
        if sleep_score > 0:
            latest_sleep_score = sleep_score
        if sleep_hrs > 0:
            latest_sleep_hrs = sleep_hrs
        
        timeline_90d.append({
            "date": d_str,
            "label": day_dt.strftime("%b %d"),
            "rhr": rhr,
            "hrv": hrv_val,
            "sleep_hrs": sleep_hrs if sleep_hrs > 0 else None,
            "sleep_score": sleep_score if sleep_score > 0 else None
        })

    valid_recent_rhr = [t["rhr"] for t in timeline_90d[-7:] if t["rhr"]]
    avg_7d_rhr = round(sum(valid_recent_rhr) / len(valid_recent_rhr)) if valid_recent_rhr else (latest_rhr or 53)

    run_zones = {}
    if isinstance(hr_zones, list):
        for z in hr_zones:
            if z.get("sport") == "RUNNING" or (not run_zones and z.get("sport") == "DEFAULT"):
                run_zones = z

    # Sub-3:28 Pacing Strategies (Negative Split vs Mumbai Course vs Even Split)
    pacing_strategies = {
        "negative": {
            "name": "Negative Split (Recommended)",
            "subtitle": "Conservative start (5:02), steady cruise, strong second-half kick (4:50-4:54). Conserves glycogen.",
            "first_half": "1:44:45 (4:58/km)",
            "second_half": "1:43:15 (4:54/km)",
            "stages": [
                {"stage": "KM 0 - 5", "phase": "Settle & Avoid Chaos", "pace": "5:04 /km", "time": "25:20", "notes": "CST to Marine Drive. Hold back adrenaline."},
                {"stage": "KM 5 - 15", "phase": "Aerobic Cruise", "pace": "4:58 /km", "time": "1:15:00", "notes": "Peddar Road climb 1. Keep HR under Zone 3."},
                {"stage": "KM 15 - 28", "phase": "Sea Link Groove", "pace": "4:54 /km", "time": "2:18:42", "notes": "Flat & open. Lock into target cadence."},
                {"stage": "KM 28 - 35", "phase": "Peddar Road Return", "pace": "4:57 /km", "time": "2:53:21", "notes": "The decisive climb at KM 34. Don't surge."},
                {"stage": "KM 35 - 42.2", "phase": "Final Push to Finish", "pace": "4:49 /km", "time": "3:28:00", "notes": "Marine Drive kick. Empty the tank."}
            ]
        },
        "even": {
            "name": "Even Split (Flat Baseline)",
            "subtitle": "Constant 4:56/km from start to finish. Simple, but vulnerable to late-stage fatigue.",
            "first_half": "1:44:00 (4:56/km)",
            "second_half": "1:44:00 (4:56/km)",
            "stages": [
                {"stage": "KM 0 - 10", "phase": "First 10K", "pace": "4:56 /km", "time": "49:20", "notes": "Steady pace."},
                {"stage": "KM 10 - 20", "phase": "Second 10K", "pace": "4:56 /km", "time": "1:38:40", "notes": "Steady pace."},
                {"stage": "KM 20 - 30", "phase": "Third 10K", "pace": "4:56 /km", "time": "2:28:00", "notes": "Maintaining rhythm."},
                {"stage": "KM 30 - 40", "phase": "Fourth 10K", "pace": "4:56 /km", "time": "3:17:20", "notes": "Fighting fatigue."},
                {"stage": "KM 40 - 42.2", "phase": "Final 2.2K", "pace": "4:56 /km", "time": "3:28:00", "notes": "Cross the finish line."}
            ]
        }
    }

    result = {
        "sync_time": meta.get("last_sync", now.isoformat())[:16].replace("T", " "),
        "mumbai": {
            "name": "Tata Mumbai Marathon",
            "date": "Jan 17, 2027",
            "target_time": "3:28:00",
            "target_pace": "4:56 /km",
            "days_left": days_to_mumbai,
            "weeks_left": round(days_to_mumbai / 7, 1)
        },
        "delhi": {
            "name": "New Delhi Marathon",
            "date": "Feb 28, 2027",
            "target_time": "3:28:00",
            "target_pace": "4:56 /km",
            "days_left": days_to_delhi,
            "weeks_left": round(days_to_delhi / 7, 1)
        },
        "current_week": current_week_data,
        "avg_4_week_km": avg_4_week_km,
        "latest_rhr": latest_rhr or 53,
        "avg_7d_rhr": avg_7d_rhr,
        "latest_hrv": latest_hrv or 45,
        "latest_hrv_status": latest_hrv_status,
        "acute_load_7d": acute_load_7d,
        "chronic_load_weekly": chronic_load_weekly,
        "acwr": acwr,
        "acwr_status": acwr_status,
        "acwr_color": acwr_color,
        "pct_easy": pct_easy,
        "pct_hard": pct_hard,
        "latest_sleep_score": latest_sleep_score or 82,
        "latest_sleep_hrs": latest_sleep_hrs or 7.5,
        "total_runs": len(running_activities),
        "lifetime_km": round(lifetime_km, 1),
        "recent_26_weeks": recent_26_weeks,
        "long_runs": long_runs[:12],
        "latest_run": latest_run,
        "timeline_90d": timeline_90d,
        "recent_activities": running_activities[:25],
        "hr_zones": run_zones,
        "pacing_strategies": pacing_strategies
    }
    try:
        with open(DATA_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return result

def generate_pwa_files():
    manifest = {
        "name": "Garmini",
        "short_name": "Garmini",
        "description": "Garmin Marathon Training Command Center",
        "start_url": "/?mode=pwa",
        "scope": "/",
        "display": "standalone",
        "background_color": "#030712",
        "theme_color": "#38bdf8",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "/icon-maskable-192.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable"},
            {"src": "/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
        ]
    }
    
    for path in [MANIFEST_FILE, BASE_DIR / "site" / "manifest.json", BASE_DIR / "site" / "manifest.webmanifest"]:
        if path.parent.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

    sw_code = """// Garmini Service Worker v5
const CACHE_NAME = 'garmini-v5';
const ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-192.png',
  '/icon-maskable-512.png',
  '/apple-touch-icon.png',
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(
      keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          if (res && res.status === 200) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(e.request, copy));
          }
          return res;
        })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});
"""
    with open(SW_FILE, "w", encoding="utf-8") as f:
        f.write(sw_code)

    site_sw = BASE_DIR / "site" / "sw.js"
    if site_sw.parent.exists():
        with open(site_sw, "w", encoding="utf-8") as f:
            f.write(sw_code)

def generate_dashboard_html(data):
    data_json = json.dumps(data, ensure_ascii=False)
    
    html = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>Garmini • Sub-3:28 Marathon Hub</title>
  
  <!-- PWA Meta -->
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#030712" id="metaThemeColor">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Garmini">
  <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
  <link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">

  <!-- Early PWA Prompt Capture -->
  <script>
    window.__deferredPrompt = null;
    window.addEventListener('beforeinstallprompt', (e) => {{
      e.preventDefault();
      window.__deferredPrompt = e;
      window.dispatchEvent(new CustomEvent('pwa-prompt-ready'));
    }});
  </script>

  <!-- Chart.js CDN -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

  <style>
    /* Dark Theme Tokens (Default: Midnight Athletic) */
    :root, [data-theme="dark"] {{
      color-scheme: dark;
      --bg: #030712;
      --card-bg: #0b1329;
      --card-bg-subtle: #142244;
      --card-border: #1e335b;
      --card-border-glow: #2c487b;
      --text-main: #ffffff;
      --text-muted: #bfdbfe;
      --text-dim: #93c5fd;
      
      --accent-primary: #38bdf8; /* Electric Sky Blue */
      --accent-primary-hover: #0284c7;
      --accent-primary-subtle: rgba(56, 189, 248, 0.18);
      --accent-cyan: #2dd4bf;
      --accent-blue: #60a5fa;
      --accent-orange: #fbbf24;
      --accent-red: #fb7185;
      --accent-purple: #e879f9;
      
      --chart-grid: rgba(255, 255, 255, 0.06);
      --chart-text: #93c5fd;
      --banner-bg: linear-gradient(90deg, #0284c7 0%, #2563eb 100%);
      --focus-ring: #38bdf8;

      /* Sleek Themed Scrollbars */
      --scrollbar-track: rgba(11, 19, 41, 0.45);
      --scrollbar-thumb: rgba(147, 197, 253, 0.24);
      --scrollbar-thumb-hover: #38bdf8;

      --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      --font-mono: ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Consolas, "Liberation Mono", Menlo, monospace;
    }}

    /* Light Theme Tokens (Athletic Daylight) */
    [data-theme="light"] {{
      color-scheme: light;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --card-bg-subtle: #f1f5f9;
      --card-border: #cbd5e1;
      --card-border-glow: #94a3b8;
      --text-main: #0f172a;
      --text-muted: #475569;
      --text-dim: #64748b;
      
      --accent-primary: #0284c7; /* Athletic Ocean Blue */
      --accent-primary-hover: #0369a1;
      --accent-primary-subtle: rgba(2, 132, 199, 0.12);
      --accent-cyan: #0d9488;
      --accent-blue: #2563eb;
      --accent-orange: #d97706;
      --accent-red: #e11d48;
      --accent-purple: #9333ea;
      
      --chart-grid: rgba(0, 0, 0, 0.07);
      --chart-text: #475569;
      --banner-bg: linear-gradient(90deg, #0284c7 0%, #2563eb 100%);
      --focus-ring: #0284c7;

      /* Sleek Themed Scrollbars */
      --scrollbar-track: rgba(241, 245, 249, 0.7);
      --scrollbar-thumb: rgba(100, 116, 139, 0.35);
      --scrollbar-thumb-hover: #0284c7;
    }}

    /* Modern Custom Scrollbars (Cross-Platform / Cross-Browser) */
    * {{
      scrollbar-width: thin;
      scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);
    }}

    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}

    ::-webkit-scrollbar-track {{
      background: var(--scrollbar-track);
      border-radius: 9999px;
    }}

    ::-webkit-scrollbar-thumb {{
      background-color: var(--scrollbar-thumb);
      border-radius: 9999px;
      border: 1px solid transparent;
      background-clip: padding-box;
      transition: background-color 0.2s ease;
    }}

    ::-webkit-scrollbar-thumb:hover {{
      background-color: var(--scrollbar-thumb-hover);
    }}

    ::-webkit-scrollbar-corner {{
      background: transparent;
    }}

    ::-webkit-scrollbar-button {{
      display: none !important;
      width: 0 !important;
      height: 0 !important;
    }}

    /* Reset & Prevent Any Horizontal Overflow */
    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
      transition: background-color 0.2s ease, border-color 0.2s ease, color 0.15s ease;
    }}

    html, body {{
      width: 100%;
      max-width: 100vw;
      overflow-x: hidden !important;
      position: relative;
    }}

    body {{
      background-color: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 16px;
      max-width: 1320px;
      margin: 0 auto;
      font-size: 15px;
    }}

    main {{
      width: 100%;
      max-width: 100%;
      min-width: 0;
    }}

    *:focus-visible {{
      outline: 2px solid var(--focus-ring) !important;
      outline-offset: 2px !important;
    }}

    /* Tabular Numerals for Numerical Clarity */
    .num-tabular, .race-stat-val, .metric-val, .splits-table td, td, .lr-dist, .lr-metrics {{
      font-family: var(--font-mono);
      font-variant-numeric: tabular-nums;
      font-feature-settings: "tnum" 1;
    }}

    /* Skip Link for Accessibility */
    .skip-link {{
      position: absolute;
      top: -60px;
      left: 14px;
      background: var(--accent-primary);
      color: #ffffff;
      padding: 8px 16px;
      font-weight: 700;
      border-radius: 6px;
      z-index: 99999;
      text-decoration: none;
      font-size: 0.85rem;
      transition: top 0.2s ease-in-out;
    }}
    .skip-link:focus {{
      top: 14px;
    }}

    .metric-svg-icon {{
      width: 19px;
      height: 19px;
      stroke-width: 2.2;
      stroke: currentColor;
      fill: none;
      stroke-linecap: round;
      stroke-linejoin: round;
      flex-shrink: 0;
      display: inline-block;
      vertical-align: middle;
    }}

    /* Top PWA Install Bar */
    .pwa-install-bar {{
      background: var(--banner-bg);
      color: #ffffff;
      padding: 10px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-radius: 12px;
      margin-bottom: 16px;
      box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
      font-size: 0.86rem;
      gap: 12px;
      max-width: 100%;
      flex-wrap: wrap;
    }}

    @media all and (display-mode: standalone),
           all and (display-mode: fullscreen),
           all and (display-mode: minimal-ui) {{
      #pwaInstallBanner, .pwa-install-bar {{
        display: none !important;
      }}
    }}

    .pwa-banner-content {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
      min-width: 200px;
    }}

    .pwa-banner-icon {{
      width: 20px;
      height: 20px;
      fill: currentColor;
      flex-shrink: 0;
    }}

    .pwa-banner-actions {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .pwa-btn-install {{
      background: #ffffff;
      color: #0f172a;
      font-weight: 700;
      font-size: 0.8rem;
      padding: 7px 16px;
      border-radius: 6px;
      border: none;
      cursor: pointer;
      min-height: 36px;
    }}

    .pwa-btn-dismiss {{
      background: transparent;
      border: none;
      color: rgba(255, 255, 255, 0.85);
      font-size: 1.2rem;
      cursor: pointer;
      padding: 4px 8px;
      min-height: 36px;
      min-width: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    /* Header Nav */
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 14px 20px;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      margin-bottom: 20px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
      flex-wrap: wrap;
      gap: 12px;
      width: 100%;
      max-width: 100%;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .brand-logo {{
      width: 40px;
      height: 40px;
      background: var(--card-bg-subtle);
      border: 2px solid var(--accent-primary);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 16px var(--accent-primary-subtle);
      flex-shrink: 0;
    }}

    .brand-logo svg {{
      width: 20px;
      height: 20px;
      fill: var(--accent-primary);
    }}

    .brand-text h1 {{
      font-size: 1.35rem;
      font-weight: 800;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      color: var(--text-main);
      line-height: 1.2;
    }}

    .brand-text p {{
      font-size: 0.78rem;
      color: var(--text-dim);
      font-family: var(--font-mono);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}

    .header-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}

    /* Theme Toggle Button */
    .theme-toggle-btn {{
      background: var(--card-bg-subtle);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 6px 14px;
      border-radius: 20px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 7px;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      font-weight: 600;
      min-height: 34px;
      transition: all 0.2s ease;
    }}

    .theme-toggle-btn:hover {{
      border-color: var(--accent-primary);
      background: var(--accent-primary-subtle);
      color: var(--accent-primary);
    }}

    .theme-toggle-icon {{
      font-size: 0.95rem;
      line-height: 1;
    }}

    .badge-sync {{
      font-family: var(--font-mono);
      font-size: 0.76rem;
      color: var(--accent-primary);
      background: var(--accent-primary-subtle);
      border: 1px solid var(--accent-primary);
      padding: 6px 12px;
      border-radius: 20px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      min-height: 34px;
    }}

    .pulse-dot {{
      width: 7px;
      height: 7px;
      background-color: var(--accent-primary);
      border-radius: 50%;
      box-shadow: 0 0 8px var(--accent-primary);
      animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
      0%, 100% {{ opacity: 1; transform: scale(1); }}
      50% {{ opacity: 0.35; transform: scale(0.85); }}
    }}

    /* Race Countdown Banner */
    .marathon-hero {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 22px;
      width: 100%;
      max-width: 100%;
    }}

    @media (max-width: 768px) {{
      .marathon-hero {{
        grid-template-columns: 1fr;
      }}
    }}

    .race-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px 22px;
      position: relative;
      overflow: hidden;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
      min-width: 0;
      max-width: 100%;
    }}

    .race-card::before {{
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      width: 5px;
      height: 100%;
      background: var(--accent-primary);
    }}

    .race-top {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 14px;
      flex-wrap: wrap;
      gap: 8px;
    }}

    .race-title {{
      font-size: 1.18rem;
      font-weight: 700;
      color: var(--text-main);
    }}

    .race-date {{
      font-size: 0.82rem;
      color: var(--text-dim);
      font-family: var(--font-mono);
      margin-top: 2px;
    }}

    .race-pill {{
      font-family: var(--font-mono);
      font-size: 0.74rem;
      padding: 4px 10px;
      border-radius: 6px;
      text-transform: uppercase;
      font-weight: 700;
      background: var(--accent-primary-subtle);
      color: var(--accent-primary);
      border: 1px solid var(--accent-primary);
      white-space: nowrap;
    }}

    .race-stats {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      background: var(--card-bg-subtle);
      padding: 14px 16px;
      border-radius: 12px;
      border: 1px solid var(--card-border);
      min-width: 0;
      max-width: 100%;
    }}

    .race-stat-col {{
      text-align: left;
      min-width: 0;
      overflow: hidden;
    }}

    .race-stat-label {{
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      font-weight: 600;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .race-stat-val {{
      font-size: 1.25rem;
      font-weight: 800;
      color: var(--text-main);
      margin-top: 3px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .race-stat-val.highlight {{
      color: var(--accent-primary);
      text-shadow: 0 0 10px var(--accent-primary-subtle);
    }}

    .race-stat-sub {{
      font-size: 0.73rem;
      color: var(--text-muted);
      margin-top: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    /* Key Runner Metrics Grid */
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 24px;
      width: 100%;
      max-width: 100%;
    }}

    @media (max-width: 1080px) and (min-width: 681px) {{
      .metrics-grid {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
      }}
    }}

    @media (max-width: 680px) {{
      .metrics-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
        margin-bottom: 16px;
      }}
      .metric-card {{
        padding: 10px 12px !important;
        border-radius: 12px !important;
      }}
      .metric-label {{
        font-size: 0.68rem !important;
        letter-spacing: 0.4px;
      }}
      .metric-label .metric-svg-icon {{
        width: 15px !important;
        height: 15px !important;
      }}
      .metric-val {{
        font-size: 1.35rem !important;
        margin: 4px 0 2px 0 !important;
        gap: 3px !important;
      }}
      .metric-unit {{
        font-size: 0.74rem !important;
      }}
      .metric-sub {{
        font-size: 0.68rem !important;
        line-height: 1.25 !important;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }}
      /* Card 5 (Sleep Recovery) spans both columns horizontally */
      .metric-card:last-child {{
        grid-column: span 2;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 10px 14px !important;
      }}
      .metric-card:last-child .metric-val {{
        margin: 0 !important;
        font-size: 1.35rem !important;
      }}
      .metric-card:last-child .metric-sub {{
        text-align: right;
      }}
    }}

    .metric-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 18px;
      position: relative;
      min-width: 0;
      max-width: 100%;
    }}

    .metric-label {{
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .metric-val {{
      font-size: 1.9rem;
      font-weight: 800;
      color: var(--text-main);
      margin: 8px 0 4px 0;
      display: flex;
      align-items: baseline;
      gap: 5px;
      flex-wrap: wrap;
    }}

    .metric-unit {{
      font-size: 0.88rem;
      color: var(--text-muted);
      font-weight: 500;
    }}

    .metric-sub {{
      font-size: 0.78rem;
      color: var(--text-dim);
      font-family: var(--font-mono);
      word-break: break-word;
    }}

    /* Training Load ACWR & 80/20 Hub */
    .advanced-runner-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 24px;
      width: 100%;
      max-width: 100%;
    }}

    @media (max-width: 860px) {{
      .advanced-runner-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .runner-intel-card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      min-width: 0;
      max-width: 100%;
      overflow: hidden;
    }}

    .intel-title {{
      font-size: 0.96rem;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 8px;
    }}

    /* Progress & Polarized Gauge */
    .gauge-bar {{
      height: 16px;
      background: var(--card-bg-subtle);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      margin: 12px 0;
      border: 1px solid var(--card-border);
      width: 100%;
    }}

    .gauge-fill-easy {{
      background: var(--accent-primary);
      height: 100%;
    }}

    .gauge-fill-hard {{
      background: var(--accent-orange);
      height: 100%;
    }}

    /* Pacing Strategy Buttons */
    .pace-strat-btn {{
      background: var(--card-bg-subtle);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      font-family: var(--font-mono);
      font-size: 0.75rem;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      min-height: 34px;
      transition: all 0.15s ease;
    }}

    .pace-strat-btn:hover {{
      color: var(--text-main);
      border-color: var(--card-border-glow);
    }}

    .pace-strat-btn.active {{
      background: var(--accent-primary-subtle);
      color: var(--accent-primary);
      border-color: var(--accent-primary);
      font-weight: 700;
    }}

    /* Table Scroll Wrapper to Prevent Page Overflow */
    .table-scroll-wrap {{
      width: 100%;
      max-width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      margin-top: 10px;
      padding-bottom: 6px;
    }}

    .splits-table {{
      width: 100%;
      min-width: 480px;
      border-collapse: collapse;
      font-size: 0.82rem;
    }}

    .splits-table th {{
      color: var(--text-dim);
      padding: 8px 10px;
      border-bottom: 1px solid var(--card-border);
      text-align: left;
      font-size: 0.74rem;
      text-transform: uppercase;
      white-space: nowrap;
    }}

    .splits-table td {{
      padding: 10px;
      border-bottom: 1px solid var(--card-border);
      white-space: nowrap;
    }}

    .splits-table th:last-child,
    .splits-table td:last-child {{
      white-space: normal;
      min-width: 140px;
      line-height: 1.35;
    }}

    /* Section Layouts */
    .section-title {{
      font-size: 1.05rem;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }}

    .grid-2col {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 18px;
      margin-bottom: 24px;
      width: 100%;
      max-width: 100%;
    }}

    @media (max-width: 992px) {{
      .grid-2col {{
        grid-template-columns: 1fr;
      }}
    }}

    .chart-panel {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 20px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
      min-width: 0;
      max-width: 100%;
      overflow: hidden;
    }}

    .chart-container {{
      position: relative;
      height: 250px;
      width: 100%;
      max-width: 100%;
    }}

    /* Day Schedule */
    .current-week-bar {{
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 8px;
      margin-top: 14px;
      width: 100%;
      max-width: 100%;
    }}

    @media (max-width: 640px) {{
      .current-week-bar {{
        display: flex;
        overflow-x: auto;
        padding-bottom: 8px;
        -webkit-overflow-scrolling: touch;
      }}
      .day-chip {{
        min-width: 64px;
        flex: 1 0 auto;
      }}
    }}

    .day-chip {{
      background: var(--card-bg-subtle);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 9px 6px;
      text-align: center;
      min-width: 0;
    }}

    .day-chip.active-day {{
      border-color: var(--accent-primary);
      background: var(--accent-primary-subtle);
    }}

    .day-chip.today {{
      border-color: var(--accent-primary);
      box-shadow: 0 0 10px var(--accent-primary-subtle);
    }}

    .day-name {{
      font-size: 0.72rem;
      color: var(--text-dim);
      text-transform: uppercase;
      font-family: var(--font-mono);
      font-weight: 600;
    }}

    .day-dist {{
      font-size: 0.92rem;
      font-weight: 800;
      color: var(--text-main);
      margin: 4px 0 2px 0;
    }}

    .day-type {{
      font-size: 0.74rem;
      color: var(--accent-primary);
      font-weight: 600;
    }}

    /* Long Run List */
    .long-runs-list {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      max-height: 290px;
      overflow-y: auto;
      width: 100%;
      max-width: 100%;
      padding-right: 6px;
      scrollbar-gutter: stable;
    }}

    .long-run-item {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--card-bg-subtle);
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 12px 14px;
      gap: 8px;
      min-width: 0;
    }}

    .lr-date {{
      font-size: 0.8rem;
      color: var(--text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    .lr-dist {{
      font-size: 1.05rem;
      font-weight: 800;
      color: var(--accent-primary);
      white-space: nowrap;
    }}

    .lr-metrics {{
      font-size: 0.8rem;
      color: var(--text-muted);
      text-align: right;
      white-space: nowrap;
      flex-shrink: 0;
    }}

    /* Interactive Table Toolbar & Filters */
    .table-toolbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
      width: 100%;
      max-width: 100%;
    }}

    .activity-filter-group {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .filter-btn {{
      background: var(--card-bg-subtle);
      border: 1px solid var(--card-border);
      color: var(--text-muted);
      font-family: var(--font-mono);
      font-size: 0.76rem;
      padding: 6px 12px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 600;
      min-height: 34px;
      transition: all 0.15s ease;
      white-space: nowrap;
    }}

    .filter-btn:hover {{
      color: var(--text-main);
      border-color: var(--card-border-glow);
    }}

    .filter-btn.active {{
      background: var(--accent-primary-subtle);
      color: var(--accent-primary);
      border-color: var(--accent-primary);
      font-weight: 700;
    }}

    .activity-search-input {{
      background: var(--card-bg-subtle);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.82rem;
      font-family: var(--font-sans);
      outline: none;
      min-height: 34px;
      min-width: 200px;
      transition: border-color 0.2s ease;
    }}

    .activity-search-input:focus {{
      border-color: var(--accent-primary);
    }}

    /* Table Container with Sticky Header */
    .table-container {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      overflow-x: auto;
      max-height: 520px;
      overflow-y: auto;
      margin-bottom: 24px;
      width: 100%;
      max-width: 100%;
      -webkit-overflow-scrolling: touch;
      scrollbar-gutter: stable;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
      text-align: left;
    }}

    th {{
      position: sticky;
      top: -16px;
      background: var(--card-bg);
      padding: 12px 14px;
      font-size: 0.74rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: var(--text-dim);
      border-bottom: 2px solid var(--card-border);
      z-index: 2;
      white-space: nowrap;
    }}

    td {{
      padding: 12px 14px;
      border-bottom: 1px solid var(--card-border);
      white-space: nowrap;
    }}

    tr:hover td {{
      background: var(--card-bg-subtle);
    }}

    .te-badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.72rem;
      text-transform: uppercase;
      font-weight: 700;
      background: var(--accent-primary-subtle);
      color: var(--accent-primary);
      border: 1px solid var(--accent-primary);
      white-space: nowrap;
    }}

    footer {{
      text-align: center;
      padding: 26px 0 14px 0;
      color: var(--text-dim);
      font-size: 0.8rem;
      font-family: var(--font-mono);
      width: 100%;
    }}

    /* Ultra-Responsive Mobile Ergonomics */
    @media (max-width: 540px) {{
      body {{
        padding: 10px 8px;
      }}
      header {{
        padding: 12px 14px;
      }}
      .brand-text h1 {{
        font-size: 1.2rem;
      }}
      .race-card {{
        padding: 14px 14px;
      }}
      .race-stats {{
        padding: 10px 8px;
        gap: 6px;
      }}
      .race-stat-label {{
        font-size: 0.68rem;
      }}
      .race-stat-val {{
        font-size: 1.05rem;
      }}
      .race-stat-sub {{
        font-size: 0.68rem;
      }}
      .runner-intel-card {{
        padding: 14px;
      }}
      .chart-panel {{
        padding: 14px;
      }}
      .table-container {{
        padding: 10px;
      }}
      .table-toolbar {{
        flex-direction: column;
        align-items: stretch;
      }}
      .activity-filter-group {{
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 6px;
        -webkit-overflow-scrolling: touch;
      }}
      .activity-search-input {{
        min-width: 100%;
        width: 100%;
      }}
      .pwa-install-bar {{
        flex-direction: column;
        align-items: flex-start;
        padding: 12px 14px;
      }}
      .pwa-banner-actions {{
        width: 100%;
        justify-content: flex-end;
      }}
    }}
  </style>
</head>
<body>

  <!-- Accessible Skip-to-Content Link -->
  <a href="#mainContent" class="skip-link">Skip to training metrics</a>

  <!-- Top PWA Install Bar -->
  <div id="pwaInstallBanner" class="pwa-install-bar" style="display: none;" role="region" aria-label="Install Application">
    <div class="pwa-banner-content">
      <svg class="pwa-banner-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
      <span><strong>Install Garmini:</strong> Offline-capable marathon training companion.</span>
    </div>
    <div class="pwa-banner-actions">
      <button class="pwa-btn-install" onclick="handlePWAInstall()">Install</button>
      <button class="pwa-btn-dismiss" onclick="handlePWADismiss()" title="Dismiss banner" aria-label="Dismiss banner">✕</button>
    </div>
  </div>

  <!-- Header -->
  <header role="banner">
    <div class="brand">
      <div class="brand-logo" aria-hidden="true">
        <svg viewBox="0 0 24 24"><polygon points="12,2 22,22 12,18 2,22"/></svg>
      </div>
      <div class="brand-text">
        <h1>Garmini</h1>
        <p>Marathon Performance Hub • Sub-3:28</p>
      </div>
    </div>
    
    <div class="header-actions">
      <!-- Dark / Light Theme Toggle -->
      <button id="themeToggleBtn" class="theme-toggle-btn" onclick="toggleTheme()" aria-label="Toggle theme" title="Switch between dark and light theme">
        <span id="themeToggleIcon" class="theme-toggle-icon">☀️</span>
        <span id="themeToggleText" class="theme-toggle-text">Light</span>
      </button>

      <div class="badge-sync" aria-live="polite">
        <span class="pulse-dot" aria-hidden="true"></span>
        <span>Synced {data["sync_time"]}</span>
      </div>
    </div>
  </header>

  <main id="mainContent">
    <!-- Dual Marathon Countdown & Pace Targets -->
    <div class="marathon-hero">
      <div class="race-card" role="region" aria-label="Target A Tata Mumbai Marathon">
        <div class="race-top">
          <div>
            <div class="race-title">{data["mumbai"]["name"]}</div>
            <div class="race-date">{data["mumbai"]["date"]}</div>
          </div>
          <span class="race-pill">Target A • Mumbai</span>
        </div>
        <div class="race-stats">
          <div class="race-stat-col">
            <div class="race-stat-label">Countdown</div>
            <div class="race-stat-val highlight">{data["mumbai"]["days_left"]} <span class="race-stat-sub">days</span></div>
            <div class="race-stat-sub">{data["mumbai"]["weeks_left"]} wks out</div>
          </div>
          <div class="race-stat-col">
            <div class="race-stat-label">Goal Target</div>
            <div class="race-stat-val">{data["mumbai"]["target_time"]}</div>
            <div class="race-stat-sub">Sub-3:28</div>
          </div>
          <div class="race-stat-col">
            <div class="race-stat-label">Req Pace</div>
            <div class="race-stat-val highlight">{data["mumbai"]["target_pace"]}</div>
            <div class="race-stat-sub">4:56/km</div>
          </div>
        </div>
      </div>

      <div class="race-card" role="region" aria-label="Target B New Delhi Marathon">
        <div class="race-top">
          <div>
            <div class="race-title">{data["delhi"]["name"]}</div>
            <div class="race-date">{data["delhi"]["date"]}</div>
          </div>
          <span class="race-pill">Target B • Delhi</span>
        </div>
        <div class="race-stats">
          <div class="race-stat-col">
            <div class="race-stat-label">Countdown</div>
            <div class="race-stat-val highlight">{data["delhi"]["days_left"]} <span class="race-stat-sub">days</span></div>
            <div class="race-stat-sub">{data["delhi"]["weeks_left"]} wks out</div>
          </div>
          <div class="race-stat-col">
            <div class="race-stat-label">Goal Target</div>
            <div class="race-stat-val">{data["delhi"]["target_time"]}</div>
            <div class="race-stat-sub">Sub-3:28</div>
          </div>
          <div class="race-stat-col">
            <div class="race-stat-label">Req Pace</div>
            <div class="race-stat-val highlight">{data["delhi"]["target_pace"]}</div>
            <div class="race-stat-sub">4:56/km</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Runner Pillars: Essential Weekly & Physiological Signals -->
    <div class="metrics-grid">
      <!-- Weekly Volume -->
      <div class="metric-card">
        <div class="metric-label">
          <span>Current Week</span>
          <svg class="metric-svg-icon" style="color: var(--accent-primary);" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        </div>
        <div class="metric-val">{data["current_week"]["running_km"]} <span class="metric-unit">km</span></div>
        <div class="metric-sub">{data["current_week"]["runs_count"]} runs • 4-Wk Avg: {data["avg_4_week_km"]} km</div>
      </div>

      <!-- ACWR (Training Stress Ratio) -->
      <div class="metric-card">
        <div class="metric-label">
          <span>Training Load (ACWR)</span>
          <svg class="metric-svg-icon" style="color: {data['acwr_color']};" viewBox="0 0 24 24" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        </div>
        <div class="metric-val" style="color: {data['acwr_color']};">{data["acwr"]} <span class="metric-unit">ratio</span></div>
        <div class="metric-sub">{data["acwr_status"]}</div>
      </div>

      <!-- Resting HR -->
      <div class="metric-card">
        <div class="metric-label">
          <span>Resting HR</span>
          <svg class="metric-svg-icon" style="color: var(--accent-red);" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>
        </div>
        <div class="metric-val" style="color: var(--accent-red);">{data["latest_rhr"]} <span class="metric-unit">bpm</span></div>
        <div class="metric-sub">7-Day Rolling Avg: {data["avg_7d_rhr"]} bpm</div>
      </div>

      <!-- HRV Recovery -->
      <div class="metric-card">
        <div class="metric-label">
          <span>Nightly HRV</span>
          <svg class="metric-svg-icon" style="color: var(--accent-cyan);" viewBox="0 0 24 24" aria-hidden="true"><polygon points="12 2.5 4.5 13 11 13 10 21.5 19.5 10 13 10 12 2.5"/></svg>
        </div>
        <div class="metric-val" style="color: var(--accent-cyan);">{data["latest_hrv"]} <span class="metric-unit">ms</span></div>
        <div class="metric-sub">Status: {data["latest_hrv_status"]}</div>
      </div>

      <!-- Sleep Recovery -->
      <div class="metric-card">
        <div class="metric-label">
          <span>Sleep Recovery</span>
          <svg class="metric-svg-icon" style="color: var(--accent-blue);" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.5 12.5A8.5 8.5 0 1 1 11.5 3.5a6.5 6.5 0 0 0 9 9z"/></svg>
        </div>
        <div class="metric-val" style="color: var(--accent-blue);">{data["latest_sleep_score"]} <span class="metric-unit">pts</span></div>
        <div class="metric-sub">{data["latest_sleep_hrs"]} hrs last night</div>
      </div>
    </div>

    <!-- Training Science: 80/20 Distribution & Sub-3:28 Split Calculator -->
    <div class="advanced-runner-grid">
      <!-- 80/20 Polarized Distribution -->
      <div class="runner-intel-card">
        <div class="intel-title">
          <span>80/20 Intensity Polarized Distribution (28 Days)</span>
          <span style="font-size: 0.78rem; color: var(--accent-primary); font-family: var(--font-mono); font-weight: 700;">Garmin HR Zones</span>
        </div>
        <p style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 10px;">
          High-performance marathoners aim for ~80% easy volume (Zone 1–2) to build mitochondrial density while avoiding injury before race day.
        </p>
        <div class="gauge-bar">
          <div class="gauge-fill-easy" style="width: {data['pct_easy']}%;" title="Zone 1-2 Easy: {data['pct_easy']}%"></div>
          <div class="gauge-fill-hard" style="width: {data['pct_hard']}%;" title="Zone 3-5 Quality: {data['pct_hard']}%"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-family: var(--font-mono); font-weight: 600; flex-wrap: wrap; gap: 4px;">
          <span style="color: var(--accent-primary);">● {data["pct_easy"]}% Zone 1–2 (Easy Base)</span>
          <span style="color: var(--accent-orange);">● {data["pct_hard"]}% Zone 3–5 (Quality)</span>
        </div>
      </div>

      <!-- Sub-3:28 Interactive Marathon Pacing Plan -->
      <div class="runner-intel-card">
        <div class="intel-title">
          <span>Sub-3:28:00 Marathon Pacing Strategy</span>
          <div style="display: flex; gap: 6px; flex-wrap: wrap;">
            <button id="btnPaceNeg" class="pace-strat-btn active" onclick="setPacingStrategy('negative')">Negative Split (Recommended)</button>
            <button id="btnPaceEven" class="pace-strat-btn" onclick="setPacingStrategy('even')">Even Split (Flat)</button>
          </div>
        </div>
        <p id="paceStrategySubtitle" style="font-size: 0.78rem; color: var(--text-muted); margin-bottom: 10px;"></p>
        <div id="paceHalvesBadge" style="display: flex; gap: 10px; font-family: var(--font-mono); font-size: 0.76rem; margin-bottom: 12px; flex-wrap: wrap;"></div>
        <div class="table-scroll-wrap">
          <table class="splits-table">
            <thead>
              <tr>
                <th>Stage</th>
                <th>Phase Strategy</th>
                <th>Target Pace</th>
                <th>Split Clock</th>
                <th>Course Focus</th>
              </tr>
            </thead>
            <tbody id="pacingTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Weekly Mileage & Long Run Progression -->
    <div class="grid-2col">
      <div class="chart-panel">
        <div class="intel-title">
          <span>26-Week Mileage & Weekly Longest Run</span>
        </div>
        <div class="chart-container">
          <canvas id="weeklyVolumeChart"></canvas>
        </div>

        <!-- Current Week Day-by-Day -->
        <div style="margin-top: 18px; border-top: 1px solid var(--card-border); padding-top: 14px;">
          <div style="font-size: 0.76rem; color: var(--text-dim); text-transform: uppercase; font-family: var(--font-mono); font-weight: 700; margin-bottom: 8px;">
            Current Week Training Schedule
          </div>
          <div class="current-week-bar" id="currentWeekContainer"></div>
        </div>
      </div>

      <!-- Long Run Marathon Tracker (15 km+) -->
      <div class="chart-panel">
        <div class="intel-title">
          <span>Long Run Progression (15k+)</span>
          <span style="font-size: 0.76rem; color: var(--text-dim); font-family: var(--font-mono); font-weight: 700;">Target: 4:56/km</span>
        </div>
        <div class="long-runs-list" id="longRunsList"></div>
      </div>
    </div>

    <!-- Recovery Trends: Resting HR & HRV -->
    <div class="grid-2col">
      <div class="chart-panel">
        <div class="intel-title"><span>Resting Heart Rate & HRV Baseline (90 Days)</span></div>
        <div class="chart-container">
          <canvas id="rhrHrvChart"></canvas>
        </div>
      </div>

      <div class="chart-panel">
        <div class="intel-title"><span>Sleep Quality & Recovery Score (90 Days)</span></div>
        <div class="chart-container">
          <canvas id="sleepChart"></canvas>
        </div>
      </div>
    </div>

    <!-- Running Log with Interactive Filters & Dynamics -->
    <div class="section-title">
      <span>Recent Running Sessions & Dynamics</span>
    </div>

    <div class="table-toolbar">
      <div class="activity-filter-group" role="group" aria-label="Filter activities by category">
        <button class="filter-btn active" id="filterAll" onclick="filterActivities('all')">All Runs</button>
        <button class="filter-btn" id="filterLong" onclick="filterActivities('long')">Long Runs (15k+)</button>
        <button class="filter-btn" id="filterFast" onclick="filterActivities('fast')">Target Pace (≤ 4:56)</button>
        <button class="filter-btn" id="filterEasy" onclick="filterActivities('easy')">Aerobic Base</button>
      </div>
      <input type="text" id="activitySearch" class="activity-search-input" placeholder="Search sessions or dates..." aria-label="Search activities by name or date" oninput="onSearchActivities(this.value)">
    </div>

    <div class="table-container">
      <table aria-label="Running Sessions and Dynamics">
        <thead>
          <tr>
            <th>Date</th>
            <th>Activity</th>
            <th>Distance</th>
            <th>Duration</th>
            <th>Pace</th>
            <th>Vs 4:56 Target</th>
            <th>Avg HR</th>
            <th>Cadence</th>
            <th>Power</th>
            <th>Training Effect</th>
          </tr>
        </thead>
        <tbody id="activityTableBody"></tbody>
      </table>
    </div>
  </main>

  <footer>
    Garmini • Built for Sub-3:28 Marathoners • Garmin Personal API
  </footer>

  <script>
    const D = {data_json};
    let currentFilter = 'all';
    let currentSearchTerm = '';
    let currentThemeMode = localStorage.getItem('garmini_theme_mode') || 'dark';

    let chartWeeklyVolume = null;
    let chartRhrHrv = null;
    let chartSleep = null;

    // Theme Engine (Dark / Light)
    function applyTheme(mode) {{
      currentThemeMode = (mode === 'light') ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', currentThemeMode);
      localStorage.setItem('garmini_theme_mode', currentThemeMode);

      const iconEl = document.getElementById('themeToggleIcon');
      const textEl = document.getElementById('themeToggleText');
      const btnEl = document.getElementById('themeToggleBtn');

      if (currentThemeMode === 'light') {{
        if (iconEl) iconEl.innerText = '🌙';
        if (textEl) textEl.innerText = 'Dark';
        if (btnEl) btnEl.setAttribute('aria-label', 'Switch to dark theme');
      }} else {{
        if (iconEl) iconEl.innerText = '☀️';
        if (textEl) textEl.innerText = 'Light';
        if (btnEl) btnEl.setAttribute('aria-label', 'Switch to light theme');
      }}

      // Sync meta theme-color for browser titlebar
      const meta = document.getElementById('metaThemeColor');
      if (meta) {{
        meta.setAttribute('content', currentThemeMode === 'light' ? '#f8fafc' : '#030712');
      }}

      // Update Chart.js palette dynamically
      updateChartsTheme(currentThemeMode);
    }}

    function toggleTheme() {{
      applyTheme(currentThemeMode === 'dark' ? 'light' : 'dark');
    }}

    // 1. Interactive Pacing Strategy Switcher
    function setPacingStrategy(stratKey) {{
      const strat = D.pacing_strategies[stratKey] || D.pacing_strategies.negative;
      
      document.querySelectorAll('.pace-strat-btn').forEach(b => b.classList.remove('active'));
      const activeBtn = document.getElementById(stratKey === 'negative' ? 'btnPaceNeg' : 'btnPaceEven');
      if (activeBtn) activeBtn.classList.add('active');

      document.getElementById('paceStrategySubtitle').innerText = strat.subtitle;
      document.getElementById('paceHalvesBadge').innerHTML = `
        <span style="background: var(--card-bg-subtle); padding: 5px 12px; border-radius: 6px; border: 1px solid var(--card-border);">
          1st Half: <strong style="color: var(--accent-primary);">${{strat.first_half}}</strong>
        </span>
        <span style="background: var(--card-bg-subtle); padding: 5px 12px; border-radius: 6px; border: 1px solid var(--card-border);">
          2nd Half: <strong style="color: var(--accent-cyan);">${{strat.second_half}}</strong>
        </span>
      `;

      const tbody = document.getElementById('pacingTableBody');
      tbody.innerHTML = strat.stages.map(s => `
        <tr>
          <td style="font-weight: 700; color: var(--text-main);">${{s.stage}}</td>
          <td style="color: var(--text-muted);">${{s.phase}}</td>
          <td style="color: var(--accent-primary); font-weight: 700;">${{s.pace}}</td>
          <td style="font-weight: 600;">${{s.time}}</td>
          <td style="color: var(--text-dim); font-size: 0.76rem;">${{s.notes}}</td>
        </tr>
      `).join('');
    }}

    setPacingStrategy('negative');

    // 2. PWA Detection & Install Bar
    const pwaBanner = document.getElementById('pwaInstallBanner');

    function isInstalledOrStandalone() {{
      if (
        window.matchMedia('(display-mode: standalone)').matches ||
        window.matchMedia('(display-mode: fullscreen)').matches ||
        window.matchMedia('(display-mode: minimal-ui)').matches ||
        window.navigator.standalone === true ||
        document.referrer.includes('android-app://') ||
        window.location.search.includes('mode=pwa') ||
        localStorage.getItem('garmini_pwa_installed') === 'true' ||
        localStorage.getItem('garmini_pwa_dismissed') === 'true'
      ) {{
        return true;
      }}
      return false;
    }}

    function checkPWA() {{
      if (isInstalledOrStandalone()) {{
        if (pwaBanner) pwaBanner.remove();
        return;
      }}
      if (window.__deferredPrompt && pwaBanner) {{
        pwaBanner.style.display = 'flex';
      }}
    }}

    window.addEventListener('pwa-prompt-ready', checkPWA);
    window.addEventListener('beforeinstallprompt', checkPWA);
    window.addEventListener('DOMContentLoaded', checkPWA);

    function handlePWADismiss() {{
      localStorage.setItem('garmini_pwa_installed', 'true');
      localStorage.setItem('garmini_pwa_dismissed', 'true');
      if (pwaBanner) pwaBanner.remove();
    }}

    async function handlePWAInstall() {{
      const prompt = window.__deferredPrompt;
      if (prompt) {{
        try {{
          prompt.prompt();
          prompt.userChoice?.then(c => {{
            if (c?.outcome === 'accepted') {{
              localStorage.setItem('garmini_pwa_installed', 'true');
              if (pwaBanner) pwaBanner.remove();
            }}
          }});
        }} catch(e) {{}}
      }} else {{
        localStorage.setItem('garmini_pwa_installed', 'true');
        if (pwaBanner) pwaBanner.remove();
      }}
    }}

    // Render Long Runs
    const lrList = document.getElementById('longRunsList');
    if (D.long_runs && D.long_runs.length > 0) {{
      lrList.innerHTML = D.long_runs.map(r => {{
        const diff = r.pace_diff_s;
        const diffText = diff > 0 ? `+${{diff}}s vs 4:56` : `${{diff}}s vs 4:56`;
        const diffColor = diff <= 0 ? 'var(--accent-primary)' : 'var(--text-muted)';
        return `
          <div class="long-run-item">
            <div>
              <div class="lr-date">${{r.date}} • ${{r.name}}</div>
              <div class="lr-dist">${{r.dist_km.toFixed(2)}} km</div>
            </div>
            <div class="lr-metrics">
              <div style="font-weight: 700; color: var(--text-main);">${{r.pace}} /km</div>
              <div style="color: ${{diffColor}};">${{diffText}} • ${{r.avg_hr ? r.avg_hr + ' bpm' : ''}}</div>
            </div>
          </div>
        `;
      }}).join('');
    }}

    // Render Week Day Schedule with Today Indicator
    const cwContainer = document.getElementById('currentWeekContainer');
    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const curDays = D.current_week.days || {{}};
    const todayIsoDay = (new Date().getDay() === 0 ? 7 : new Date().getDay());
    let cwHtml = '';
    for (let d = 1; d <= 7; d++) {{
      const acts = curDays[d] || [];
      const runAct = acts.find(a => a.sport === 'running');
      const dist = runAct ? runAct.dist_km : 0;
      const activeClass = dist > 0 ? 'active-day' : '';
      const isToday = (d === todayIsoDay) ? 'today' : '';
      cwHtml += `
        <div class="day-chip ${{activeClass}} ${{isToday}}">
          <div class="day-name">${{dayNames[d-1]}}${{(d === todayIsoDay) ? ' •' : ''}}</div>
          <div class="day-dist">${{dist > 0 ? dist.toFixed(1) : '-'}}</div>
          <div class="day-type">${{dist > 0 ? 'Run' : 'Rest'}}</div>
        </div>
      `;
    }}
    cwContainer.innerHTML = cwHtml;

    // Filter & Search Activity Table
    function renderActivityTable() {{
      const tbody = document.getElementById('activityTableBody');
      const all = D.recent_activities || [];
      
      const filtered = all.filter(a => {{
        if (currentFilter === 'long' && a.dist_km < 15.0) return false;
        if (currentFilter === 'fast' && a.pace_diff_s > 0) return false;
        if (currentFilter === 'easy' && (a.z1_m + a.z2_m) < (a.z3_m + a.z4_m + a.z5_m)) return false;

        if (currentSearchTerm) {{
          const term = currentSearchTerm.toLowerCase();
          const matchName = (a.name || '').toLowerCase().includes(term);
          const matchDate = (a.date || '').toLowerCase().includes(term);
          const matchTe = (a.te_label || '').toLowerCase().includes(term);
          if (!matchName && !matchDate && !matchTe) return false;
        }}
        return true;
      }});

      if (filtered.length === 0) {{
        tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: var(--text-dim); padding: 24px;">No matching activities found.</td></tr>`;
        return;
      }}

      tbody.innerHTML = filtered.map(a => {{
        const diff = a.pace_diff_s;
        const diffText = diff > 0 ? `+${{diff}}s` : `${{diff}}s`;
        const diffColor = diff <= 0 ? 'var(--accent-primary)' : 'var(--text-dim)';
        return `
          <tr>
            <td>${{a.date}}</td>
            <td style="color: var(--text-main); font-weight: 600;">${{a.name}}</td>
            <td style="color: var(--accent-primary); font-weight: 700;">${{a.dist_km.toFixed(2)}} km</td>
            <td>${{a.dur_fmt}}</td>
            <td>${{a.pace}}</td>
            <td style="color: ${{diffColor}};">${{diffText}}</td>
            <td>${{a.avg_hr ? a.avg_hr + ' bpm' : '--'}}</td>
            <td>${{a.cadence ? a.cadence + ' spm' : '--'}}</td>
            <td>${{a.power ? a.power + ' W' : '--'}}</td>
            <td><span class="te-badge">${{a.te_label}}</span></td>
          </tr>
        `;
      }}).join('');
    }}

    function filterActivities(category) {{
      currentFilter = category;
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      const activeId = {{ all: 'filterAll', long: 'filterLong', fast: 'filterFast', easy: 'filterEasy' }}[category] || 'filterAll';
      const el = document.getElementById(activeId);
      if (el) el.classList.add('active');
      renderActivityTable();
    }}

    function onSearchActivities(term) {{
      currentSearchTerm = term.trim();
      renderActivityTable();
    }}

    renderActivityTable();

    // Chart.js Setup & Dynamic Theme Updates
    function getChartThemeTokens(mode) {{
      const isLight = (mode === 'light');
      return {{
        text: isLight ? '#475569' : '#93c5fd',
        grid: isLight ? 'rgba(0, 0, 0, 0.07)' : 'rgba(255, 255, 255, 0.06)',
        primary: isLight ? '#0284c7' : '#38bdf8',
        secondary: isLight ? '#0d9488' : '#2dd4bf',
        rhr: isLight ? '#e11d48' : '#fb7185',
        sleep: isLight ? '#2563eb' : '#60a5fa'
      }};
    }}

    function initCharts(mode) {{
      const tokens = getChartThemeTokens(mode);

      Chart.defaults.font.family = 'ui-monospace, "SF Mono", "Cascadia Code", "Roboto Mono", Consolas, monospace';
      Chart.defaults.color = tokens.text;
      Chart.defaults.borderColor = tokens.grid;

      // 1. Weekly Volume
      const wCtx = document.getElementById('weeklyVolumeChart').getContext('2d');
      if (chartWeeklyVolume) chartWeeklyVolume.destroy();
      chartWeeklyVolume = new Chart(wCtx, {{
        type: 'bar',
        data: {{
          labels: D.recent_26_weeks.map(w => w.label),
          datasets: [
            {{
              label: 'Weekly Mileage (km)',
              data: D.recent_26_weeks.map(w => w.running_km),
              backgroundColor: tokens.primary + 'c0',
              borderColor: tokens.primary,
              borderWidth: 1,
              borderRadius: 4,
              order: 2
            }},
            {{
              label: 'Longest Run (km)',
              data: D.recent_26_weeks.map(w => w.long_run_km),
              type: 'line',
              borderColor: tokens.secondary,
              pointBackgroundColor: tokens.secondary,
              pointRadius: 3,
              borderWidth: 2,
              tension: 0.2,
              order: 1
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            y: {{ beginAtZero: true, grid: {{ color: tokens.grid }} }},
            x: {{ grid: {{ display: false }} }}
          }}
        }}
      }});

      // 2. RHR & HRV
      const rCtx = document.getElementById('rhrHrvChart').getContext('2d');
      if (chartRhrHrv) chartRhrHrv.destroy();
      chartRhrHrv = new Chart(rCtx, {{
        type: 'line',
        data: {{
          labels: D.timeline_90d.map(t => t.label),
          datasets: [
            {{
              label: 'Resting HR (bpm)',
              data: D.timeline_90d.map(t => t.rhr),
              borderColor: tokens.rhr,
              yAxisID: 'yRhr',
              borderWidth: 2,
              pointRadius: 1,
              tension: 0.25,
              spanGaps: true
            }},
            {{
              label: 'Nightly HRV (ms)',
              data: D.timeline_90d.map(t => t.hrv),
              borderColor: tokens.secondary,
              yAxisID: 'yHrv',
              borderWidth: 2,
              pointRadius: 1,
              tension: 0.25,
              spanGaps: true
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            yRhr: {{ type: 'linear', position: 'left', suggestedMin: 45, suggestedMax: 65, grid: {{ color: tokens.grid }} }},
            yHrv: {{ type: 'linear', position: 'right', suggestedMin: 30, suggestedMax: 70, grid: {{ display: false }} }},
            x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 10 }} }}
          }}
        }}
      }});

      // 3. Sleep
      const sCtx = document.getElementById('sleepChart').getContext('2d');
      if (chartSleep) chartSleep.destroy();
      chartSleep = new Chart(sCtx, {{
        type: 'bar',
        data: {{
          labels: D.timeline_90d.map(t => t.label),
          datasets: [
            {{
              type: 'line',
              label: 'Sleep Score',
              data: D.timeline_90d.map(t => t.sleep_score),
              borderColor: tokens.sleep,
              yAxisID: 'yScore',
              borderWidth: 2,
              pointRadius: 1.5,
              tension: 0.2,
              spanGaps: true
            }},
            {{
              type: 'bar',
              label: 'Hours',
              data: D.timeline_90d.map(t => t.sleep_hrs),
              backgroundColor: tokens.primary + '55',
              yAxisID: 'yHrs',
              borderRadius: 3
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            yScore: {{ type: 'linear', position: 'right', suggestedMin: 50, suggestedMax: 100, grid: {{ display: false }} }},
            yHrs: {{ type: 'linear', position: 'left', suggestedMin: 4, suggestedMax: 10, grid: {{ color: tokens.grid }} }},
            x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 10 }} }}
          }}
        }}
      }});
    }}

    function updateChartsTheme(mode) {{
      initCharts(mode);
    }}

    // Initialize Theme & Charts
    applyTheme(currentThemeMode);
  </script>
</body>
</html>
"""
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    site_index = SITE_DIR / "index.html"
    if site_index.parent.exists():
        with open(site_index, "w", encoding="utf-8") as f:
            f.write(html)
    print(f"-> Successfully generated {OUTPUT_HTML} and site/index.html ({len(html)} bytes)")

def main():
    print("========================================")
    print(" Garmini - Advanced Marathon Builder")
    print("========================================")
    data = process_data()
    generate_pwa_files()
    generate_dashboard_html(data)
    print("Done! Standalone dashboard & PWA ready.")

if __name__ == "__main__":
    main()
