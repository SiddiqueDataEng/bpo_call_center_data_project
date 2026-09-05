"""Structured pipeline logger."""
import logging
import sys
from datetime import datetime, timezone


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter(
            "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def pipeline_log(stage: str, table: str, rows_in: int, rows_out: int,
                 dropped: int = 0, extra: str = "") -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(
        f"[{ts}] PIPELINE  stage={stage:<8}  table={table:<38} "
        f"in={rows_in:>6,}  out={rows_out:>6,}  dropped={dropped:>5,}"
        + (f"  {extra}" if extra else "")
    )
