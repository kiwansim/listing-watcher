#!/usr/bin/env python3
"""Poll marketplace searches and email when new listings appear."""
import json
import os
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_PATH = BASE_DIR / "state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )
}


def fetch_poshmark(url):
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for tile in soup.select("div.tile-grid-redesign"):
        listing_id = tile.get("data-et-prop-listing_id")
        if not listing_id:
            continue

        link = tile.select_one("a.tile-grid-redesign__meta-link") or tile.select_one(
            "a.tile__covershot"
        )
        href = link["href"] if link else None
        title_el = tile.select_one("span.tile-grid-redesign__title")
        price_el = tile.select_one("span.tile-grid-redesign__price-current")

        items.append(
            {
                "id": listing_id,
                "title": title_el.get_text(strip=True) if title_el else "(untitled)",
                "price": price_el.get_text(strip=True) if price_el else "",
                "url": f"https://poshmark.com{href}" if href else url,
            }
        )
    return items


FETCHERS = {
    "poshmark": fetch_poshmark,
    # "mercari" and "depop" are not wired up yet — they need a headless
    # browser session (Mercari's API 401s without one; Depop sits behind a
    # Cloudflare bot challenge). Add adapters here once that's built.
}


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True))


def send_email(subject, body):
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_password = os.environ["GMAIL_APP_PASSWORD"]
    to_address = os.environ.get("NOTIFY_EMAIL", gmail_address)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_address

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, [to_address], msg.as_string())


def main():
    config = load_json(CONFIG_PATH, [])
    state = load_json(STATE_PATH, {})
    state_changed = False

    for search in config:
        search_id = search["id"]
        label = search.get("label", search_id)
        fetcher = FETCHERS.get(search["site"])
        if not fetcher:
            print(f"skip {search_id}: no fetcher for site '{search['site']}'")
            continue

        try:
            items = fetcher(search["url"])
        except Exception as exc:
            print(f"error fetching {search_id}: {exc}")
            continue

        seen_ids = set(state.get(search_id, []))
        current_ids = {item["id"] for item in items}
        is_first_run = search_id not in state
        new_items = [item for item in items if item["id"] not in seen_ids]

        if is_first_run:
            print(f"{search_id}: first run, seeding {len(current_ids)} listing id(s), no email")
        elif new_items:
            sections = [f"New listings for {label}:"]
            for item in new_items:
                price = f" - {item['price']}" if item["price"] else ""
                sections.append(f"- {item['title']}{price}\n  {item['url']}")
            body = "\n\n".join(sections)
            send_email(f"[{label}] {len(new_items)} new listing(s)", body)
            print(f"{search_id}: emailed {len(new_items)} new listing(s)")
        else:
            print(f"{search_id}: no new listings ({len(current_ids)} total seen)")

        updated_ids = seen_ids | current_ids
        if updated_ids != seen_ids:
            state[search_id] = sorted(updated_ids)
            state_changed = True

    if state_changed:
        save_json(STATE_PATH, state)
        print("state.json updated")


if __name__ == "__main__":
    main()
