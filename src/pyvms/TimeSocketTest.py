import datetime
import logging
from time import sleep
from .TimeSocket import *
from .TimeStats import *

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(levelname)-8s %(module)s:%(lineno)s - %(message)s')


def test_timestamp(iterations=1, delay=1.):
    ret = 0

    sock = TimeSocket()
    sock.listen(50000)
    for i in range(iterations):
        stats = TimeStats()
        sock.receive_loop(time=delay, stats=stats)
        print(stats.print())
    sock.close()

    return ret


if __name__ == "__main__":
    print(f"=== START === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    err = 0
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    for i in range(1):
        err += test_timestamp(iterations=5, delay=10)

    print(f"=== END === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    print('=== RESULT === {} === '.format('SUCCESS' if err == 0 else '{} ERRORS'.format(err)))
