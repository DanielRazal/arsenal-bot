# Deploy on Render (free tier, 24/7)

This runs the **whole bot** — live goals, red cards, pre-match, half-time,
post-match AI summary, Spurs schadenfreude, news polling, morning digest, and
the Telegram `/commands` — as a single always-on process. This is what GitHub
Actions can't do: Actions can only fire once a minute *at best* and is often
delayed several minutes, so real-time goals arrive late or not at all. Here the
poller checks every ~45 s while a match is live.

## Why a Web Service (and the uptime pinger)

Render's **free** tier only includes Web Services — there is no free Background
Worker. So the bot runs as a Web Service and exposes a tiny health endpoint
(`/`, see `src/health.py`). Free Web Services **spin down after 15 minutes of
no inbound traffic**, which would stop the poller — so we keep it awake with a
free external pinger (step 4).

## 1. Push the code to GitHub

The repo already has `render.yaml`. Commit and push the migration changes:

```bash
git add -A
git commit -m "Add Render deployment (web service + health endpoint)"
git push
```

## 2. Create the service from the Blueprint

1. Go to <https://dashboard.render.com> → **New** → **Blueprint**.
2. Connect the `arsenal-bot` GitHub repo. Render reads `render.yaml` and
   proposes one Web Service named **arsenal-bot** on the **Free** plan.
3. Click **Apply**.

## 3. Add the secrets

In the service → **Environment** tab, add each of these (values from your local
`.env`). They are marked `sync: false` in the blueprint precisely so they are
*not* committed to git:

| Key | From `.env` |
|-----|-------------|
| `FOOTBALL_DATA_API_KEY` | same |
| `TELEGRAM_BOT_TOKEN` | same |
| `TELEGRAM_CHAT_ID` | same |
| `DISCORD_WEBHOOK_URL` | same |
| `GROQ_API_KEY` | same |
| `GEMINI_API_KEY` | same (optional) |

Save — Render redeploys automatically. Watch **Logs** for:

```
Health server listening on port 10000
Arsenal bot starting…
match_watcher started
news_poller started
```

## 4. Keep it awake (free, required)

A free Web Service sleeps after 15 min idle. Point a free uptime pinger at the
service's public URL (shown at the top of the service page, e.g.
`https://arsenal-bot.onrender.com`):

- **UptimeRobot** (<https://uptimerobot.com>): New Monitor → HTTP(s) → paste the
  URL → check interval **5 minutes**.
- or **cron-job.org** (<https://cron-job.org>): new cron job → the URL → every
  10 minutes.

That single request every few minutes resets the idle timer and keeps the
poller running around the clock.

## State / duplicate alerts

The free tier has an **ephemeral filesystem**: the SQLite state in
`data/state.db` is wiped on every restart/deploy. To avoid re-announcing goals
already on the scoreboard after a restart, `match_watcher.prime_state()` runs on
startup and marks the current live/recent events as "already sent" without
notifying. The only gap is an event that lands in the ~1-minute restart window
(rare, since the pinger keeps restarts infrequent). If you later want zero risk,
upgrade to a paid plan and attach a Persistent Disk mounted at `data/`.

## GitHub Actions — fully retired

Everything now runs in this one process, including the standings alert (every
6h) and the weekly recap (Friday 19:00 IL), which were ported into
`src/workers/standings_alert.py` and `src/workers/weekly_recap.py`. All seven
workflows in `.github/workflows/` were therefore renamed to `*.yml.disabled` so
nothing fires there and you never get a duplicate notification. To revert any of
them, rename back to `.yml` (and set the matching `ENABLE_*` env var to `false`
on Render so it isn't sent twice).
