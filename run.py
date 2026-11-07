import sys
import os
import uvicorn

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def main():
    print("=" * 65)
    print("🎓 PLACEMENT INTELLIGENCE HUB — RADAR & WATCHDOG ENGINE")
    print("=" * 65)
    print("📡 Priority Watchdog: Ethara.AI (LLM GenOPS 6 LPA) & Amazon SDE")
    print("🚀 Web Admin Dashboard: http://localhost:8000")
    print("📚 Interactive Swagger API: http://localhost:8000/docs")
    print("🤖 Telegram Bot: apps/telegram_bot/bot.py")
    print("=" * 65)

    uvicorn.run(
        "apps.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()

