import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    colors = {
        'TEXT': '\033[38;5;250m',
        'LEVEL': '\033[38;5;6m',
        'SOURCE': '\033[38;5;7m',
        'TIME': '\033[38;5;8m',
        'INFO': '\033[38;5;6m',
        'DEBUG': '\033[38;5;4m',
        'WARNING': '\033[38;5;3m',
        'ERROR': '\033[38;5;1m',
        'CRITICAL': '\033[38;5;5m'
    }

    def format(self, record):
        log_message = super().format(record)
        return (
            f'{self.colors["TEXT"]}{log_message} '
            f'{self.colors["LEVEL"]}[{record.levelname}] '
            f'{self.colors["SOURCE"]}({record.filename}:{record.lineno}) '
            f'{self.colors["TIME"]}{self.formatTime(record, self.datefmt)}\033[0m'
        )


# Plain formatter for file logging (no color codes)
plain_formatter = logging.Formatter(
    fmt='%(message)s [%(levelname)s] (%(filename)s:%(lineno)d) %(asctime)s',
    datefmt='%H:%M:%S'
)


def get_rotating_log_file_handler():
    # Set the base log file name (without .txt, it will be added in the suffix)
    log_file_name = fr'{logs_path}/log'

    # TimedRotatingFileHandler rotates the log every midnight and keeps up to 7 backups
    file_handler = TimedRotatingFileHandler(
        log_file_name,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding='utf-8',
        utc=False
    )

    # This ensures the filename includes the date and .txt extension during rotation
    file_handler.suffix = "%Y-%m-%d.txt"

    # Assign plain formatter to file handler
    file_handler.setFormatter(plain_formatter)

    return file_handler


logs_path = r'data/logs'
os.makedirs(logs_path, exist_ok=True)

# Setup for logging
colored_formatter = ColoredFormatter(fmt='%(message)s', datefmt='%H:%M:%S')

# Console handler (with colored output)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(colored_formatter)

# File handler (with log rotation)
file_handler = get_rotating_log_file_handler()

# Logger configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)  # Console logging
logger.addHandler(file_handler)  # File logging with rotation

# Example log messages
logger.info(f'Time: {datetime.now()}')
