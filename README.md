# 🎓 Placement Intelligence Hub (College Placement Radar & Watchdog)

> **Autonomous multi-source placement radar, career watchdog, and distribution engine for Batch 2026/2027.**
> Zero-license cost foundation with instant native execution, Telegram channel/forum distribution, and WhatsApp 1-click formatted drops.

---

## 🎯 1. Target Priorities & Real-World Sources

| Target / Channel | Focus & Role | Action / Workflow |
| :--- | :--- | :--- |
| **Ethara.AI HRMS** | **LLM Post-Training – GenOPS** (₹6 LPA, Pure English Only) | Continuous watchdog on `hrms.ethara.ai/careers`. Alerts immediately upon opening! |
| **Amazon Jobs** | **SDE Intern / University Talent Acquisition** (May 2027 / 2026) | Tracks official `amazon.jobs` student program feeds. |
| **WhatsApp Communities** | *2027 Batch Placement 1*, *Jobs & Internships (109k)*, *CampusMonk* | Parses incoming posts (Hevo, TCS NQT, Infosys), strips ads, formats clean cards. |
| **Telegram Network** | Dedicated **`Placements`** Channel & Discussion Supergroup with Topics | Official bot publishes approved opportunities with `message_thread_id` routing. |

---

## 🏗️ 2. System Architecture

```
  [Information Sources]
  • Ethara.AI HRMS Careers Watchdog
  • Amazon University SDE Portal
  • Official ATS Boards (Greenhouse, Lever, Ashby)
  • Community Messages (Hevo, TCS NQT, Infosys)
             │
             ▼
  [Intelligence & Processing Core]
  • Multi-Stage Deduplication (Canonical URL Hash, Title/Company Fuzzy match)
  • Batch & Degree Analyzer (Batch 2026/2027, CS/IT, SDE/GenOPS alignment)
  • Source Verifier (Official ATS domain validation & HTTP status probe)
  • Standardized Content Formatter (Telegram Markdown & WhatsApp Text)
             │
             ▼
  [Admin Moderation & Approval Queue]
  • Interactive Web Dashboard (http://localhost:8000)
  • Telegram Bot Inline Review Cards ([Approve] [Reject] [Copy WhatsApp])
             │
      ┌──────┴─────────────────────────┐
      ▼                                ▼
  [Telegram Network]             [WhatsApp Group]
  • Broadcast Channel            • 1-Click Clipboard Ready Card
  • Forum Supergroup Topics      • Safe from personal number bans!
```

---

## 🚀 3. Quick Start (Run in 5 Seconds)

### Native Local Start (Zero Setup Needed)
```powershell
cd C:\Users\Rose\.gemini\antigravity\scratch\placement-intelligence-hub
python run.py
```
Open **http://localhost:8000** in your browser to access the live Web Admin Dashboard!

### Or with Docker Compose:
```bash
docker compose up -d
```

---

## 📡 4. Telegram Bot Setup (@BotFather)

1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, name your bot (e.g., `CampusPlacementRadarBot`), and copy the **API Token**.
3. Add the token to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN="your_bot_token_here"
   TELEGRAM_CHANNEL_ID="@Placements"
   ```
4. In your **`Placements`** channel, add your bot as an **Administrator** with "Post Messages" permission.
5. Run the bot listener:
   ```powershell
   python -m apps.telegram_bot.bot
   ```

### Bot Commands:
- `/status`: Live telemetry, total jobs discovered, active watchdogs, Ethara target status.
- `/pending`: Browse pending opportunities with inline `[Approve]` and `[Reject]` buttons.
- `/submit <url or message>`: Paste any forwarded placement message to parse and queue it.
- `/scan`: Trigger an instant career portal acquisition cycle.

---

## 📋 5. WhatsApp Safe Distribution (Zero-Ban Architecture)

Instead of using risky third-party WhatsApp web bots that risk your personal phone number getting banned:
1. When an opportunity is approved, click **"Copy for WhatsApp"** on the dashboard or Telegram bot.
2. The card is instantly formatted with standard bullet points, emojis, bold tags, and direct official apply links.
3. Paste directly into your college group: **`2027 Batch Placement 1`** or **`Group of Placements`**!

---

## 🧪 6. Automated Verification Tests

Run the full automated test suite anytime:
```powershell
python -m pytest tests/
```
All unit tests for deduplication, eligibility parsing, format rendering, and end-to-end acquisition cycles are 100% automated and verified.
