"""
Unit tests for FileStorage (app.models.storage).

Tests profile, test drive, and session CRUD operations
using tmp_path to avoid polluting real storage.
"""

import json

import pytest

from app.models.schemas import UserProfile
from app.models.storage import FileStorage


class TestProfileStorage:
    def test_save_and_load_profile(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)
        profile = UserProfile(phone_number="13800000001", name="Alice", age="25")
        FileStorage.save_profile("13800000001", profile)

        loaded = FileStorage.load_profile("13800000001")
        assert loaded is not None
        assert loaded.name == "Alice"
        assert loaded.age == "25"
        assert loaded.phone_number == "13800000001"

    def test_load_profile_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)
        assert FileStorage.load_profile("nonexistent") is None

    def test_load_profile_corrupt_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("not valid json", encoding="utf-8")
        assert FileStorage.load_profile("corrupt") is None

    def test_list_profiles(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        FileStorage.save_profile("111", UserProfile(phone_number="111"))
        FileStorage.save_profile("222", UserProfile(phone_number="222"))

        profiles = FileStorage.list_profiles()
        assert sorted(profiles) == ["111", "222"]

    def test_delete_profile(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)

        FileStorage.save_profile("333", UserProfile(phone_number="333"))
        assert FileStorage.delete_profile("333") is True
        assert FileStorage.load_profile("333") is None

    def test_delete_profile_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.PROFILES_DIR", tmp_path)
        assert FileStorage.delete_profile("nonexistent") is False


class TestTestDriveStorage:
    def test_save_and_load_test_drive(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)
        data = {
            "phone_number": "14000000001",
            "reservation": {"test_driver": "Bob", "reservation_date": "2024-06-01"},
            "car_model": "Tesla-Model Y",
        }
        FileStorage.save_test_drive("14000000001", data)

        loaded = FileStorage.load_test_drive("14000000001")
        assert loaded is not None
        assert loaded["car_model"] == "Tesla-Model Y"
        assert loaded["reservation"]["test_driver"] == "Bob"

    def test_load_test_drive_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)
        assert FileStorage.load_test_drive("nonexistent") is None

    def test_list_test_drives(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        FileStorage.save_test_drive("aaa", {"phone_number": "aaa"})
        FileStorage.save_test_drive("bbb", {"phone_number": "bbb"})

        drives = FileStorage.list_test_drives()
        assert sorted(drives) == ["aaa", "bbb"]

    def test_delete_test_drive(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)

        FileStorage.save_test_drive("ccc", {"phone_number": "ccc"})
        assert FileStorage.delete_test_drive("ccc") is True
        assert FileStorage.load_test_drive("ccc") is None

    def test_delete_test_drive_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.TEST_DRIVES_DIR", tmp_path)
        assert FileStorage.delete_test_drive("nonexistent") is False


class TestSessionStorage:
    def test_save_and_load_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.SESSIONS_DIR", tmp_path)
        data = {"session_id": "sess-001", "stage": "welcome"}
        FileStorage.save_session("sess-001", data)

        loaded = FileStorage.load_session("sess-001")
        assert loaded is not None
        assert loaded["stage"] == "welcome"

    def test_load_session_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.SESSIONS_DIR", tmp_path)
        assert FileStorage.load_session("nonexistent") is None

    def test_delete_session(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.SESSIONS_DIR", tmp_path)

        FileStorage.save_session("sess-002", {"session_id": "sess-002"})
        assert FileStorage.delete_session("sess-002") is True
        assert FileStorage.load_session("sess-002") is None

    def test_delete_session_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("app.models.storage.SESSIONS_DIR", tmp_path)
        assert FileStorage.delete_session("nonexistent") is False
