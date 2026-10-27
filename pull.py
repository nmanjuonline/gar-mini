"""
Garmini - Data Puller for Garmin Personal API
Fetches activities, daily health summaries, sleep, HRV, weight, and biometric zones.
Only uses standard Python libraries.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Safe stdout for Windows console (handles emojis gracefully)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
ENV_FILE = BASE_DIR / ".env.local"
TOKEN_FILE = DATA_DIR / "token.json"

BASE_API_URL = "https://personal.connectapi.garmin.com"
TOKEN_URL = f"{BASE_API_URL}/personalapitoken-service/personal-api/personal-api-key/token"

def get_api_key():
    # 1. Check environment variable (CI/CD, GitHub Actions, Docker)
    env_key = os.environ.get("GARMIN_PERSONAL_API_KEY", "").strip().strip('"').strip("'")
    if env_key:
        return env_key

    # 2. Check local .env.local file
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GARMIN_PERSONAL_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if key:
                        return key

    raise ValueError(
        "GARMIN_PERSONAL_API_KEY is missing or empty.\n"
        "- For GitHub Actions: Add GARMIN_PERSONAL_API_KEY to Repository Secrets at:\n"
        "  https://github.com/nmanjuonline/gar-mini/settings/secrets/actions\n"
        "- For local runs: Add GARMIN_PERSONAL_API_KEY=<your-key> to .env.local"
    )

def get_access_token():
    # Check if cached token is still valid (< 20 hours old)
    if TOKEN_FILE.exists():
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                created_at = data.get("created_at", 0)
                token = data.get("token", "")
                if token and (time.time() - created_at < 20 * 3600):
                    return token
        except Exception:
            pass

    # Request new token
    api_key = get_api_key()
    req = urllib.request.Request(TOKEN_URL, method="POST")
    req.add_header("Authorization", f"ApiKey {api_key}")
    req.add_header("User-Agent", "Garmini/1.0")

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            token = resp.read().decode("utf-8").strip()
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                json.dump({"token": token, "created_at": time.time()}, f)
            return token
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Failed to authenticate with Garmin API (HTTP {e.code}): {err_msg}")

def api_get(endpoint, token, max_retries=3):
    url = f"{BASE_API_URL}{endpoint}" if endpoint.startswith("/") else endpoint
    for attempt in range(max_retries):
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("User-Agent", "Garmini/1.0")
        try:
            time.sleep(0.2)  # courteous pause
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                if not raw.strip():
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503) and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"    [!] HTTP {e.code}. Waiting {wait_time}s to retry...", flush=True)
                time.sleep(wait_time)
                continue
            elif e.code == 404:
                return None
            else:
                raise
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            raise

def load_json_file(filename, default):
    path = DATA_DIR / filename
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json_file(filename, data):
    path = DATA_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_activities(token, cutoff_date=None):
    print("-> Fetching activities...", flush=True)
    existing_activities = load_json_file("activities.json", [])
    existing_by_id = {act["activityId"]: act for act in existing_activities if "activityId" in act}
    
    new_activities = []
    start = 0
    limit = 20
    stop_paging = False

    while not stop_paging:
        endpoint = f"/activitylist-service/activities/search/activities?start={start}&limit={limit}"
        data = api_get(endpoint, token)
        if not data or not isinstance(data, list) or len(data) == 0:
            break

        for act in data:
            act_id = act.get("activityId")
            start_time = act.get("startTimeLocal", "")
            
            # If cutoff_date is set and activity is older, stop
            if cutoff_date and start_time[:10] < cutoff_date:
                stop_paging = True
                break

            # If re-running and we encounter an already known activity, we can merge and update
            if act_id in existing_by_id:
                # Update existing record in place
                existing_by_id[act_id] = act
            else:
                existing_by_id[act_id] = act
                new_activities.append(act)

        print(f"   Checked activities {start} to {start + len(data)} (total stored: {len(existing_by_id)})", flush=True)

        if len(data) < limit:
            break
        start += limit

    all_sorted = sorted(existing_by_id.values(), key=lambda x: x.get("startTimeLocal", ""), reverse=True)
    save_json_file("activities.json", all_sorted)
    print(f"   Saved {len(all_sorted)} activities ({len(new_activities)} new).", flush=True)
    return all_sorted

def fetch_daily_summaries_range(token, start_date_str, end_date_str):
    """Fetch with auto-halving if HTTP 500 (>256KB payload limit)"""
    endpoint = f"/usersummary-service/v2/dailysummaries?startDate={start_date_str}&endDate={end_date_str}"
    try:
        res = api_get(endpoint, token)
        if res and isinstance(res, dict) and "data" in res:
            return res["data"]
        return []
    except urllib.error.HTTPError as e:
        if e.code == 500:
            d1 = datetime.strptime(start_date_str, "%Y-%m-%d")
            d2 = datetime.strptime(end_date_str, "%Y-%m-%d")
            delta = (d2 - d1).days
            if delta <= 1:
                return []
            mid = d1 + timedelta(days=delta // 2)
            mid_str = mid.strftime("%Y-%m-%d")
            mid_next_str = (mid + timedelta(days=1)).strftime("%Y-%m-%d")
            print(f"   [!] Splitting daily summaries range {start_date_str}..{end_date_str} due to payload size limit...", flush=True)
            left = fetch_daily_summaries_range(token, start_date_str, mid_str)
            right = fetch_daily_summaries_range(token, mid_next_str, end_date_str)
            return left + right
        raise

def fetch_daily_summaries(token, start_dt, end_dt):
    print("-> Fetching daily wellness summaries...", flush=True)
    existing_list = load_json_file("daily_summaries.json", [])
    existing_by_date = {d.get("calendarDate"): d for d in existing_list if "calendarDate" in d}

    # Chunk by 60 days
    curr = start_dt
    while curr <= end_dt:
        chunk_end = min(curr + timedelta(days=59), end_dt)
        s_str = curr.strftime("%Y-%m-%d")
        e_str = chunk_end.strftime("%Y-%m-%d")
        
        # Check if already fully in existing and chunk_end is not today
        today_str = datetime.now().strftime("%Y-%m-%d")
        missing = False
        check_date = curr
        while check_date <= chunk_end:
            c_str = check_date.strftime("%Y-%m-%d")
            if c_str not in existing_by_date or c_str == today_str:
                missing = True
                break
            check_date += timedelta(days=1)

        if missing:
            print(f"   Fetching daily summaries {s_str} to {e_str}...", flush=True)
            try:
                items = fetch_daily_summaries_range(token, s_str, e_str)
                for item in items:
                    c_date = item.get("calendarDate")
                    if c_date:
                        existing_by_date[c_date] = item
            except Exception as e:
                print(f"   [!] Warning: Error fetching daily summaries for {s_str}..{e_str}: {e}")

        curr = chunk_end + timedelta(days=1)

    all_sorted = sorted(existing_by_date.values(), key=lambda x: str(x.get("calendarDate") or ""))
    save_json_file("daily_summaries.json", all_sorted)
    print(f"   Saved {len(all_sorted)} daily summary records.", flush=True)
    return all_sorted

def fetch_sleep_summaries(token, start_dt, end_dt):
    print("-> Fetching sleep summaries (31-day windows)...", flush=True)
    existing_list = load_json_file("sleep.json", [])
    existing_by_date = {d.get("calendarDate"): d for d in existing_list if "calendarDate" in d}

    curr = start_dt
    today_str = datetime.now().strftime("%Y-%m-%d")

    while curr <= end_dt:
        chunk_end = min(curr + timedelta(days=29), end_dt)
        s_str = curr.strftime("%Y-%m-%d")
        e_str = chunk_end.strftime("%Y-%m-%d")

        missing = False
        check_date = curr
        while check_date <= chunk_end:
            c_str = check_date.strftime("%Y-%m-%d")
            if c_str not in existing_by_date or c_str == today_str:
                missing = True
                break
            check_date += timedelta(days=1)

        if missing:
            endpoint = f"/sleep-service/sleep/dailySleepSummariesByDate?startDate={s_str}&endDate={e_str}"
            try:
                data = api_get(endpoint, token)
                if data and isinstance(data, list):
                    for item in data:
                        c_date = item.get("calendarDate")
                        if c_date:
                            existing_by_date[c_date] = item
            except Exception as e:
                print(f"   [!] Sleep fetch error for {s_str}..{e_str}: {e}")

        curr = chunk_end + timedelta(days=1)

    all_sorted = sorted(existing_by_date.values(), key=lambda x: str(x.get("calendarDate") or ""))
    save_json_file("sleep.json", all_sorted)
    print(f"   Saved {len(all_sorted)} sleep records.", flush=True)
    return all_sorted

def fetch_hrv_summaries(token, start_dt, end_dt):
    print("-> Fetching HRV summaries (up to 365-day windows)...", flush=True)
    existing_list = load_json_file("hrv.json", [])
    existing_by_date = {d.get("calendarDate"): d for d in existing_list if "calendarDate" in d}

    curr = start_dt
    while curr <= end_dt:
        chunk_end = min(curr + timedelta(days=360), end_dt)
        s_str = curr.strftime("%Y-%m-%d")
        e_str = chunk_end.strftime("%Y-%m-%d")

        endpoint = f"/hrv-service/hrv/daily/{s_str}/{e_str}"
        try:
            data = api_get(endpoint, token)
            if data and isinstance(data, dict):
                summaries = data.get("hrvSummaries", [])
                for item in summaries:
                    c_date = item.get("calendarDate")
                    if c_date:
                        existing_by_date[c_date] = item
        except Exception as e:
            print(f"   [!] HRV fetch error for {s_str}..{e_str}: {e}")

        curr = chunk_end + timedelta(days=1)

    all_sorted = sorted(existing_by_date.values(), key=lambda x: str(x.get("calendarDate") or ""))
    save_json_file("hrv.json", all_sorted)
    print(f"   Saved {len(all_sorted)} HRV records.", flush=True)
    return all_sorted

def fetch_weight(token, start_dt, end_dt):
    print("-> Fetching weight history...", flush=True)
    existing_list = load_json_file("weight.json", [])
    existing_by_date = {d.get("date"): d for d in existing_list if "date" in d}

    s_str = start_dt.strftime("%Y-%m-%d")
    e_str = end_dt.strftime("%Y-%m-%d")
    endpoint = f"/weight-service/weight/range/{s_str}/{e_str}"
    try:
        data = api_get(endpoint, token)
        if data and isinstance(data, dict):
            summaries = data.get("dailyWeightSummaries", [])
            for item in summaries:
                # date can be date or calendarDate
                d = item.get("summaryDate") or item.get("calendarDate") or item.get("date")
                if d:
                    existing_by_date[d] = item
    except Exception as e:
        print(f"   [!] Weight fetch note: {e}")

    all_sorted = sorted(existing_by_date.values(), key=lambda x: str(x.get("summaryDate") or x.get("date") or ""))
    save_json_file("weight.json", all_sorted)
    print(f"   Saved {len(all_sorted)} weight records.", flush=True)
    return all_sorted

def fetch_biometrics_and_zones(token):
    print("-> Fetching HR zones & biometrics...", flush=True)
    endpoint = "/biometric-service/heartRateZones/v2"
    try:
        data = api_get(endpoint, token)
        if data:
            save_json_file("hr_zones.json", data)
            print("   Saved heart rate zones.", flush=True)
    except Exception as e:
        print(f"   [!] HR zones note: {e}")

    today_str = datetime.now().strftime("%Y-%m-%d")
    endpoint_fa = f"/fitnessage-service/fitnessage/v2/{today_str}"
    try:
        data_fa = api_get(endpoint_fa, token)
        if data_fa:
            save_json_file("fitness_age.json", data_fa)
            print("   Saved fitness age.", flush=True)
    except Exception as e:
        pass

def main():
    full_history = "--full" in sys.argv
    print("========================================")
    print(" Garmini - Garmin Personal API Sync")
    print(f" Mode: {'Full History' if full_history else 'Last 12 Months'}")
    print("========================================")

    now = datetime.now()
    if full_history:
        # Default back 5 years for full history
        start_dt = now - timedelta(days=365 * 5)
        cutoff_date = None
    else:
        start_dt = now - timedelta(days=365)
        cutoff_date = start_dt.strftime("%Y-%m-%d")

    token = get_access_token()
    print("[1/6] Token validated.")

    # 1. Activities
    activities = fetch_activities(token, cutoff_date=cutoff_date)

    # 2. Daily summaries
    daily = fetch_daily_summaries(token, start_dt, now)

    # 3. Sleep
    sleep = fetch_sleep_summaries(token, start_dt, now)

    # 4. HRV
    hrv = fetch_hrv_summaries(token, start_dt, now)

    # 5. Weight
    weight = fetch_weight(token, start_dt, now)

    # 6. Biometrics & Zones
    fetch_biometrics_and_zones(token)

    # Summary
    earliest_date = "N/A"
    latest_date = "N/A"
    all_dates = []
    if activities:
        all_dates.extend([a.get("startTimeLocal", "")[:10] for a in activities if a.get("startTimeLocal")])
    if daily:
        all_dates.extend([d.get("calendarDate") for d in daily if d.get("calendarDate")])
    if all_dates:
        earliest_date = min(all_dates)
        latest_date = max(all_dates)

    meta = {
        "last_sync": now.isoformat(),
        "total_activities": len(activities),
        "total_daily_summaries": len(daily),
        "total_sleep_records": len(sleep),
        "total_hrv_records": len(hrv),
        "total_weight_records": len(weight),
        "date_range": f"{earliest_date} to {latest_date}"
    }
    save_json_file("meta.json", meta)

    print("\n----------------------------------------")
    print("Sync Complete!")
    print(f"Total Activities: {meta['total_activities']}")
    print(f"Daily Summaries:  {meta['total_daily_summaries']}")
    print(f"Sleep Records:    {meta['total_sleep_records']}")
    print(f"HRV Records:      {meta['total_hrv_records']}")
    print(f"Date Range:       {meta['date_range']}")
    print("----------------------------------------")

if __name__ == "__main__":
    main()
