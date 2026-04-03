import logging

class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[94m',
        'INFO': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'CRITICAL': '\033[95m',
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)

        log_format = f"{color}[%(levelname)s] %(asctime)s - %(name)s - %(message)s{self.RESET}"
        formatter = logging.Formatter(log_format, "%H:%M:%S")

        return formatter.format(record)