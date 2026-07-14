"""Flask application for consent-first movement recording."""

from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from typing import Any

import requests
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

DEFAULT_TASKS = [
    "Look at the camera and smile naturally",
    "Raise one hand and show your open palm",
    "Slowly close that hand into a gentle fist",
    "Open your hand again and spread your fingers",
    "Raise one arm as comfortably as you can, then lower it",
]
MAX_UPLOAD_BYTES = 45 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {"video/webm", "video/mp4", "video/quicktime"}


def _tasks_from_environment() -> list[str]:
    raw = os.getenv("TASKS_JSON")
    if not raw:
        return DEFAULT_TASKS
    try:
        tasks = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TASKS_JSON must be a valid JSON array") from exc
    if not isinstance(tasks, list) or not tasks or not all(isinstance(x, str) for x in tasks):
        raise RuntimeError("TASKS_JSON must be a non-empty JSON array of strings")
    cleaned = [task.strip() for task in tasks if task.strip()]
    if not cleaned:
        raise RuntimeError("TASKS_JSON must contain at least one non-empty prompt")
    return cleaned


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        MAX_CONTENT_LENGTH=MAX_UPLOAD_BYTES,
        PROJECT_NAME=os.getenv("PROJECT_NAME", "CrowdCollect Movement Demo"),
        PROJECT_DESCRIPTION=os.getenv(
            "PROJECT_DESCRIPTION",
            "We are evaluating a simple way to collect short movement videos for research "
            "prototyping. You will be asked to perform a few visible face, hand, and arm movements.",
        ),
        CONTACT_EMAIL=os.getenv("CONTACT_EMAIL", "the research team"),
        TASKS=_tasks_from_environment(),
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        TELEGRAM_CHAT_ID=os.getenv("TELEGRAM_CHAT_ID", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "").lower()
        in {"1", "true", "yes"},
    )
    if test_config:
        app.config.update(test_config)

    @app.after_request
    def security_headers(response):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
            "script-src 'self'; style-src 'self'; frame-ancestors 'none'"
        )
        response.headers["Permissions-Policy"] = "camera=(self), microphone=()"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def information():
        return render_template(
            "information.html",
            project_name=app.config["PROJECT_NAME"],
            description=app.config["PROJECT_DESCRIPTION"],
            contact=app.config["CONTACT_EMAIL"],
        )

    @app.post("/consent")
    def consent():
        if request.form.get("consent") != "yes":
            return render_template(
                "information.html",
                project_name=app.config["PROJECT_NAME"],
                description=app.config["PROJECT_DESCRIPTION"],
                contact=app.config["CONTACT_EMAIL"],
                error="Please check the consent box before continuing.",
            ), 400
        session.clear()
        session["consented_at"] = datetime.now(UTC).isoformat()
        session["participant_id"] = secrets.token_urlsafe(8)
        return redirect(url_for("record"))

    @app.get("/record")
    def record():
        if "consented_at" not in session:
            return redirect(url_for("information"))
        return render_template("record.html", tasks=app.config["TASKS"])

    @app.post("/upload")
    def upload():
        if "consented_at" not in session:
            return jsonify(error="Consent is required before uploading."), 403

        token = app.config["TELEGRAM_BOT_TOKEN"]
        chat_id = app.config["TELEGRAM_CHAT_ID"]
        if not token or not chat_id:
            app.logger.error("Telegram credentials are not configured")
            return jsonify(error="The collection service is not configured yet."), 503

        video = request.files.get("video")
        if video is None or not video.filename:
            return jsonify(error="No recording was received."), 400
        media_type = (video.mimetype or "").split(";", 1)[0].lower()
        if media_type not in ALLOWED_VIDEO_TYPES:
            return jsonify(error="Unsupported video format."), 415

        participant_id = session.get("participant_id", "unknown")
        completed_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        filename = secure_filename(video.filename) or "movement-session.webm"
        caption = f"CrowdCollect session\nID: {participant_id}\nCompleted: {completed_at}"

        try:
            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (filename, video.stream, media_type)},
                timeout=(10, 120),
            )
            response.raise_for_status()
            result = response.json()
            if not result.get("ok"):
                raise requests.RequestException(result.get("description", "Telegram rejected upload"))
        except (requests.RequestException, ValueError) as exc:
            # Requests exceptions can include the request URL, which contains the bot token.
            app.logger.warning("Telegram upload failed (%s)", type(exc).__name__)
            return jsonify(error="Upload failed. Please keep this page open and try again."), 502

        session.clear()
        return jsonify(ok=True)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify(error="The recording is too large. Please record a shorter session."), 413

    return app


app = create_app()
