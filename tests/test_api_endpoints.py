import pytest
from httpx import AsyncClient, ASGITransport
from apps.api.main import app
from packages.core.database import init_db

@pytest.mark.asyncio
async def test_api_health_and_dashboard():
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health Endpoint
        res_health = await client.get("/api/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "healthy"

        # 2. Dashboard Root HTML
        res_root = await client.get("/")
        assert res_root.status_code == 200
        assert "Placement Intelligence Hub" in res_root.text

        # 3. Stats
        res_stats = await client.get("/api/stats")
        assert res_stats.status_code == 200
        stats = res_stats.json()
        assert "total_discovered" in stats
        assert "ethara_target_status" in stats

        # 4. List Opportunities
        res_opps = await client.get("/api/opportunities")
        assert res_opps.status_code == 200
        opps = res_opps.json()
        assert isinstance(opps, list)

        # 5. Pending Approvals
        res_pending = await client.get("/api/approvals/pending")
        assert res_pending.status_code == 200
        pending = res_pending.json()
        assert isinstance(pending, list)

        if pending:
            opp_id = pending[0]["id"]
            # Formats Check
            res_formats = await client.get(f"/api/opportunities/{opp_id}/formats")
            assert res_formats.status_code == 200
            formats = res_formats.json()
            assert "whatsapp_card" in formats
            assert "telegram_markdown" in formats

            # Action Check (Approve)
            res_action = await client.post(
                f"/api/approvals/{opp_id}/action",
                json={"action": "approve", "reviewed_by": "Shivam Lead", "publish_telegram": False}
            )
            assert res_action.status_code == 200
            assert res_action.json()["status"] == "success"
            assert res_action.json()["new_status"] in ("approved", "published")
