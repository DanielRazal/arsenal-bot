# Arsenal Bot

Personal Telegram + Discord bot for Arsenal FC: live goal alerts, pre-match notifications, AI match summaries (Hebrew), transfer news, and a morning news digest.

**Stack:** Python 3.11 · asyncio · SQLite · football-data.org · Groq Llama 3.3 70B (+ Gemini fallback) · python-telegram-bot · discord.py

**Cost:** $0/month. All services used have genuine free tiers — no credit card charges.

---

## Features

| Feature | What it does |
|---------|--------------|
| Pre-match alert | 30 minutes before kickoff — competition, opponent, kickoff time |
| Live goals | Pushes every goal during the match (~45 s polling) |
| Post-match summary | AI-generated Hebrew summary with personality once the final whistle blows |
| Transfer news | Polls RSS feeds (Arseblog, Sky, BBC, Guardian, Reddit r/Gunners) every 15 min |
| Morning digest | 08:00 Israel time — top 5 Arsenal stories from the last 24h, summarized |

---

## Setup

### 1. Get the keys (one-time, all free)

| Service | Where | Key var in `.env` |
|---------|-------|--------------------|
| football-data.org | <https://www.football-data.org/client/register> | `FOOTBALL_DATA_API_KEY` |
| Telegram bot | message `@BotFather` → `/newbot` | `TELEGRAM_BOT_TOKEN` |
| Telegram chat ID | message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` | `TELEGRAM_CHAT_ID` |
| Discord webhook | server Settings → Integrations → Webhooks → New | `DISCORD_WEBHOOK_URL` |
| Groq | <https://console.groq.com> | `GROQ_API_KEY` |
| Gemini *(optional fallback)* | <https://aistudio.google.com/apikey> | `GEMINI_API_KEY` |

### 2. Install and run locally

```bash
python -m venv .venv
.venv\Scripts\activate         # Windows
# or: source .venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
copy .env.example .env         # Windows  (cp on Linux)
# edit .env and paste your keys

python -m src.main
```

If everything is wired up, within ~30 s you'll see:

```
INFO arsenal-bot | Arsenal bot starting…
INFO src.workers.match_watcher | match_watcher started
INFO src.workers.news_poller | news_poller started
INFO src.workers.morning_digest | morning_digest scheduled daily at 08:00 Asia/Jerusalem
```

### 3. Deploy 24/7

See [deploy/setup_oracle.md](deploy/setup_oracle.md) for step-by-step Oracle Cloud Always Free instructions.

---

## Hybrid mode with GitHub Actions

When the PC is asleep, scheduled work can run for free in GitHub Actions:

| Workload | Where it runs |
|----------|----------------|
| ⚽ Live match alerts, half-time, red cards, post-match summary | PC (always-on host) |
| 🤖 `/next` Telegram command | PC |
| 📰 News polling (every 15 min) | GitHub Actions |
| ☕ Morning digest (daily 08:00 IL) | GitHub Actions |

### One-time setup

1. **Add GitHub repo secrets** at <https://github.com/DanielRazal/arsenal-bot/settings/secrets/actions>. Click "New repository secret" for each:

   | Secret name | Paste the value from your local `.env` |
   |-------------|------------------------------------------|
   | `FOOTBALL_DATA_API_KEY` | `FOOTBALL_DATA_API_KEY` |
   | `TELEGRAM_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` |
   | `TELEGRAM_CHAT_ID` | `TELEGRAM_CHAT_ID` |
   | `DISCORD_WEBHOOK_URL` | `DISCORD_WEBHOOK_URL` |
   | `GROQ_API_KEY` | `GROQ_API_KEY` |

2. **Disable the duplicated workers on the PC** by adding to your `.env`:
   ```
   ENABLE_NEWS_POLLER=false
   ENABLE_MORNING_DIGEST=false
   ```
   then restart `python -m src.main`. The log will confirm:
   ```
   INFO arsenal-bot | News poller disabled (handled by GitHub Actions)
   INFO arsenal-bot | Morning digest disabled (handled by GitHub Actions)
   ```

3. **Verify the workflows** at <https://github.com/DanielRazal/arsenal-bot/actions>. After the next 15-minute boundary you'll see a "News Poll" run; the "Morning Digest" run appears once per day around 05:30 UTC.

### Manually trigger a run

Both workflows expose `workflow_dispatch`, so you can fire either of them on demand:

1. Go to the Actions tab → pick the workflow → click "Run workflow" (top-right).

---

## Project layout

```
src/
├── main.py                  entry point — wires workers + notifiers
├── config.py                .env loader
├── db.py                    SQLite schema + dedup helpers
├── formatting.py            message templates (Hebrew)
├── workers/
│   ├── match_watcher.py     adaptive polling (idle → prematch → live)
│   ├── news_poller.py       RSS every 15 min
│   └── morning_digest.py    APScheduler cron job
├── sources/
│   ├── football_data.py     football-data.org client
│   ├── rss.py               feedparser wrapper
│   └── feeds.py             feed list + keyword filter
├── llm/
│   ├── client.py            Groq + Gemini fallback
│   ├── match_summary.py     post-match prompt
│   └── article_digest.py    morning digest prompt
└── notifiers/
    ├── telegram.py
    ├── discord.py           webhook-based
    └── fanout.py            sends to both
```

---

## Tweaking

- **Polling cadence:** edit constants at the top of `src/workers/match_watcher.py`.
- **Add a feed:** append to `FEEDS` in `src/sources/feeds.py`.
- **Change LLM personality:** edit `SYSTEM_PROMPT` in `src/llm/match_summary.py`.
- **Morning digest time:** change `MORNING_DIGEST_HOUR` in `.env`.
- **Different team:** change `ARSENAL_TEAM_ID` in `.env` (Spurs = 73, City = 65, etc.) — though that would be a strange life choice.

---

## Resetting state

To re-trigger alerts for matches/articles already processed, delete `data/state.db`. It will be recreated empty on next start.
