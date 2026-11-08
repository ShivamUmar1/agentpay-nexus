from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from api.database import Base


class RateLimitRecord(Base):
    __tablename__ = "rate_limits"

    key = Column(String(255), primary_key=True, index=True)
    count = Column(Integer, default=1, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
