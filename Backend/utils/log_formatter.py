import logging
import sys
import os

# ANSI color codes
RESET = "\033[0m"
COLORS = {
    'DEBUG': '\033[36m',    # Cyan
    'INFO': '\033[32m',     # Green
    'WARNING': '\033[33m',  # Yellow
    'ERROR': '\033[31m',    # Red
    'CRITICAL': '\033[41m', # Red background
    'TIMESTAMP': '\033[37m', # White/Grey
    'LOGGER': '\033[37m',   # White/Grey
}

class ColoredFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt=None, style='%', use_color=True):
        super().__init__(fmt, datefmt, style)
        self.use_color = use_color and self._supports_color()

    def format(self, record):
        levelname = record.levelname
        msg = super().format(record)
        if self.use_color and levelname in COLORS:
            color = COLORS[levelname]
            msg = f"{color}{msg}{RESET}"
        return msg

    def _supports_color(self):
        # Force color if configured in config.yml
        try:
            from config_loader import get_config
            if get_config().get("app", {}).get("force_color"):
                return True
        except Exception:
            # If config not available, fall through to other checks
            pass

        # Check TERM for color support
        term = os.getenv('TERM', '')
        if term in ('xterm', 'xterm-256color', 'screen', 'screen-256color'):
            return True
        # On Linux, allow color unless explicitly dumb
        if sys.platform != 'win32':
            if term and term != 'dumb':
                return True
        # Windows checks
        if sys.platform == 'win32':
            return os.getenv('ANSICON') is not None or 'WT_SESSION' in os.environ
        # Fallback to isatty
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    def formatTime(self, record, datefmt=None):
        s = super().formatTime(record, datefmt)
        if self.use_color:
            s = f"{COLORS['TIMESTAMP']}{s}{RESET}"
        return s

    def formatName(self, record):
        name = record.name
        if self.use_color:
            name = f"{COLORS['LOGGER']}{name}{RESET}"
        return name
