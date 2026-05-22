"""Arsenal squad data from ESPN's unofficial public API.

No API key or registration required. ESPN uses this endpoint internally
for their own site, so the data is comprehensive and up-to-date.
"""
import httpx

ARSENAL_ESPN_ID = 359
_URL = f"https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams/{ARSENAL_ESPN_ID}/roster"

_POSITION_MAP = {
    "Goalkeeper": "Goalkeeper",
    "Defender": "Defender",
    "Midfielder": "Midfielder",
    "Forward": "Attacker",
    "Attacker": "Attacker",
}


async def fetch_arsenal_squad() -> list[dict]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(_URL)
        resp.raise_for_status()
        data = resp.json()

    players = []
    for player in data.get("athletes", []):
        if (player.get("status") or {}).get("type") != "active":
            continue
        pos_label = (player.get("position") or {}).get("name", "")
        players.append({
            "name": player.get("fullName", ""),
            "position": _POSITION_MAP.get(pos_label, pos_label),
            "age": player.get("age"),
            "jersey": player.get("jersey"),
        })
    return players
