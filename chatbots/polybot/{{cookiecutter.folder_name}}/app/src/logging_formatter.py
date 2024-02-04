import logging


class ConsoleFormatter(logging.Formatter):
    def __init__(self, format):
        """
        Console formatter to format console output.
        """
        self.colors = {
            "DEBUG": "\033[38;20mDEBUG" + "\033[0m:" + " " * (9 - len("DEBUG")),
            "INFO": "\033[94mINFO" + "\033[0m:" + " " * (9 - len("INFO")),
            "WARNING": "\033[33;20m"
            + "WARNING"
            + "\033[0m:"
            + " " * (9 - len("WARNING")),
            "ERROR": "\033[31;20m" + "ERROR" + "\033[0m:" + " " * (9 - len("ERROR")),
            "CRITICAL": "\033[31;1m"
            + "CRITICAL"
            + "\033[0m:"
            + " " * (9 - len("CRITICAL")),
            "ENDCOLOR": "\033[0m",
        }

        self._format = format

        self.formats = {
            logging.DEBUG: self.colors["DEBUG"]
            + self._format
            + self.colors["ENDCOLOR"],
            logging.INFO: self.colors["INFO"] + self._format + self.colors["ENDCOLOR"],
            logging.WARNING: self.colors["WARNING"]
            + self._format
            + self.colors["ENDCOLOR"],
            logging.ERROR: self.colors["ERROR"]
            + self._format
            + self.colors["ENDCOLOR"],
            logging.CRITICAL: self.colors["CRITICAL"]
            + self._format
            + self.colors["ENDCOLOR"],
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the given log record.

        Args:
            record (logging.LogRecord): Log record.

        Returns:
            str: Formatted log record.
        """
        log_format = self.formats.get(record.levelno)
        formatter = logging.Formatter(log_format)
        return formatter.format(record)
