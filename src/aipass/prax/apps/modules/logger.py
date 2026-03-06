"""Prax Logger - Minimal stub for AIPass public repo."""
import logging

_logger = logging.getLogger("aipass")
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.INFO)


class SystemLogger:
    """Minimal system logger matching Dev-Pass interface."""
    def info(self, msg, *args, **kwargs):
        _logger.info(msg, *args, **kwargs)
    def warning(self, msg, *args, **kwargs):
        _logger.warning(msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs):
        _logger.error(msg, *args, **kwargs)
    def debug(self, msg, *args, **kwargs):
        _logger.debug(msg, *args, **kwargs)


system_logger = SystemLogger()
