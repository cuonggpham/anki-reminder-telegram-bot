from datetime import datetime

import pytest

from anki_reminder_bot.adapters.anki.official import AnkiSyncError, OfficialAnkiAdapter


class _FakeCollection:
    def __init__(self, required):
        self.required = required
        self.download_calls = []
        self.reopened = False

    def sync_login(self, email, password, endpoint):
        return type("Auth", (), {"endpoint": endpoint})()

    def sync_status(self, auth):
        return type("Status", (), {"new_endpoint": ""})()

    def sync_collection(self, auth, sync_media):
        return type("Response", (), {"new_endpoint": "", "required": self.required})()

    def close_for_full_sync(self):
        pass

    def full_upload_or_download(self, **kwargs):
        self.download_calls.append(kwargs)

    def reopen(self, after_full_sync):
        self.reopened = after_full_sync


def test_anki_adapter_refuses_full_upload():
    collection = _FakeCollection(required=4)
    adapter = OfficialAnkiAdapter("email", "password", "Asia/Ho_Chi_Minh")
    with pytest.raises(AnkiSyncError, match="full upload"):
        adapter._sync_collection(collection)
    assert collection.download_calls == []


def test_anki_adapter_downloads_full_sync_without_uploading():
    collection = _FakeCollection(required=3)
    adapter = OfficialAnkiAdapter("email", "password", "Asia/Ho_Chi_Minh")
    adapter._sync_collection(collection)
    assert len(collection.download_calls) == 1
    assert collection.download_calls[0]["server_usn"] is None
    assert collection.download_calls[0]["upload"] is False
    assert collection.reopened is True


def test_parent_deck_expands_to_subdecks():
    decks = ["English", "English::Beginner", "English::Advanced", "Japanese"]
    assert OfficialAnkiAdapter._expand_selected_decks(["English"], decks) == [
        "English",
        "English::Advanced",
        "English::Beginner",
    ]


def test_virtual_parent_deck_expands_to_subdecks():
    decks = ["Language::English::Beginner", "Language::English::Advanced"]
    assert OfficialAnkiAdapter._expand_selected_decks(["Language"], decks) == [
        "Language::English::Advanced",
        "Language::English::Beginner",
    ]


def test_virtual_parent_deck_is_valid_for_stats_queries():
    class _StatsCollection:
        def find_cards(self, _query):
            return []

    adapter = OfficialAnkiAdapter("email", "password", "Asia/Ho_Chi_Minh")
    stats = adapter._read_stats(
        _StatsCollection(),
        ["Language"],
        ["Language::English::Beginner", "Language::English::Advanced"],
        datetime.fromisoformat("2026-09-10T08:00:00+07:00"),
    )
    assert stats.deck_names == (
        "Language::English::Advanced",
        "Language::English::Beginner",
    )
