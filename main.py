#!/usr/bin/env python3

import sys, os, threading
sys.path.append(os.path.dirname(__file__))

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
from gi.repository import GLib

from driver.ssd1306 import SSD1306
# from driver.mpu6050 import MPU6050
# from driver.bmp280 import BMP280
from config import *
from screen.runner import ScreenRunner
from screen.power import PowerScreen
from screen.media import MediaScreen
from screen.sleep import SleepScreen

def glib_thread():
    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    display = SSD1306(I2C_ADAPTER, SSD1306_ADDR)
    # mpu = MPU6050(I2C_ADAPTER, MPU6050_ADDR)

    # test commands
    if "blank" in sys.argv:
        display.power(False)
        exit()
    if "white" in sys.argv:
        display.draw.rectangle((0, 0, 128, 64), 1, width=0)
        display.flip()
        exit()

    # start GLib loop thread for receiving DBus signals
    threading.Thread(target=glib_thread).start()

    # start screen runner
    screen_runner = ScreenRunner([
        PowerScreen,
        MediaScreen,
        SleepScreen,
    ])
    while True:
        screen_runner.frame(display)
