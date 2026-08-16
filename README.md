# checkprint

Minimal check register + PDF check printing app. Tracks checks written and
deposits made, computes a running balance, and prints checks onto
pre-printed check stock via a PDF with configurable field positions.

No authentication — intended to run behind a reverse proxy (e.g. Traefik)
on a trusted internal network. Auth (Authentik) is a planned v2, not part
of this app.

## Run locally

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Visit http://localhost:8000. The SQLite database is created at
`instance/checkprint.db` on first run.

## Run with Docker Compose

```
docker compose up --build
```

This builds the image, persists the database to `./data/checkprint.db` on
the host, and joins the external `proxy` Docker network with Traefik
labels for `checkprint.ce.int`. Adjust the `Host()` rule and `TZ` in
`docker-compose.yml` as needed. Uncomment the `ports` block if you want to
reach it directly without Traefik.

## Tweaking check print positions

`config/check_layout.yml` controls where each field is drawn on the printed PDF
(in points, 1/72 inch, origin at bottom-left). It's bind-mounted into the
container and re-read on every print request — edit it and reprint, no
rebuild or restart required.

The `config/` directory (not the file itself) is what's bind-mounted in
`docker-compose.yml`. That's deliberate: editors and tools like `sed -i`
typically save by writing a new file and renaming it over the old one,
which swaps the inode — a bind mount of the *file* would keep pointing at
the old, now-detached inode and silently stop seeing edits. Mounting the
containing directory avoids that.

If a printed check is off by a consistent amount in every field, adjust
`offset.x_pt` / `offset.y_pt` once instead of editing every field
individually (this covers the common case of uniform paper-feed drift).
If only one field is off, edit that field's `x`/`y` directly.

The current values are a first-pass estimate from `check_template.pdf` (a
600 DPI scan) and have not yet been verified against a real printed
check — expect to do one print-and-measure pass.

## Data model notes

- Money is stored as integer cents, never floats.
- Running balance is computed on read (SQL window function), never
  stored, so it can't drift from a manual edit or deleted row.
- Voided transactions stay in the register (struck through) but are
  excluded from the balance — nothing is ever hard-deleted.
- The balance starts at zero. There's no separate "opening balance"
  setting — seed the register with a normal deposit (e.g. described as
  "Opening balance") dated whenever you want the history to start.
- Check numbers are entered by the user (the app suggests the last
  check number + 1, but never generates or enforces one) and are tracked
  in the database only — they are **not** drawn on the printed PDF,
  since they're already pre-printed on the physical check stock.
