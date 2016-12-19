import logging
logging.basicConfig(level="DEBUG")

import zmq
from zmq.utils.strtypes import bytes, unicode, cast_bytes

# TODO(giulioungaretti)
# What you don’t want to collect 	How to avoid collecting it
# Information about where calls were made from.
# Set logging._srcfile to None. This avoids calling sys._getframe(), which
# may help to speed up your code in environments like PyPy (which can’t
# speed up code that uses sys._getframe()), if and when PyPy
# supports Python 3.x.
# TODO(giulioungaretti) review formatters


DEBUGF = "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s"
DATEFMT = "%H:%M:%S"

# for k in PUBHandler.formatters:
    # QPUBHandler.formatters[k] = logging.Formatter(f, datefmt=)

class QPUBHandler(logging.Handler):
    """A basic logging handler that emits log messages through a PUB socket.

    Takes an interface to connect to.

        handler = PUBHandler('inproc://loc')

    Log messages handled by this handler are broadcast with ZMQ topics
    ``this.root_topic`` comes first, followed by the log level
    (DEBUG,INFO,etc.), followed by any additional subtopics specified in the
    message by: log.debug("subtopic.subsub::the real message")
    """
    root_topic=""
    socket = None

    # add more info to debug it's not cheap but more informative
    formatters = {
        logging.DEBUG: logging.Formatter(DEBUGF, datefmt=DATEFMT),
        logging.INFO: logging.Formatter("%(name)s:%(message)s\n", datefmt=DATEFMT),
        logging.WARN: logging.Formatter(
            "%(levelname)s %(filename)s:%(name)s:%(lineno)d - %(message)s\n", datefmt=DATEFMT),
        logging.ERROR: logging.Formatter(
            "%(levelname)s %(filename)s:%(name)s:%(lineno)d - %(message)s - %(exc_info)s\n", datefmt=DATEFMT),
        logging.CRITICAL: logging.Formatter(
        "%(levelname)s %(filename)s:%(lineno)d - %(message)s\n",  datefmt=DATEFMT)}

    def __init__(self, interface_or_socket, context=None):
        logging.Handler.__init__(self)
        self.ctx = context or zmq.Context()
        self.socket = self.ctx.socket(zmq.PUB)
        self.socket.connect(interface_or_socket)

    def format(self,record):
        """Format a record."""
        return self.formatters[record.levelno].format(record)

    def emit(self, record):
        """Emit a record message
        Args:
            record (logging.record): record to shovel on the socket
        """
        try:
            topic, record.msg = record.msg.split(TOPIC_DELIM,1)
        except Exception:
            topic = ""
        try:
            bmsg = cast_bytes(self.format(record))
        except Exception:
            self.handleError(record)
            return

        topic_list = []

        if self.root_topic:
            topic_list.append(self.root_topic)

        topic_list.append(record.levelname)

        if topic:
            topic_list.append(topic)

        btopic = b'.'.join(cast_bytes(t) for t in topic_list)

        self.socket.send_multipart([btopic, bmsg])

def check_broker(frontend_addres="tcp://*:5559", backend_address="tcp://*:5560"):
    """
    Simple XPUB/XSUB broker.
    Listens for messages on the frontend and transparently pushes them to a
    backend.
    This allows to have centralized logging, from multiple processes
    and to multiple consumers.
    Messages sent but never forward (f.e.x if there aren't subscribers)
    are quietly dropped.

    Args:
        frontend_addres (str): Interface to which the frontend is bound
        backend_address (str): Interface to which the backend is bound

    """
    context = zmq.Context()
    # Socket facing clients
    frontend = context.socket(zmq.XSUB)
    f = True
    b = True
    try:
        frontend.bind(frontend_addres)
        f = False
    except zmq.error.ZMQError:
        pass

    # Socket facing services
    backend = context.socket(zmq.XPUB)
    try:
        backend.bind(backend_address)
        b = False
    except zmq.error.ZMQError:
        pass

    frontend.close()
    backend.close()
    context.term()
    return f and b
