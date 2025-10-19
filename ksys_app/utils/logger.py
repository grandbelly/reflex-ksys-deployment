"""
Centralized logging configuration for debugging
Provides file and function level logging with execution tracking
"""

import os
import sys
import logging
import logging.handlers
import functools
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import asyncio
import inspect

# Create logs directory structure
# Use /tmp/ksys_logs to avoid Reflex hot reload issues
LOG_DIR = Path("/tmp/ksys_logs") if os.path.exists("/tmp") else Path("logs")
LOG_DIR.mkdir(exist_ok=True, parents=True)

# Session-based log directory (one per app start)
SESSION_ID = datetime.now().strftime('%Y%m%d_%H%M%S')
SESSION_DIR = LOG_DIR / f"session_{SESSION_ID}"
SESSION_DIR.mkdir(exist_ok=True)

# Single log files per session
LOG_FILE = SESSION_DIR / "app.log"
ERROR_LOG_FILE = SESSION_DIR / "errors.log"
DEBUG_LOG_FILE = SESSION_DIR / "debug.log"

# Latest symlink for easy access
LATEST_LOG = LOG_DIR / "latest.log"
LATEST_ERROR_LOG = LOG_DIR / "latest_errors.log"

# Configure root logger
def setup_logging(level=logging.DEBUG):
    """Setup comprehensive logging configuration with better file management"""

    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | Line:%(lineno)-5d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    debug_formatter = logging.Formatter(
        '%(asctime)s | %(name)s.%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%H:%M:%S.%f'[:-3]
    )

    # Main log file with rotation (max 10MB, keep 5 backups)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)

    # Debug log file (only DEBUG level, rotates at 50MB)
    debug_handler = logging.handlers.RotatingFileHandler(
        DEBUG_LOG_FILE,
        maxBytes=50*1024*1024,  # 50MB
        backupCount=2,
        encoding='utf-8'
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG)  # Only DEBUG
    debug_handler.setFormatter(debug_formatter)

    # Error log file (errors only)
    error_handler = logging.FileHandler(ERROR_LOG_FILE, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)

    # Setup root logger
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(debug_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(console_handler)

    # Create symlinks to latest logs (Windows requires admin or developer mode)
    try:
        if LATEST_LOG.exists():
            LATEST_LOG.unlink()
        if LATEST_ERROR_LOG.exists():
            LATEST_ERROR_LOG.unlink()

        # For Windows, just copy instead of symlink
        if sys.platform == 'win32':
            with open(LOG_FILE, 'a') as f:
                f.write('')  # Touch file
            with open(ERROR_LOG_FILE, 'a') as f:
                f.write('')  # Touch file
        else:
            LATEST_LOG.symlink_to(LOG_FILE)
            LATEST_ERROR_LOG.symlink_to(ERROR_LOG_FILE)
    except Exception:
        pass  # Ignore symlink errors

    # Log startup
    root_logger.info("="*80)
    root_logger.info(f"SESSION STARTED - {SESSION_ID}")
    root_logger.info(f"Session directory: {SESSION_DIR}")
    root_logger.info(f"Main log: {LOG_FILE}")
    root_logger.info(f"Error log: {ERROR_LOG_FILE}")
    root_logger.info(f"Debug log: {DEBUG_LOG_FILE}")
    root_logger.info(f"Python: {sys.version.split()[0]}")
    root_logger.info(f"Platform: {sys.platform}")
    root_logger.info(f"Docker: {os.environ.get('DOCKER_CONTAINER', 'False')}")
    root_logger.info("="*80)

    return root_logger

# Get logger for module
def get_logger(name: str) -> logging.Logger:
    """Get logger for specific module"""
    logger = logging.getLogger(name)

    # Log module initialization
    logger.debug(f"Logger initialized for module: {name}")

    return logger

# Decorator for function logging
def log_function(func: Callable) -> Callable:
    """Decorator to log function entry, exit, and errors"""

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        func_name = f"{func.__module__}.{func.__name__}"

        # Log function entry (only in DEBUG mode)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"ENTER >>> {func_name}")
            if args or kwargs:
                logger.debug(f"  Args: {_safe_repr(args)}, Kwargs: {_safe_repr(kwargs)}")

        try:
            # Execute function
            result = func(*args, **kwargs)

            # Log successful exit (only in DEBUG mode)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"EXIT <<< {func_name} [SUCCESS]")
                if result is not None:
                    logger.debug(f"  Result: {_safe_repr(result)}")

            return result

        except Exception as e:
            # Log error with full traceback
            logger.error(f"ERROR in {func_name}: {str(e)}")
            logger.error(f"  Traceback:\n{traceback.format_exc()}")
            raise

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        func_name = f"{func.__module__}.{func.__name__}"

        # Log function entry (only in DEBUG mode)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"ASYNC ENTER >>> {func_name}")
            if args or kwargs:
                logger.debug(f"  Args: {_safe_repr(args)}, Kwargs: {_safe_repr(kwargs)}")

        try:
            # Execute async function
            result = await func(*args, **kwargs)

            # Log successful exit (only in DEBUG mode)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"ASYNC EXIT <<< {func_name} [SUCCESS]")
                if result is not None:
                    logger.debug(f"  Result: {_safe_repr(result)}")

            return result

        except Exception as e:
            # Log error with full traceback
            logger.error(f"ASYNC ERROR in {func_name}: {str(e)}")
            logger.error(f"  Traceback:\n{traceback.format_exc()}")
            raise

    # Return appropriate wrapper
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

def _safe_repr(obj: Any, max_len: int = 100) -> str:
    """Safe representation of objects for logging"""
    try:
        repr_str = repr(obj)
        if len(repr_str) > max_len:
            return repr_str[:max_len] + "..."
        return repr_str
    except:
        return f"<{type(obj).__name__} object>"

# Class decorator for automatic method logging
def log_class(cls):
    """Decorator to add logging to all methods in a class"""

    for name, method in inspect.getmembers(cls, inspect.isfunction):
        # Skip private methods and special methods
        if not name.startswith('_'):
            setattr(cls, name, log_function(method))

    # Log class initialization
    logger = logging.getLogger(cls.__module__)
    logger.debug(f"Class {cls.__name__} decorated with logging")

    return cls

# Context manager for operation logging
class LogOperation:
    """Context manager for logging operations"""

    def __init__(self, operation_name: str, logger: logging.Logger = None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger(__name__)
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"START OPERATION: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            self.logger.info(f"END OPERATION: {self.operation_name} [SUCCESS in {duration:.2f}s]")
        else:
            self.logger.error(f"END OPERATION: {self.operation_name} [FAILED in {duration:.2f}s]")
            self.logger.error(f"  Error: {exc_val}")
            self.logger.error(f"  Traceback:\n{traceback.format_tb(exc_tb)}")

        return False  # Don't suppress exception

# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()