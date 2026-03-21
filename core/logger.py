"""
Logger centralizado.
Use assim em qualquer módulo:
    from core.logger import get_logger
    log = get_logger(__name__)
    log.info("mensagem")
"""

import logging
import sys
from pathlib import Path


def get_logger(name: str, cfg: dict = None) -> logging.Logger:
    logger = logging.getLogger(name)

    # Evita adicionar handlers duplicados se chamado várias vezes
    if logger.handlers:
        return logger

    level = logging.INFO
    log_to_file = False
    log_file = "durer.log"

    if cfg:
        log_cfg = cfg.get("logging", {})
        level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
        log_to_file = log_cfg.get("log_to_file", False)
        log_file = log_cfg.get("log_file", "durer.log")

    logger.setLevel(level)
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    # Handler pro terminal
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    # Handler pro arquivo (opcional)
    if log_to_file:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger
