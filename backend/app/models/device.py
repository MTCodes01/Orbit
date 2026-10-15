"""Device SQLAlchemy model."""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Float, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.engine import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    friendly_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hostname: Mapped[str] = mapped_column(String(256), nullable=False)
    os_info: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    agent_version: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    screen_width: Mapped[int] = mapped_column(Integer, nullable=False, default=1920)
    screen_height: Mapped[int] = mapped_column(Integer, nullable=False, default=1080)

    # Stored as JSON string for flexibility
    capabilities_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Auth — device_secret is stored as a bcrypt hash, never plaintext
    device_secret_hash: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_paired: Mapped[bool] = mapped_column(Boolean, default=False)

    online: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Virtual layout position (logical desktop pixels)
    layout_x: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    layout_y: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Extra config stored as JSON
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    @property
    def capabilities(self):
        if self.capabilities_json:
            return json.loads(self.capabilities_json)
        return {}

    @capabilities.setter
    def capabilities(self, value):
        self.capabilities_json = json.dumps(value) if value else None

    def touch(self):
        self.last_seen_at = datetime.now(timezone.utc)
