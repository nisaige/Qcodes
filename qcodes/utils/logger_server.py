import logging
import zmq

def broker(frontend_addres="tcp://*:5559", backend_address="tcp://*:5560"):
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
    try:
        frontend.bind(frontend_addres)
        logging.info("XSUB listening at {}".format(frontend_addres))
    except zmq.error.ZMQError:
        logging.debug("Exiting. Broker is already running")
        return

        # Socket facing services
    backend = context.socket(zmq.XPUB)
    try:
        backend.bind(backend_address)
        logging.info("XPUB publishing at {}".format(backend_address))
    except zmq.error.ZMQError:
        logging.debug("Exiting. Broker is already running")
        return

    try:
        a = zmq.proxy(frontend, backend)
    except KeyboardInterrupt:
        frontend.close()
        backend.close()
        context.term()
        logging.debug("Exiting. Broker got <C-c>")
        return

broker()
