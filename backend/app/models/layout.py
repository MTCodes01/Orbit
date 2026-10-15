"""Layout topology SQLAlchemy model."""

import json
from datetime import datetime, timezone

from sqlalchemy import Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.engine import Base


class Layout(Base):
    __tablename__ = "layouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # JSON array of { device_id, x, y, width, height }
    layout_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def layout(self):
        return json.loads(self.layout_json)

    @layout.setter
    def layout(self, value):
        self.layout_json = json.dumps(value)


class PairingCode(Base):
    """Short-lived pairing code records."""
    __tablename__ = "pairing_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[bool] = mapped_column(default=False)
    # Pending pairing info from agent — stored as JSON
    agent_info_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    @property
    def agent_info(self):
        return json.loads(self.agent_info_json)

    @agent_info.setter
    def agent_info(self, value):
        self.agent_info_json = json.dumps(value)

    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at
