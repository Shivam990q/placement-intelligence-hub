"""Zero-cost Quota and Budget Defense Manager.

Enforces strict fail-closed rate-limiting and usage tracking across all
free-tier cloud infrastructure providers (Cloudflare, GitHub Actions, Workers AI).
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Free-tier hard daily and monthly quotas
DEFAULT_LIMITS: Dict[str, int] = {
    "cf_worker_requests_daily": 100_000,       # Cloudflare Workers: 100,000 req/day
    "cf_d1_reads_daily": 5_000_000,            # Cloudflare D1: 5,000,000 reads/day
    "cf_d1_writes_daily": 100_000,             # Cloudflare D1: 100,000 writes/day
    "cf_ai_neurons_daily": 10_000,             # Cloudflare Workers AI: 10,000 neurons/day
    "gh_actions_minutes_monthly": 2_000,       # GitHub Actions: 2,000 min/month free
    "telegram_messages_minute": 1_800,         # Safe Telegram ceiling (30 msg/sec * 60)
}

# Thresholds for defense actions
WARNING_THRESHOLD = 0.80   # 80% quota consumption -> Log alert
CRITICAL_THRESHOLD = 0.95  # 95% quota consumption -> Restrict high-cost ops
FAIL_CLOSED_THRESHOLD = 1.00 # 100% quota consumption -> Hard block / fallback


@dataclass
class QuotaStatus:
    metric: str
    current_usage: int
    limit: int
    usage_percent: float
    is_warning: bool
    is_critical: bool
    is_exhausted: bool


class QuotaManager:
    """Tracks and enforces infrastructure usage to preserve the ₹0 budget invariant."""

    def __init__(
        self,
        persistence_path: Optional[Path] = None,
        custom_limits: Optional[Dict[str, int]] = None,
    ) -> None:
        if persistence_path is None:
            persistence_path = Path.cwd() / "data" / "quota_state.json"
        self.path = persistence_path
        self.limits = {**DEFAULT_LIMITS, **(custom_limits or {})}
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            initial_state = {
                "last_daily_reset": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "last_monthly_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
                "metrics": {key: 0 for key in self.limits},
            }
            self._save_state(initial_state)

    def _load_state(self) -> Dict[str, Any]:
        self._ensure_storage()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            logger.warning(f"Error reading quota state file: {e}. Resetting to empty state.")
            state = {
                "last_daily_reset": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "last_monthly_reset": datetime.now(timezone.utc).strftime("%Y-%m"),
                "metrics": {key: 0 for key in self.limits},
            }

        # Check and handle resets
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        month_str = now.strftime("%Y-%m")

        state_modified = False

        if state.get("last_daily_reset") != today_str:
            # Reset daily metrics
            for k in list(state.get("metrics", {}).keys()):
                if "daily" in k or "minute" in k:
                    state["metrics"][k] = 0
            state["last_daily_reset"] = today_str
            state_modified = True

        if state.get("last_monthly_reset") != month_str:
            # Reset monthly metrics
            for k in list(state.get("metrics", {}).keys()):
                if "monthly" in k:
                    state["metrics"][k] = 0
            state["last_monthly_reset"] = month_str
            state_modified = True

        if state_modified:
            self._save_state(state)

        return state

    def _save_state(self, state: Dict[str, Any]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        temp_path.replace(self.path)

    def record_usage(self, metric: str, amount: int = 1) -> QuotaStatus:
        """Atomically increments metric usage and returns updated status."""
        state = self._load_state()
        metrics = state.setdefault("metrics", {})
        metrics[metric] = metrics.get(metric, 0) + amount
        self._save_state(state)

        return self.check_quota(metric)

    def check_quota(self, metric: str) -> QuotaStatus:
        """Evaluates whether an operation is permissible under zero-cost constraints."""
        state = self._load_state()
        current = state.get("metrics", {}).get(metric, 0)
        limit = self.limits.get(metric, 100_000)
        percent = (current / limit) if limit > 0 else 0.0

        is_warning = percent >= WARNING_THRESHOLD
        is_critical = percent >= CRITICAL_THRESHOLD
        is_exhausted = percent >= FAIL_CLOSED_THRESHOLD

        if is_critical:
            logger.critical(
                f"[QUOTA DEFENSE ALERT] Metric '{metric}' at {percent:.1%} ({current}/{limit})! "
                f"Fail-closed threshold is {FAIL_CLOSED_THRESHOLD:.0%}."
            )
        elif is_warning:
            logger.warning(
                f"[QUOTA WARNING] Metric '{metric}' at {percent:.1%} ({current}/{limit})."
            )

        return QuotaStatus(
            metric=metric,
            current_usage=current,
            limit=limit,
            usage_percent=round(percent, 4),
            is_warning=is_warning,
            is_critical=is_critical,
            is_exhausted=is_exhausted,
        )

    def can_consume(self, metric: str, projected_amount: int = 1) -> bool:
        """Returns True if projected consumption does not breach fail-closed quota."""
        status = self.check_quota(metric)
        return (status.current_usage + projected_amount) <= status.limit

    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """Returns full audit summary of all tracked infrastructure quotas."""
        summary = {}
        for metric in self.limits:
            status = self.check_quota(metric)
            summary[metric] = asdict(status)
        return summary


# Global singleton instance for easy import across modules
global_quota_manager = QuotaManager()
