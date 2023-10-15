import datetime
import logging
from time import sleep
from .ConfigSocket import *
from .Regs import VmsRegsMcu as mcu
from .Regs import VmsRegsMaster as master
from .Regs import VmsRegsFe as fe


def test_setup(iterations=1, delay=1.):
    ret = 0
    fe16 = 16

    conf = ConfigSocket()
    conf.listen(50001)

    # conf.update_firmware('p:/001_Projects/LE_15-001_VMS/_Old/200_BTT_v2/111_FW/001_VMS_v2_FW/RevB/CardMCU_RevB1/'
    #                      '2017-10-02-12h-13m-36s-CardMCU_RevB1.rbf', Protocol.FW_MASTER, 0)

    # Temperature alarm and measurement do not work
    conf.write_fe(fe16, fe.TEMPERATURE_ALARM, 2000 << 16)
    sleep(1)
    value = conf.read_fe(fe16, fe.TEMPERATURE_ALARM)
    temper, alarm = get_fe_temperature(value)
    print(temper, alarm)

    sleep(1)
    val = conf.read_mcu(mcu.CONTROL) + (1 << 4)
    conf.write_mcu(mcu.CONTROL, val)
    sleep(2)

    conf.close()

    return ret


if __name__ == "__main__":
    print(f"=== START === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    err = 0
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    for i in range(1):
        err += test_setup(iterations=1, delay=5)

    print(f"=== END === " + datetime.datetime.now().strftime("%y/%m/%d %H:%M:%S ==="))
    print('=== RESULT === {} === '.format('SUCCESS' if err == 0 else '{} ERRORS'.format(err)))
