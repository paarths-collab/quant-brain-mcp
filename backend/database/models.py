from sqlalchemy import (
    Column,
    String,
    Date,
    Float,
    DateTime,
    func,
    Index,
    CheckConstraint
)

from .connection import Base   # Import Base from connection.py


# =====================================================
# FRED DATA (TIME SERIES)
# =====================================================

class FredData(Base):
    """
    FRED time-series data.
    One row = one observation.
    """
    __tablename__ = "fred_data"

    series_id = Column(String(50), primary_key=True, nullable=False)
    date = Column(Date, primary_key=True, nullable=False)

    series_type = Column(String(30), nullable=False)
    value = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        # Fast lookups for charts & latest values
        Index("idx_fred_series_date_desc", "series_id", "date"),

        # Optional sanity check (safe)
        CheckConstraint(
            "series_id <> ''",
            name="ck_fred_series_id_not_empty"
        ),
    )

    def __repr__(self):
        return (
            f"<FredData(series_id='{self.series_id}', "
            f"date='{self.date}', value={self.value})>"
        )

    def to_dict(self):
        return {
            "series_id": self.series_id,
            "series_type": self.series_type,
            "date": self.date.isoformat(),
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# =====================================================
# FRED SERIES METADATA
# =====================================================

class FredSeriesMetadata(Base):
    """
    Metadata describing a FRED series.
    One row per series_id.
    """
    __tablename__ = "fred_series_metadata"

    series_id = Column(String(50), primary_key=True, nullable=False)
    series_type = Column(String(30), nullable=False)

    title = Column(String(200), nullable=True)
    frequency = Column(String(20), nullable=True)
    units = Column(String(100), nullable=True)

    last_updated = Column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    __table_args__ = (
        Index("idx_fred_metadata_series_type", "series_type"),
    )

    def __repr__(self):
        return (
            f"<FredSeriesMetadata(series_id='{self.series_id}', "
            f"title='{self.title}')>"
        )

    def to_dict(self):
        return {
            "series_id": self.series_id,
            "series_type": self.series_type,
            "title": self.title,
            "frequency": self.frequency,
            "units": self.units,
            "last_updated": self.last_updated.isoformat(),
        }
