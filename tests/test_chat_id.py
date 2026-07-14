from unittest.mock import Mock, patch

from crowdcollect.chat_id import get_chats


@patch("crowdcollect.chat_id.requests.get")
def test_get_chats_deduplicates_recent_updates(mock_get):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "ok": True,
        "result": [
            {"message": {"chat": {"id": 42, "first_name": "Ada"}}},
            {"message": {"chat": {"id": 42, "first_name": "Ada"}}},
            {"channel_post": {"chat": {"id": -1001, "title": "Research"}}},
        ],
    }
    mock_get.return_value = response

    chats = get_chats("token")

    assert [chat["id"] for chat in chats] == [42, -1001]
