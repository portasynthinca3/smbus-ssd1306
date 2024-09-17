#!/usr/bin/env python3

import sys, os, threading
sys.path.append(os.path.dirname(__file__))

from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
from gi.repository import GLib

from driver.ssd1306 import SSD1306
# from driver.mpu6050 import MPU6050
# from driver.bmp280 import BMP280
from config import I2C_ADAPTER, SSD1306_ADDR
from screen.runner import ScreenRunner
from screen.power import PowerScreen
from screen.media import MediaScreen
from screen.sleep import SleepScreen
from screen.load import LoadScreen
from screen.new_year import NewYearScreen
from server import ScreenService

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
        display.draw.rectangle((0, 0, 128, 64), 1)
        display.flip()
        exit()
    if "bad_apple" in sys.argv:
        import bad_apple
        bad_apple.run(display)
        exit()

    # init screen runner
    screen_runner = ScreenRunner([
        PowerScreen,
        MediaScreen,
        LoadScreen,
        NewYearScreen,
        SleepScreen,
    ])

    # init D-Bus service
    ScreenService(screen_runner, "/ru/psi3/ssd1306/screens", "ru.psi3.ssd1306")

    # run application
    threading.Thread(target=glib_thread).start()
    while True:
        screen_runner.frame(display)
