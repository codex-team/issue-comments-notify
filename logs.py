import logging


def init_logger(name, filename="logs.log"):
    logging.basicConfig(
        filename=filename,
        level=logging.INFO,
        format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(name)-9s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    return logging.getLogger(name)
