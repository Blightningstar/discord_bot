# discord_bot

A full-stack Discord bot built with **discord.py** and **Django**, designed for personal servers only. It combines a Discord bot process (slash/prefix commands) with a companion Django web application that serves a live command-reference site, shares a PostgreSQL database, and is deployed via Gunicorn.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Features](#features)
  - [Music Bot](#music-bot)
  - [Halloween Bot](#halloween-bot)
  - [Django Web App](#django-web-app)
- [Tech Stack](#tech-stack)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Development](#development)
- [Database](#database)

---

## Overview

The project runs two concurrent processes that share the same Django ORM and PostgreSQL database:

1. **Discord bot** (`marmoBot.py`) — loads cogs and connects to Discord via `discord.py`.
2. **Django web server** (`manage.py` + Gunicorn) — serves a commands-help website and the Django admin panel.

Both are Django apps, so `manage.py` handles migrations, the admin interface, and static file collection for both.

---

## Architecture

```
marmoBot.py  ──────────────────────────────────────────────
  │                                                        │
  ├── MusicCog (music_bot/)        HalloweenCog (halloween_bot/)
  │       │                                │
  │  yt-dlp / YouTube Data API      BeautifulSoup scraper
  │  FFmpeg audio streaming          creepypasta.xyz
  │  Django ORM (SongLog)
  │
Django (discord_bot/)
  ├── manage.py  ──► migrations, admin, collectstatic
  ├── settings.py  ──► environs (.env)
  ├── urls.py  ──► / (home), /admin/, /<bot_name>/commands_help/
  └── music_bot/urls.py  ──► per-command help pages
```

The bot cogs are initialized inside an `asyncio` event loop (`asyncio.run(main())`) while Django is served synchronously by Gunicorn. `asgiref.sync_to_async` bridges the async bot code with Django's synchronous ORM calls.

---

## Project Structure

```
discord_bot/               ← Django project root (contains manage.py)
├── marmoBot.py            ← Bot entry point; loads cogs and starts the client
├── manage.py              ← Django management CLI
├── discord_bot/           ← Django project package (settings, urls, wsgi)
│   ├── settings.py
│   ├── urls.py
│   └── views.py           ← Home page view
├── music_bot/             ← Django app: Music cog + web help pages
│   ├── music_cog.py       ← All music Discord commands (MusicCog)
│   ├── music_commands.py  ← Command name constants and aliases
│   ├── music_reference.py ← Early prototype/reference implementation
│   ├── models.py          ← SongLog model (song cache)
│   ├── views.py           ← Per-command help page views
│   └── urls.py            ← URL routes for music help pages
├── halloween_bot/         ← Django app: Halloween story cog
│   ├── halloween_cog.py   ← HalloweenCog: daily creepypasta command
│   └── halloween_commands.py ← Command aliases
└── templates/             ← Django HTML templates for all help pages
```

---

## Features

### Music Bot

`MusicCog` is the primary feature. It streams audio from YouTube directly into a Discord voice channel using `yt-dlp` + `FFmpeg`.

| Command | Aliases | Description |
|---|---|---|
| `play <url\|name>` | `r`, `rolela`, `p` | Queue a YouTube URL or search by name |
| `play_next <url\|name>` | `pn`, `n` | Insert a song at the front of the queue |
| `queue` | `c`, `cola`, `q` | Display all queued songs as rich embeds |
| `now_playing` | `np`, `cual`, `z`, `ls` | Show the currently playing song |
| `skip` | `s`, `saltela`, `siguiente` | Skip to the next song |
| `pause` | `d`, `pausa`, `pa`, `pare` | Pause playback |
| `resume` | `re`, `siga`, `continue` | Resume playback |
| `shuffle` | `b`, `barajela` | Shuffle the current queue |
| `move <pos1> <pos2>` | `m`, `mueva`, `coleme` | Move a song within the queue |
| `join` | `u`, `unete`, `j` | Join the user's voice channel |
| `disconnect` | `jale`, `desconectar`, `apagar` | Leave the voice channel |
| `help` | `h`, `commands`, `ayuda`, `alias` | Link to the web command-reference |

**Notable implementation details:**

- **Song caching** — Before downloading audio, the bot queries the `SongLog` database table. If a song has been played before, its metadata (title, duration, thumbnail) is retrieved from the DB instead of re-fetching from the YouTube Data API, reducing API quota usage.
- **Playlist support** — Passing a YouTube playlist URL enqueues all videos in the playlist using the YouTube Data API v3 (paginated, up to 50 videos per page).
- **Audio format selection** — `yt-dlp` extracts available formats and selects the best Opus audio stream based on bitrate; falls back to a Node.js JS runtime if the initial extraction fails.
- **Async/sync bridge** — ORM calls (`SongLog.objects.filter`, `.save()`) are wrapped with `@sync_to_async` to keep the asyncio event loop unblocked.
- **Channel guard** — Commands are only accepted in a designated music text channel (`MUSIC_CHANNEL`), and the command author must be in a voice channel.

### Halloween Bot

`HalloweenCog` delivers a daily horror story (creepypasta) throughout October.

| Command | Aliases | Description |
|---|---|---|
| `creepy_pasta` | configured in `halloween_commands.py` | Post the day's creepypasta story |

- Scrapes story text from `es.creepypasta.xyz` using `BeautifulSoup`.
- Splits long stories across multiple paginated Discord embeds (max 1024 chars per embed field, preserving word boundaries).
- Enforces a one-story-per-day limit by writing the current day to `stories_telled.txt`.
- Only works in the designated Halloween text channel (`HALLOWEEN_CHANNEL`).

### Django Web App

A companion website served alongside the bot that documents every music command:

- **`/`** — Home page.
- **`/admin/`** — Django admin panel (manage `SongLog` entries).
- **`/<bot_name>/commands_help/`** — Index of all music commands.
- **`/<bot_name>/commands_help/<command>`** — Individual help page for each command (play, queue, skip, shuffle, etc.).

Static files are served via **WhiteNoise** (no separate static file server needed).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Discord bot framework | `discord.py` 2.x with `commands.Cog` |
| Web framework | Django 4.2 |
| Audio streaming | `yt-dlp` + `FFmpeg` (`FFmpegPCMAudio`) |
| YouTube metadata | YouTube Data API v3 (`google-api-python-client`) |
| HTML scraping | `BeautifulSoup4` |
| Database | PostgreSQL (`psycopg` v3) |
| Web server | Gunicorn |
| Static files | WhiteNoise |
| Config management | `environs` (`.env` file) |
| Dependency management | `uv` (lock file → `requirements.txt`) |
| Python | ≥ 3.14 |

---

## Configuration

All settings are loaded from a `.env` file via `environs`. Create a `.env` in the Django project root (`discord_bot/`) by running
```bash
# You'll need to populate the environment variables.
./setup_env.sh
```

---

## Running the Project

### Install dependencies

```bash
# Using uv (recommended)
uv sync

# Or pip
pip install -r requirements.txt
```

### Apply migrations

```bash
cd discord_bot
python manage.py migrate
```

### Start the Django web server

```bash
# Development
python manage.py runserver

# Production
gunicorn discord_bot.wsgi:application
```

### Start the Discord bot

```bash
cd discord_bot
python marmoBot.py
```

Both processes can run in parallel and share the same database.

---

## Development

The project uses [pre-commit](https://pre-commit.com/) to enforce code quality on every commit. Install the hooks after setting up your environment:

```bash
# Install dev dependencies (includes pre-commit)
uv sync

# Register the hooks in your local .git directory
pre-commit install
```

The following hooks run automatically on `git commit`:

| Hook | Purpose |
|---|---|
| `black` | Opinionated Python code formatter |
| `isort` | Sorts and groups import statements |
| `flake8` | PEP 8 style and lint checks |
| `check-added-large-files` | Blocks files > 900 KB |
| `check-json` / `check-yaml` | Validates JSON and YAML syntax |
| `check-merge-conflict` | Prevents accidental merge-conflict markers |
| `end-of-file-fixer` / `trailing-whitespace` | Normalises whitespace |
| `uv-lock` + `uv-export` | Keeps `requirements.txt` and `requirements-dev.txt` in sync with `pyproject.toml` |

All hooks exclude `migrations/`, `.venv/`, and `.git/` directories.

To run the hooks manually against all files:

```bash
pre-commit run --all-files
```

---

## Database

The `music_bot` app contains one model:

**`SongLog`** — caches YouTube video metadata to avoid redundant API calls.

| Field | Type | Notes |
|---|---|---|
| `url` | `URLField` (PK) | Unique YouTube video ID |
| `title` | `CharField` | Video title |
| `duration` | `FloatField` | Duration in seconds |
| `thumbnail` | `ImageField` | Thumbnail URL |

Migrations are managed via Django's standard migration system (`music_bot/migrations/`).
