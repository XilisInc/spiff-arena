"""Logging_service."""
import json
import logging
import re
import sys
from typing import Any
from typing import Optional

from flask.app import Flask


# flask logging formats:
#   from: https://www.askpython.com/python-modules/flask/flask-logging
# %(asctime)s— The timestamp as a string.
# %(levelname)s—The logging level as a string.
# %(name)s—The logger name as a string.
# %(threadname)s—The thread name as a string.
# %(message)s—The log message.

# full message list:
# {'name': 'gunicorn.error', 'msg': 'GET /admin/token', 'args': (), 'levelname': 'DEBUG', 'levelno': 10, 'pathname': '~/.cache/pypoetry/virtualenvs/spiffworkflow-backend-R_hdWfN1-py3.10/lib/python3.10/site-packages/gunicorn/glogging.py', 'filename': 'glogging.py', 'module': 'glogging', 'exc_info': None, 'exc_text': None, 'stack_info': None, 'lineno': 267, 'funcName': 'debug', 'created': 1657307111.4513023, 'msecs': 451.30228996276855, 'relativeCreated': 1730.785846710205, 'thread': 139945864087360, 'threadName': 'MainThread', 'processName': 'MainProcess', 'process': 2109561, 'message': 'GET /admin/token', 'asctime': '2022-07-08T15:05:11.451Z'}


class InvalidLogLevelError(Exception):
    """InvalidLogLevelError."""


# originally from https://stackoverflow.com/a/70223539/6090676


class JsonFormatter(logging.Formatter):
    """Formatter that outputs JSON strings after parsing the LogRecord.

    @param dict fmt_dict: Key: logging format attribute pairs. Defaults to {"message": "message"}.
    @param str time_format: time.strftime() format string. Default: "%Y-%m-%dT%H:%M:%S"
    @param str msec_format: Microsecond formatting. Appended at the end. Default: "%s.%03dZ"
    """

    def __init__(
        self,
        fmt_dict: Optional[dict] = None,
        time_format: str = "%Y-%m-%dT%H:%M:%S",
        msec_format: str = "%s.%03dZ",
    ):
        """__init__."""
        self.fmt_dict = fmt_dict if fmt_dict is not None else {"message": "message"}
        self.default_time_format = time_format
        self.default_msec_format = msec_format
        self.datefmt = None

    def usesTime(self) -> bool:
        """Overwritten to look for the attribute in the format dict values instead of the fmt string."""
        return "asctime" in self.fmt_dict.values()

    # we are overriding a method that returns a string and returning a dict, hence the Any
    def formatMessage(self, record: logging.LogRecord) -> Any:
        """Overwritten to return a dictionary of the relevant LogRecord attributes instead of a string.

        KeyError is raised if an unknown attribute is provided in the fmt_dict.
        """
        return {fmt_key: record.__dict__[fmt_val] for fmt_key, fmt_val in self.fmt_dict.items()}

    def format(self, record: logging.LogRecord) -> str:
        """Mostly the same as the parent's class method.

        The difference being that a dict is manipulated and dumped as JSON instead of a string.
        """
        record.message = record.getMessage()

        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        message_dict = self.formatMessage(record)

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)

        if record.exc_text:
            message_dict["exc_info"] = record.exc_text

        if record.stack_info:
            message_dict["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(message_dict, default=str)


def setup_logger(app: Flask) -> None:
    """Setup_logger."""
    upper_log_level_string = app.config["SPIFFWORKFLOW_BACKEND_LOG_LEVEL"].upper()
    log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    if upper_log_level_string not in log_levels:
        raise InvalidLogLevelError(
            f"Log level given is invalid: '{upper_log_level_string}'. Valid options are {log_levels}"
        )

    log_level = getattr(logging, upper_log_level_string)
    spiff_log_level = getattr(logging, upper_log_level_string)
    log_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    app.logger.debug("Printing log to create app logger")

    # the json formatter is nice for real environments but makes
    # debugging locally a little more difficult
    if app.config["ENV_IDENTIFIER"] != "local_development":
        json_formatter = JsonFormatter(
            {
                "level": "levelname",
                "message": "message",
                "loggerName": "name",
                "processName": "processName",
                "processID": "process",
                "threadName": "threadName",
                "threadID": "thread",
                "timestamp": "asctime",
            }
        )
        log_formatter = json_formatter

    spiff_logger_filehandler = None
    if app.config["SPIFFWORKFLOW_BACKEND_LOG_TO_FILE"]:
        spiff_logger_filehandler = logging.FileHandler(
            f"{app.instance_path}/../../log/{app.config['ENV_IDENTIFIER']}.log"
        )
        spiff_logger_filehandler.setLevel(spiff_log_level)
        spiff_logger_filehandler.setFormatter(log_formatter)

    # these loggers have been deemed too verbose to be useful
    garbage_loggers_to_exclude = ["connexion", "flask_cors.extension"]

    # make all loggers act the same
    for name in logging.root.manager.loggerDict:
        # use a regex so spiffworkflow_backend isn't filtered out
        if not re.match(r"^spiff\b", name):
            the_logger = logging.getLogger(name)
            the_logger.setLevel(log_level)
            if spiff_logger_filehandler:
                the_logger.handlers = []
                the_logger.propagate = False
                the_logger.addHandler(spiff_logger_filehandler)
            else:
                # it's very verbose, so only add handlers for the obscure loggers when log level is DEBUG
                if upper_log_level_string == "DEBUG":
                    if len(the_logger.handlers) < 1:
                        exclude_logger_name_from_logging = False
                        for garbage_logger in garbage_loggers_to_exclude:
                            if name.startswith(garbage_logger):
                                exclude_logger_name_from_logging = True
                        if not exclude_logger_name_from_logging:
                            the_logger.addHandler(logging.StreamHandler(sys.stdout))
                for the_handler in the_logger.handlers:
                    the_handler.setFormatter(log_formatter)
                    the_handler.setLevel(log_level)
