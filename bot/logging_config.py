import logging
import os
from datetime import datetime


def setup_logger(name: str = "trading_bot") -> logging.Logger:
    logger = logging.getLogger(name)

    # Don't add handlers if already configured (avoids duplicate logs)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_file = os.path.join(logs_dir, f"trading_{datetime.now().strftime('%Y%m%d')}.log")

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)-18s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File gets everything DEBUG and above
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console only shows INFO+ to stay readable
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
