import logging
from typing import Any

import httpx

from ..config import ARSENAL_TEAM_ID, FOOTBALL_DATA_API_KEY

BASE_URL = "https://api.football-data.org/v4"
log = logging.getLogger(__name__)


class FootballDataClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"X-Auth-Token": FOOTBALL_DATA_API_KEY},
            timeout=15.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str) -> dict[str, Any]:
        resp = await self._client.get(path)
        resp.raise_for_status()
        return resp.json()

    async def get_team_matches(self, status: str | None = None) -> list[dict]:
        params = f"?status={status}" if status else ""
        data = await self._get(f"/teams/{ARSENAL_TEAM_ID}/matches{params}")
        return [self._normalize_match(m) for m in data.get("matches", [])]

    async def get_match(self, match_id: int) -> dict:
        data = await self._get(f"/matches/{match_id}")
        return self._normalize_match(data.get("match", data))

    @staticmethod
    def _normalize_match(m: dict) -> dict:
        score = m.get("score", {}).get("fullTime", {}) or {}
        return {
            "id": m["id"],
            "utc_date": m["utcDate"],
            "status": m["status"],
            "competition": (m.get("competition") or {}).get("name", ""),
            "matchday": m.get("matchday"),
            "home_team": (m.get("homeTeam") or {}).get("name", ""),
            "home_team_id": (m.get("homeTeam") or {}).get("id"),
            "away_team": (m.get("awayTeam") or {}).get("name", ""),
            "away_team_id": (m.get("awayTeam") or {}).get("id"),
            "score_home": score.get("home"),
            "score_away": score.get("away"),
            "raw": m,
        }
