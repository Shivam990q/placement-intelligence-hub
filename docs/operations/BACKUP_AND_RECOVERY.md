# 💾 Backup, Disaster Recovery & Data Preservation Procedures

## 1. Backup Strategy Overview

The **Placement Intelligence Hub** utilizes a zero-cost, multi-tier data preservation model:
1. **Tier 1 (Local Atomic Snapshot):** Daily point-in-time snapshot of the primary SQLite database file.
2. **Tier 2 (Cloudflare D1 SQL Dump):** Scheduled export of Cloudflare D1 edge database tables to SQL dump.
3. **Tier 3 (Git Version Control):** Canonical source configuration, database migrations, and scraper rules versioned in Git.

---

## 2. Local SQLite Backup Procedures

### 2.1 Live Atomic Backup via Python
Because SQLite supports atomic VACUUM INTO and online backup APIs, backups can be taken without taking the server offline:

```python
import sqlite3
import shutil
from datetime import datetime

def backup_sqlite():
    source_db = "placement_hub.db"
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/placement_hub_{timestamp}.db"
    
    # Atomic online backup API
    with sqlite3.connect(source_db) as src:
        with sqlite3.connect(backup_file) as dst:
            src.backup(dst)
            
    print(f"Backup successfully written to {backup_file}")

if __name__ == "__main__":
    backup_sqlite()
```

### 2.2 CLI Snapshot Command (PowerShell / Bash)
```powershell
# Windows PowerShell
Copy-Item "placement_hub.db" "backups/placement_hub_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
```

```bash
# Linux / macOS
cp placement_hub.db "backups/placement_hub_$(date +%Y%m%d_%H%M%S).db"
```

---

## 3. Cloudflare D1 Cloud Backup & Restore

### 3.1 Exporting Production D1 Database
To export the complete schema and all records from Cloudflare D1 to a local SQL file:
```bash
npx wrangler d1 export placement-hub-db --remote --output=backups/d1_backup_$(date +%Y%m%d).sql
```

### 3.2 Restoring D1 from an Exported SQL File
To restore the remote database from a verified backup:
```bash
npx wrangler d1 execute placement-hub-db --remote --file=backups/d1_backup_20261107.sql
```

---

## 4. Disaster Recovery Scenarios & Playbooks

### Scenario A: Local SQLite File Corruption
1. Stop running processes (`python run.py` or `docker compose down`).
2. Move corrupted file: `Rename-Item placement_hub.db placement_hub_corrupted.db`.
3. Locate newest valid backup in `backups/`.
4. Restore backup: `Copy-Item backups/placement_hub_LATEST.db placement_hub.db`.
5. Run test suite: `python -m pytest tests/`
6. Restart platform: `python run.py`.

### Scenario B: Cloudflare Free Worker Request Exhaustion (100k requests hit)
1. Edge worker returns HTTP 429 to dynamic non-cached requests.
2. In-memory and browser localStorage caches serve cached opportunities to students.
3. Admin uses local instance (`http://localhost:8000`) or Telegram Long-Poll Bot, which continues operating independently with 0 downtime.
4. Quota automatically resets at 00:00 UTC.
