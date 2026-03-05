import logging
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    colors = {
        'TEXT': '\033[38;5;250m',  # Default text color
        'LEVEL': '\033[38;5;6m',   # Default level color
        'SOURCE': '\033[38;5;7m',  # Source (file/line) color
        'TIME': '\033[38;5;8m',    # Timestamp color
        'INFO': '\033[38;5;6m',    # Info level color (cyan)
        'DEBUG': '\033[38;5;4m',   # Debug level color (blue)
        'WARNING': '\033[38;5;214m',  # Warning level color (orange)
        'ERROR': '\033[38;5;196m',    # Error level color (red)
        'CRITICAL': '\033[38;5;5m'    # Critical level color (magenta)
    }

    def format(self, record):
        # Format the log message
        log_message = super().format(record)

        # Get the color for the log level
        level_color = self.colors.get(record.levelname, self.colors['TEXT'])

        # Return the formatted string with colors and additional context
        return (
            f'{level_color}{log_message} '  # Apply the color for the level
            f'{self.colors["LEVEL"]}[{record.levelname}] '  # Level name
            f'{self.colors["SOURCE"]}({record.name} | {record.module}.{record.funcName}:{record.lineno}) '  # Logger name, module, function, line
            f'{self.colors["TIME"]}{self.formatTime(record, self.datefmt)}\033[0m'  # Timestamp and reset color
        )


def get_daily_log_file_handler():
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file_name = fr'{logs_path}/log_output_{current_date}.txt'
    file_handler = logging.FileHandler(log_file_name, encoding='utf-8')  # Specify encoding here
    file_handler.setFormatter(formatter)
    return file_handler


logs_path = r'data/logs'
os.makedirs(logs_path, exist_ok=True)

# Setup for logging
formatter = ColoredFormatter(fmt='%(message)s', datefmt='%H:%M:%S')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)

# Initialize the first file handler
current_day = datetime.now().day
file_handler = get_daily_log_file_handler()
logger.addHandler(file_handler)
