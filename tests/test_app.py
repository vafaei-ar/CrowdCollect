from io import BytesIO
from unittest.mock import Mock, patch

import pytest

from crowdcollect.app import create_app


@pytest.fixture()
def app():
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "TELEGRAM_BOT_TOKEN": "test-token",
            "TELEGRAM_CHAT_ID": "12345",
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def consent(client):
    return client.post("/consent", data={"consent": "yes"})


def test_information_page_has_consent_and_no_microphone(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"voluntarily consent" in response.data
    assert b"Audio will not be recorded" in response.data
    assert response.headers["Permissions-Policy"] == "camera=(self), microphone=()"


def test_consent_is_required(client):
    assert client.get("/record").status_code == 302
    assert client.post("/consent", data={}).status_code == 400
    assert client.post("/upload").status_code == 403


def test_consent_opens_recording_page(client):
    response = consent(client)
    assert response.status_code == 302
    page = client.get(response.headers["Location"])
    assert page.status_code == 200
    assert b"Enable camera" in page.data
    assert b"show your open palm" in page.data
    assert b'id="movement-demo"' in page.data
    assert b"Example movement" in page.data


@patch("crowdcollect.app.requests.post")
def test_upload_forwards_video_to_telegram(mock_post, client):
    telegram_response = Mock()
    telegram_response.raise_for_status.return_value = None
    telegram_response.json.return_value = {"ok": True}
    mock_post.return_value = telegram_response
    consent(client)

    response = client.post(
        "/upload",
        data={"video": (BytesIO(b"video-data"), "session.webm", "video/webm")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json == {"ok": True}
    assert "/sendDocument" in mock_post.call_args.args[0]
    assert mock_post.call_args.kwargs["data"]["chat_id"] == "12345"
    assert client.get("/record").status_code == 302


def test_upload_rejects_non_video(client):
    consent(client)
    response = client.post(
        "/upload",
        data={"video": (BytesIO(b"text"), "notes.txt", "text/plain")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
