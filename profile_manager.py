import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any
import secrets
import hashlib


class ProfileManager:
    """
    Lightweight profile backend that stores login credentials and editable
    profile data (username, email, avatar, timezone, bio, etc.) in the
    existing tasks.db SQLite database.

    Passwords are never stored in plain text. Instead, PBKDF2-HMAC is used
    with a per-user random salt.
    """

    def __init__(self, db_path: str = "tasks.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._ensure_table()
        self._ensure_profile_row()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Create the user_profile table if it does not yet exist."""
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password_hash TEXT,
                password_salt TEXT,
                avatar_path TEXT,
                timezone TEXT,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self.conn.commit()

    def _ensure_profile_row(self) -> None:
        """Seed the table with a single default profile row if empty."""
        cursor = self.conn.execute("SELECT COUNT(*) AS count FROM user_profile")
        count = cursor.fetchone()["count"]
        if count == 0:
            self.conn.execute(
                """
                INSERT INTO user_profile (id, username, email, avatar_path, timezone, bio)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    1,
                    "Time Manager",
                    "user@example.com",
                    "profile.jpg",
                    "UTC",
                    "Stay focused and accomplish more!",
                ),
            )
            self.conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> Dict[str, str]:
        """Create a salted PBKDF2 hash for the supplied password."""
        if salt is None:
            salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            200_000,
        )
        return {"salt": salt, "hash": hashed.hex()}

    @staticmethod
    def _verify_password(password: str, salt: str, stored_hash: str) -> bool:
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            200_000,
        ).hex()
        return secrets.compare_digest(candidate, stored_hash)

    def _touch_updated_at(self) -> None:
        self.conn.execute(
            """
            UPDATE user_profile
            SET updated_at = ?
            WHERE id = 1
            """,
            (datetime.utcnow(),),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_profile(self) -> Dict[str, Any]:
        """Return non-sensitive profile data for UI consumption."""
        cursor = self.conn.execute("SELECT * FROM user_profile WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Profile row is missing.")

        return {
            "username": row["username"],
            "email": row["email"],
            "avatar_path": row["avatar_path"],
            "timezone": row["timezone"],
            "bio": row["bio"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def update_profile(
        self,
        *,
        username: Optional[str] = None,
        email: Optional[str] = None,
        avatar_path: Optional[str] = None,
        timezone: Optional[str] = None,
        bio: Optional[str] = None,
    ) -> None:
        """Update profile fields that were provided."""
        updates = []
        params = []

        if username is not None:
            updates.append("username = ?")
            params.append(username.strip())
        if email is not None:
            updates.append("email = ?")
            params.append(email.strip().lower())
        if avatar_path is not None:
            updates.append("avatar_path = ?")
            params.append(avatar_path.strip())
        if timezone is not None:
            updates.append("timezone = ?")
            params.append(timezone.strip())
        if bio is not None:
            updates.append("bio = ?")
            params.append(bio.strip())

        if not updates:
            return

        params.append(1)  # WHERE id = 1
        query = f"""
            UPDATE user_profile
            SET {", ".join(updates)}
            WHERE id = ?
        """
        self.conn.execute(query, params)
        self._touch_updated_at()
        self.conn.commit()

    def set_password(self, password: str) -> None:
        """Hash and store a new password."""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        salted = self._hash_password(password)
        self.conn.execute(
            """
            UPDATE user_profile
            SET password_hash = ?, password_salt = ?
            WHERE id = 1
            """,
            (salted["hash"], salted["salt"]),
        )
        self._touch_updated_at()
        self.conn.commit()

    def authenticate(self, identifier: str, password: str) -> bool:
        """
        Validate login credentials. `identifier` can be either username or email.
        Returns True if credentials match, False otherwise.
        """
        cursor = self.conn.execute(
            """
            SELECT password_hash, password_salt
            FROM user_profile
            WHERE (LOWER(username) = LOWER(?)) OR (LOWER(email) = LOWER(?))
            """,
            (identifier, identifier),
        )
        row = cursor.fetchone()
        if not row or not row["password_hash"] or not row["password_salt"]:
            return False
        return self._verify_password(password, row["password_salt"], row["password_hash"])

    def close(self) -> None:
        """Close the SQLite connection."""
        self.conn.close()


__all__ = ["ProfileManager"]

