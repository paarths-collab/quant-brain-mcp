import argparse
import logging
import os
import socket
import time
from pathlib import Path

from dotenv import load_dotenv

def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = str(raw).strip()
    if not raw:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = str(raw).strip()
    if not raw:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _get_markets_from_env() -> list[str]:
    raw = os.getenv("SECTOR_INTEL_MARKETS", "US,IN")
    markets = [m.strip().upper() for m in str(raw).split(",") if m.strip()]
    return markets or ["US", "IN"]


def _load_env():
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)


def run_once(markets=None, force: bool = False, sectors=None, max_sectors: int = 0):
    from backend.database.connection import get_db_session, init_db, check_db_connection
    from backend.services.sector_intel_service import refresh_all_sectors

    logging.getLogger(__name__).info("sector_intel_worker init_db")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./boomerang.db")
    logging.getLogger(__name__).info("sector_intel_worker database_url=%s", database_url)
    if not check_db_connection():
        if "://boomerang:boomerang_secret@localhost:" in database_url or "://localhost:" in database_url:
            logging.getLogger(__name__).error(
                "Tip: on some Windows/Docker setups, `localhost` resolves to IPv6 (`::1`) and the port mapping may not accept it. "
                "Try setting DATABASE_URL host to `127.0.0.1`."
            )
        logging.getLogger(__name__).error(
            "sector_intel_worker cannot connect to DATABASE_URL. "
            "Start Postgres (`cd backend; docker-compose up -d`) or set DATABASE_URL to SQLite (e.g. `sqlite:///./boomerang.db`)."
        )
        raise SystemExit(2)
    init_db()
    with get_db_session() as db:
        return refresh_all_sectors(db, markets=markets, force=force, sectors=sectors, max_sectors=max_sectors)


def run_loop(
    markets=None,
    force: bool = False,
    interval_minutes: int = 60,
    sectors=None,
    max_sectors: int = 0,
):
    while True:
        run_once(markets=markets, force=force, sectors=sectors, max_sectors=max_sectors)
        time.sleep(max(1, interval_minutes) * 60)


def main():
    parser = argparse.ArgumentParser(description="Sector intelligence background worker")
    parser.add_argument("--once", action="store_true", help="Run a single refresh cycle and exit")
    parser.add_argument("--loop", action="store_true", help="Run continuously (default if --once is not set)")
    parser.add_argument("--force", action="store_true", help="Force refresh even if snapshots are fresh")
    parser.add_argument("--markets", type=str, default="", help="Comma-separated list of markets (US,IN)")
    parser.add_argument("--sectors", type=str, default="", help="Comma-separated list of sectors to refresh")
    parser.add_argument("--max-sectors", type=int, default=0, help="Limit number of sectors per market (0 = all)")
    parser.add_argument("--interval-minutes", type=int, default=None, help="Loop interval (default from env)")
    parser.add_argument("--log-level", type=str, default="", help="Log level (default from env)")
    parser.add_argument(
        "--socket-timeout-seconds",
        type=float,
        default=None,
        help="Optional default socket timeout for network calls (0 = disabled)",
    )
    args = parser.parse_args()

    _load_env()

    log_level_raw = (args.log_level or os.getenv("SECTOR_INTEL_LOG_LEVEL") or "INFO").strip()
    log_level = getattr(logging, log_level_raw.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    markets = [market_code.strip().upper() for market_code in args.markets.split(",") if market_code.strip()] or _get_markets_from_env()
    sectors = [sector_name.strip() for sector_name in args.sectors.split(",") if sector_name.strip()] or None
    interval_minutes = args.interval_minutes if args.interval_minutes is not None else _int_env("SECTOR_INTEL_REFRESH_MINUTES", 60)
    socket_timeout_seconds = (
        float(args.socket_timeout_seconds)
        if args.socket_timeout_seconds is not None
        else _float_env("SECTOR_INTEL_SOCKET_TIMEOUT_SECONDS", 0.0)
    )

    logging.getLogger(__name__).info(
        "sector_intel_worker start once=%s force=%s markets=%s sectors=%s max_sectors=%s interval_minutes=%s",
        args.once,
        args.force,
        markets,
        sectors,
        args.max_sectors,
        interval_minutes,
    )

    if socket_timeout_seconds and socket_timeout_seconds > 0:
        socket.setdefaulttimeout(socket_timeout_seconds)
        logging.getLogger(__name__).info("sector_intel_worker socket_default_timeout_seconds=%s", socket_timeout_seconds)

    if args.once:
        result = run_once(markets=markets, force=args.force, sectors=sectors, max_sectors=args.max_sectors)
        logging.getLogger(__name__).info("sector_intel_worker done status=%s", (result or {}).get("status"))
    else:
        run_loop(
            markets=markets,
            force=args.force,
            interval_minutes=interval_minutes,
            sectors=sectors,
            max_sectors=args.max_sectors,
        )


if __name__ == "__main__":
    main()
