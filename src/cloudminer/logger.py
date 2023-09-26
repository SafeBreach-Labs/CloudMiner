import sys
import logging

INDENT_CHAR = "\t"

class CloudMinerLogger(logging.Logger):
    """
    The main program logger
    """
    def __init__(self, name: str, level: int = 0) -> None:
        super().__init__(name, level)
        self.indent = 0

    def _log(self, level, msg, *args, **kwargs) -> None:
        if level == logging.INFO:
            bullet = '[+]'
        elif level == logging.DEBUG:
            bullet = '[*]'
        elif level == logging.ERROR or level == logging.WARNING:
            bullet = '[!]'
        elif level == 100: #header
            bullet = '[#]'
        else:
            bullet = '[~]'

        msg = f"{INDENT_CHAR*self.indent}{bullet} {msg}"
        return super()._log(level, msg, *args, **kwargs)

    def add_indent(self):
        self.indent += 1

    def remove_indent(self):
        self.indent -= 1
    

class LoggerIndent():
    """
    Class to adjust indentation of the logger
    """
    def __init__(self, logger: CloudMinerLogger) -> None:
        self.logger = logger

    def __enter__(self):
        self.logger.add_indent()

    def __exit__(self, exc_type, exc_value, traceback):
        self.logger.remove_indent()


def init_logger() -> CloudMinerLogger:
    logger = CloudMinerLogger("root")
    handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(handler)
    return logger

logger = init_logger()