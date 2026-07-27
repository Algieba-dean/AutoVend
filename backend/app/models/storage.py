"""
File-based storage for profiles, sessions, and test drive reservations.

Uses JSON files for persistence, compatible with the existing system's
storage approach but with cleaner interfaces.
"""

import hashlib
import json
import logging
import uuid
from typing import Dict, List, Optional

from backend.app.config import PROFILES_DIR, SESSIONS_DIR, TEST_DRIVES_DIR
from backend.app.models.schemas import UserProfile

logger = logging.getLogger(__name__)


class FileStorage:
    """File-based JSON storage with typed accessors."""

    # --- Profiles ---

    @staticmethod
    def save_profile(phone_number: str, profile: UserProfile) -> None:
        """Save a user profile to disk."""
        path = PROFILES_DIR / f"{phone_number}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        logger.debug(f"Profile saved: {phone_number}")

    @staticmethod
    def load_profile(phone_number: str) -> Optional[UserProfile]:
        """Load a user profile from disk."""
        path = PROFILES_DIR / f"{phone_number}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return UserProfile(**data)
        except Exception as e:
            logger.warning(f"Failed to load profile {phone_number}: {e}")
            return None

    @staticmethod
    def list_profiles() -> List[str]:
        """List all stored profile phone numbers."""
        return [p.stem for p in PROFILES_DIR.glob("*.json")]

    @staticmethod
    def delete_profile(phone_number: str) -> bool:
        """Delete a profile. Returns True if deleted."""
        path = PROFILES_DIR / f"{phone_number}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # --- Test Drives ---

    @staticmethod
    def save_test_drive(phone_number: str, data: Dict) -> None:
        """Save a test drive reservation."""
        path = TEST_DRIVES_DIR / f"{phone_number}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.debug(f"Test drive saved: {phone_number}")

    @staticmethod
    def load_test_drive(phone_number: str) -> Optional[Dict]:
        """Load a test drive reservation."""
        path = TEST_DRIVES_DIR / f"{phone_number}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load test drive {phone_number}: {e}")
            return None

    @staticmethod
    def list_test_drives() -> List[str]:
        """List all stored test drive phone numbers."""
        return [p.stem for p in TEST_DRIVES_DIR.glob("*.json")]

    @staticmethod
    def delete_test_drive(phone_number: str) -> bool:
        """Delete a test drive. Returns True if deleted."""
        path = TEST_DRIVES_DIR / f"{phone_number}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # --- Sessions ---

    @staticmethod
    def _session_path(session_id: str):
        """Map an untrusted public session id to a safe, fixed-width filename."""
        digest = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return SESSIONS_DIR / f"{digest}.json"

    @staticmethod
    def save_session(session_id: str, data: Dict) -> None:
        """Atomically save session state."""
        path = FileStorage._session_path(session_id)
        temporary = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def load_session(session_id: str) -> Optional[Dict]:
        """Load session state."""
        path = FileStorage._session_path(session_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return None

    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete session state."""
        path = FileStorage._session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
