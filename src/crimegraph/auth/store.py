"""User storage and management engine for CrimeGraph AI.

Maintains user accounts, password hashes, and roles.
Persists users to data/users.json, strictly isolated from data/synthetic_data.json.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from crimegraph.auth.models import User, UserCreate, UserRole
from crimegraph.auth.security import hash_password

logger = logging.getLogger("crimegraph.auth")


def get_default_users_path() -> Path:
    """Returns absolute path to users storage file."""
    env_path = os.environ.get("CRIMEGRAPH_USERS_PATH")
    if env_path:
        return Path(env_path).resolve()

    # Place in data directory next to manual_data.json
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        cand = cur / "data" / "users.json"
        if cand.parent.exists():
            return cand.resolve()
        cur = cur.parent

    src_root = Path(__file__).resolve().parent.parent.parent.parent
    return (src_root / "data" / "users.json").resolve()


class UserStore:
    """In-memory and file-backed user management store."""

    def __init__(self, filepath: Optional[Union[str, Path]] = None):
        self.filepath = Path(filepath).resolve() if filepath else get_default_users_path()
        self.users: Dict[str, User] = {}
        self.load_users()

    def _seed_defaults(self):
        """Seeds initial default accounts for CrimeGraph analysts and administrators."""
        admin_pw = os.environ.get("CRIMEGRAPH_ADMIN_PASSWORD", "admin@2026")
        analyst_pw = os.environ.get("CRIMEGRAPH_ANALYST_PASSWORD", "analyst@2026")

        default_users = [
            User(
                username="admin",
                hashed_password=hash_password(admin_pw),
                full_name="Chief Investigating Officer (Admin)",
                role=UserRole.ADMIN,
                is_active=True
            ),
            User(
                username="analyst",
                hashed_password=hash_password(analyst_pw),
                full_name="Senior Intelligence Analyst",
                role=UserRole.ANALYST,
                is_active=True
            ),
            User(
                username="investigator",
                hashed_password=hash_password(analyst_pw),
                full_name="Field Investigation Officer",
                role=UserRole.ANALYST,
                is_active=True
            )
        ]

        for u in default_users:
            if u.username not in self.users:
                self.users[u.username] = u

    def load_users(self):
        """Loads users from users.json, seeding defaults if missing."""
        self._seed_defaults()

        if self.filepath.exists() and self.filepath.stat().st_size > 0:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for u_data in data.get("users", []):
                    if isinstance(u_data, dict) and "username" in u_data:
                        self.users[u_data["username"]] = User(**u_data)
            except Exception as e:
                logger.error(f"Error loading users from {self.filepath}: {e}")

    def save_users(self):
        """Persists user accounts atomically to users.json."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "version": "1.0",
                "type": "CRIMEGRAPH_USERS",
                "user_count": len(self.users)
            },
            "users": [u.model_dump() for u in self.users.values()]
        }

        temp_file = self.filepath.parent / f".tmp_{self.filepath.name}.{os.getpid()}"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, self.filepath)
        except Exception as e:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            logger.error(f"Failed to persist users to {self.filepath}: {e}")

    def get_user(self, username: str) -> Optional[User]:
        """Retrieve user by username."""
        return self.users.get(username.lower().strip())

    def create_user(self, user_in: UserCreate) -> User:
        """Create and persist a new user account."""
        username = user_in.username.lower().strip()
        if username in self.users:
            raise ValueError(f"Username '{username}' already exists")

        new_user = User(
            username=username,
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name or username.title(),
            role=user_in.role,
            is_active=True
        )
        self.users[username] = new_user
        self.save_users()
        return new_user

    def list_users(self) -> List[User]:
        """List all registered users."""
        return list(self.users.values())
