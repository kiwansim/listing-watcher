# poshmark-watcher

Polls one or more marketplace searches and emails you when a new listing shows up.

Currently wired up: **Poshmark** (plain HTML fetch, no auth needed). Mercari and
Depop searches can be added to `config.json`, but they need a headless-browser
adapter first — Mercari's search API 401s without a browser session, and Depop
sits behind a Cloudflare bot challenge. See the comment in `check_listings.py`.

## How it works

- `config.json` lists the searches to track (site, URL, label).
- `check_listings.py` fetches each search, diffs the listing IDs against
  `state.json`, and emails you the new ones. The very first run for a given
  search just seeds `state.json` — it won't email you every existing listing.
- `.github/workflows/watch.yml` runs the script every 15 minutes on GitHub
  Actions and commits the updated `state.json` back to the repo so state
  persists between runs.

## Setup

1. **Create a GitHub repo and push this folder to it** (see commands below).

2. **Create a Gmail App Password** — this lets the script send mail through
   your Gmail account without your real password:
   - Turn on 2-Step Verification on the Google account you want to send from:
     https://myaccount.google.com/security
   - Create an App Password: https://myaccount.google.com/apppasswords
     (choose "Mail" / "Other", name it e.g. "listing-watcher")
   - Copy the 16-character password it gives you.

3. **Add repo secrets** (Settings → Secrets and variables → Actions → New
   repository secret), or via the `gh` CLI — run these yourself so the
   password never appears in a transcript or shell history:

   ```bash
   gh secret set GMAIL_ADDRESS --body "youraddress@gmail.com"
   gh secret set NOTIFY_EMAIL --body "youraddress@gmail.com"
   gh secret set GMAIL_APP_PASSWORD
   ```

   The last one with no `--body` will prompt you to paste the app password
   interactively.

4. **Trigger a run** — either wait 15 minutes, or go to the Actions tab →
   "Watch listings" → "Run workflow" to trigger it manually. The first run
   just seeds `state.json` (no email). After that, any new listing triggers
   an email.

## Adding another search

Add an entry to `config.json` with a unique `id`, `site` (must match a key in
`FETCHERS` in `check_listings.py`), `label`, and `url`.

## Local testing

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 check_listings.py
```

Without `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` set, this will fail only if it
actually finds new listings to email — first-run seeding and "no new
listings" both work fine without credentials.
