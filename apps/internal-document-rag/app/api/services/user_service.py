from __future__ import annotations

import json
from typing import Any

from app.api.schemas.users import UserProfileSchema
from app.config import settings


class UserService:
    """Service handling user accounts, roles, API keys, and profile data."""

    def get_current_user_profile(self) -> UserProfileSchema:
        """Return authenticated user profile data."""
        return UserProfileSchema(
            id="usr-1",
            username="admin",
            email=None,
            role="System Administrator",
            avatar_letter="A",
            created_at="2026-01-15T08:30:00Z",
        )

    def get_users_list(self) -> list[dict[str, Any]]:
        """Parse static configured user credentials AND newly registered users from registered_users.json."""
        users: list[dict[str, Any]] = []
        user_names_seen: set[str] = set()

        # 1. Parse static credentials configured in settings.user_credentials
        raw_creds = getattr(settings, "user_credentials", "admin:admin123,user:user123")
        if raw_creds:
            pairs = raw_creds.split(",")
            for pair in pairs:
                parts = pair.split(":")
                if len(parts) >= 2:
                    uname = parts[0].strip()
                    email = parts[2].strip() if len(parts) >= 3 else None
                    if uname and uname.lower() not in user_names_seen:
                        user_names_seen.add(uname.lower())
                        users.append(
                            {
                                "id": len(users) + 1,
                                "name": uname,
                                "email": email,
                                "role": (
                                    "System Administrator"
                                    if uname.lower() == "admin"
                                    else "User"
                                ),
                                "status": "Active",
                            }
                        )

        # 2. Parse newly registered users saved to data/registered_users.json during Streamlit sign-up
        reg_file = settings.data_dir / "registered_users.json"
        if reg_file.exists():
            try:
                with open(reg_file, "r", encoding="utf-8") as f:
                    reg_dict = json.load(f)
                if isinstance(reg_dict, dict):
                    for uname in reg_dict:
                        if uname and uname.strip().lower() not in user_names_seen:
                            user_names_seen.add(uname.strip().lower())
                            users.append(
                                {
                                    "id": len(users) + 1,
                                    "name": uname.strip(),
                                    "email": None,
                                    "role": "User",
                                    "status": "Active",
                                }
                            )
            except Exception:
                pass

        return users

    def get_roles_list(self) -> list[dict[str, Any]]:
        """Return list of role configurations."""
        return [
            {
                "name": "System Administrator",
                "usersCount": 1,
                "permissions": [
                    "All Settings",
                    "Read/Write Docs",
                    "View Analytics",
                    "Manage Users",
                ],
            },
            {
                "name": "User",
                "usersCount": 1,
                "permissions": ["Read/Write Docs", "View Analytics"],
            },
        ]

    def get_api_keys(self) -> list[dict[str, Any]]:
        """Return list of generated API keys."""
        return []
