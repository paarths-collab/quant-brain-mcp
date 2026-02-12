from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, tuple_

from .models import FredData, FredSeriesMetadata


class FredRepository:
    def __init__(self, db: Session):
        self.db = db

    # ===============================
    # DATA OPERATIONS
    # ===============================

    def upsert_metadata(
        self,
        series_id: str,
        series_type: str,
        title: Optional[str] = None,
        frequency: Optional[str] = None,
        units: Optional[str] = None
    ) -> FredSeriesMetadata:
        obj = (
            self.db.query(FredSeriesMetadata)
            .filter(FredSeriesMetadata.series_id == series_id)
            .one_or_none()
        )

        if obj:
            obj.series_type = series_type
            if title is not None:
                obj.title = title
            if frequency is not None:
                obj.frequency = frequency
            if units is not None:
                obj.units = units
        else:
            obj = FredSeriesMetadata(
                series_id=series_id,
                series_type=series_type,
                title=title,
                frequency=frequency,
                units=units
            )
            self.db.add(obj)

        return obj

    def upsert_data(
        self,
        series_id: str,
        series_type: str,
        date_val: date,
        value: float
    ) -> FredData:

        obj = (
            self.db.query(FredData)
            .filter(
                FredData.series_id == series_id,
                FredData.date == date_val
            )
            .one_or_none()
        )

        if obj:
            obj.value = value # type: ignore
            obj.series_type = series_type # type: ignore
        else:
            obj = FredData(
                series_id=series_id,
                series_type=series_type,
                date=date_val,
                value=value
            )
            self.db.add(obj)

        return obj

    def bulk_upsert(self, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0

        keys = {(r["series_id"], r["date"]) for r in rows}

        existing = {
            (d.series_id, d.date): d
            for d in (
                self.db.query(FredData)
                .filter(tuple_(FredData.series_id, FredData.date).in_(keys))
                .all()
            )
        }

        for r in rows:
            key = (r["series_id"], r["date"])
            if key in existing:
                existing[key].value = r["value"]
                existing[key].series_type = r["series_type"]
            else:
                self.db.add(FredData(**r))

        self.db.commit()
        return len(rows)

    def bulk_insert_from_dataframe(
        self,
        df: pd.Series,
        series_id: str,
        series_type: str
    ) -> int:

        rows = []
        for idx, val in df.items():
            if pd.notna(val):
                rows.append({
                    "series_id": series_id,
                    "series_type": series_type,
                    "date": idx.date() if hasattr(idx, "date") else idx, # pyright: ignore[reportAttributeAccessIssue]
                    "value": float(val)
                })

        return self.bulk_upsert(rows)

    # ===============================
    # QUERY OPERATIONS
    # ===============================

    def get_latest(self, series_id: str) -> Optional[FredData]:
        return (
            self.db.query(FredData)
            .filter(FredData.series_id == series_id)
            .order_by(FredData.date.desc())
            .first()
        )

    def get_multiple_series_latest(
        self,
        series_ids: List[str]
    ) -> Dict[str, FredData]:

        subq = (
            self.db.query(
                FredData.series_id,
                func.max(FredData.date).label("max_date")
            )
            .filter(FredData.series_id.in_(series_ids))
            .group_by(FredData.series_id)
            .subquery()
        )

        rows = (
            self.db.query(FredData)
            .join(
                subq,
                and_(
                    FredData.series_id == subq.c.series_id,
                    FredData.date == subq.c.max_date
                )
            )
            .all()
        )

        return {r.series_id: r for r in rows} # type: ignore

    # ===============================
    # ANALYTICS
    # ===============================

    def get_statistics(
        self,
        series_id: str,
        days: int = 252
    ) -> Dict[str, Any]:

        start = date.today() - timedelta(days=days)

        stats = (
            self.db.query(
                func.count(FredData.value),
                func.min(FredData.value),
                func.max(FredData.value),
                func.avg(FredData.value)
            )
            .filter(
                FredData.series_id == series_id,
                FredData.date >= start
            )
            .one_or_none()
        )

        if not stats or stats[0] == 0:
            return {}

        latest = self.get_latest(series_id)
        oldest = (
            self.db.query(FredData)
            .filter(
                FredData.series_id == series_id,
                FredData.date >= start
            )
            .order_by(FredData.date.asc())
            .first()
        )

        if not latest or not oldest or not oldest.value: # type: ignore
            return {}

        return {
            "series_id": series_id,
            "count": stats[0],
            "min": stats[1],
            "max": stats[2],
            "mean": float(stats[3]) if stats[3] is not None else None,
            "latest": latest.value,
            "oldest": oldest.value,
            "change_pct": ((latest.value - oldest.value) / oldest.value) * 100
        }
