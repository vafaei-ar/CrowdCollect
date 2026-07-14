# CrowdCollect

CrowdCollect is a small, consent-first demo for collecting short movement videos.
A participant opens a public link, reads the study information, explicitly
consents, follows a sequence of movement prompts while seeing their camera
preview, and sends the recording to a private Telegram chat through a bot.

The application does **not** use a database or retain uploaded videos on disk.
This repository is a research demo, not a HIPAA-compliant production system or
a clinical assessment tool.

## What it does

- requires an explicit consent checkbox before camera access;
- requests video-only camera access (the microphone is not requested);
- overlays a face-and-shoulder alignment guide on the preview for consistent framing;
- records a guided session with configurable prompts and animated movement sketches;
- adapts the camera, guidance, and controls for portrait and landscape phones;
- uploads the result to a configured Telegram chat;
- assigns a random session identifier instead of asking for a name;
- limits uploads to 45 MB and recording duration to 90 seconds.

## Local setup

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
```

Edit `.env`, then start the app:

```bash
set -a
source .env
set +a
flask --app crowdcollect.app run --debug
```

Open <http://127.0.0.1:5000>. Browsers allow camera access on `localhost`; a
deployed site must use HTTPS.

## Find the Telegram chat ID

1. Create a bot with Telegram's `@BotFather` and copy its token.
2. Open a chat with the new bot and send `/start` (or add it to the intended
   group and send a message there).
3. Run either command below and follow the prompt:

```bash
crowdcollect-chat-id
# or
python scripts/show_chat_id.py
```

The helper reads `TELEGRAM_BOT_TOKEN` if it is set; otherwise it securely asks
for the token. Copy the displayed ID into `TELEGRAM_CHAT_ID`.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | yes | Secret token from BotFather |
| `TELEGRAM_CHAT_ID` | yes | Destination user/group/channel ID |
| `SECRET_KEY` | production | Signs the short-lived consent session cookie |
| `PROJECT_NAME` | no | Heading shown to participants |
| `PROJECT_DESCRIPTION` | no | Plain-text project explanation |
| `CONTACT_EMAIL` | no | Contact shown on the consent page |
| `TASKS_JSON` | no | JSON array of movement prompt strings |

Never commit the bot token. `.env` files are ignored by Git.

Example custom prompts:

```bash
export TASKS_JSON='["Smile naturally", "Show your open palm", "Make a gentle fist"]'
```

## Deploy free on Render

1. Push this repository to GitHub.
2. In Render, choose **New > Blueprint** and connect the repository.
3. Apply the included `render.yaml` blueprint using the Free instance type.
4. In the Render dashboard, enter `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
   `PROJECT_DESCRIPTION`, and `CONTACT_EMAIL` when prompted.
5. Share the generated `https://...onrender.com` URL.

Render's free web service sleeps when idle, so the first visit after inactivity
can take roughly a minute. Its filesystem is ephemeral, which is fine here
because CrowdCollect forwards recordings to Telegram rather than storing them.

## Verify

```bash
pytest
ruff check .
```

GitHub Actions runs these checks on pushes and pull requests.
