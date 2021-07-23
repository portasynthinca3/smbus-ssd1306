#!/usr/bin/env python3

## SMBus-SSD1306 by portasynthinca3, 2021
## SSD1306 driver based on thom_tl's C++ code
## Licensed under WTFPL
##
## Read README.md for instructions!

from smbus import SMBus
from PIL import Image, ImageDraw
from threading import Thread
from time import time
import dbus
import keyboard
import os, sys
from screens import Screen
from config import *

class SSD1306Vals:
    CMD_PREFIX =           0x00
    DATA_PREFIX =          0x40

    MEMORY_MODE =          0x20
    COL_ADDR =             0x21
    PAGE_ADDR =            0x22
    DISABLE_SCROLL =       0x2E
    SET_START_LINE =       0x40
    SET_CONTRAST =         0x81
    SET_CHARGE_PUMP =      0x8D
    SET_SEGMENT_REMAP =    0xA0
    DISPLAY_VRAM =         0xA4
    DISPLAY_FORCE_WHITE =  0xA5
    DISPLAY_NORMAL =       0xA6
    MULTIPLEX_RATIO =      0xA8
    DISPLAY_OFF =          0xAE
    DISPLAY_ON =           0xAF
    SET_COM_SCAN_DIR =     0xC8
    SET_DISPLAY_OFFSET =   0xD3
    SET_DISPLAY_CLK_DIV =  0xD5
    SET_PRECHARGE_PERIOD = 0xD9
    SET_COMPINS =          0xDA
    SET_VCOM_LEVEL =       0xDB

class SSD1306:
    def __init__(self, bus=0, addr=0x3C):
        # create interfacing objects
        self.bus = SMBus(bus)
        self.addr = addr
        self.fb = bytearray([0] * (128 * 64 // 8))
        # create PIL objects
        self.img = Image.new("1", (128, 64), 0)
        self.draw = ImageDraw.Draw(self.img)

    def cmd(self, cmd, *args):
        self.bus.write_i2c_block_data(self.addr, SSD1306Vals.CMD_PREFIX, [cmd] + list(args))
    def data(self, data):
        self.bus.write_i2c_block_data(self.addr, SSD1306Vals.DATA_PREFIX, list(data))

    def flip(self):
        # convert PIL image data into framebuffer data
        for coord, pix in enumerate(self.img.getdata()):
            x, y = coord % 128, coord // 128
            idx, shift = x + ((y // 8) * 128), y & 0x7
            if pix == 1:
                self.fb[idx] |= 1 << shift
            else:
                self.fb[idx] &= ~(1 << shift)
            
        # write framebuffer
        self.cmd(SSD1306Vals.PAGE_ADDR, 0, 0xFF)
        self.cmd(SSD1306Vals.COL_ADDR, 0, 127)
        for i in range(0, 128 * 64 // 8, 8):
            self.data(self.fb[i : i+8])

    def power(self, val):
        self.cmd(SSD1306Vals.DISPLAY_ON if val else SSD1306Vals.DISPLAY_OFF)

    def init(self):
        self.cmd(SSD1306Vals.DISPLAY_OFF)
        self.cmd(SSD1306Vals.SET_DISPLAY_CLK_DIV, 0x80) # suggested ratio
        self.cmd(SSD1306Vals.MULTIPLEX_RATIO, 63) # height - 1
        self.cmd(SSD1306Vals.SET_DISPLAY_OFFSET, 0)
        self.cmd(SSD1306Vals.SET_START_LINE | 0)
        self.cmd(SSD1306Vals.SET_CHARGE_PUMP, 0x14)
        self.cmd(SSD1306Vals.MEMORY_MODE, 0)
        self.cmd(SSD1306Vals.SET_SEGMENT_REMAP | 1)
        self.cmd(SSD1306Vals.SET_COM_SCAN_DIR)
        self.cmd(SSD1306Vals.SET_COMPINS, 0x12)
        # drive the display at a lower contrast to prevent burnout
        # remember, this poor panel is going to be running 24/7!
        # "normal" value: 0xC8
        self.cmd(SSD1306Vals.SET_CONTRAST, 0x00)
        self.cmd(SSD1306Vals.SET_PRECHARGE_PERIOD, 0xF1)
        self.cmd(SSD1306Vals.SET_VCOM_LEVEL, 0x40)
        self.cmd(SSD1306Vals.DISPLAY_VRAM)
        self.cmd(SSD1306Vals.DISPLAY_NORMAL)
        self.cmd(SSD1306Vals.DISABLE_SCROLL)
        self.cmd(SSD1306Vals.DISPLAY_ON)

        self.flip()

forced_screen, screen_fixed = -1, False
SCREEN_CLASSES = Screen.__subclasses__()
SCREENS = []
def drawing_thread(disp: SSD1306):
    global forced_screen

    # init state
    screen_id = 0
    screen_start = time()
    SCREENS = [x(disp.draw) for x in SCREEN_CLASSES]

    # add hotkeys
    def force_screen(i):
        global forced_screen
        forced_screen = i
    def fix_screen():
        global screen_fixed
        screen_fixed = not screen_fixed
    try:
        keyboard.add_hotkey(f"ctrl + shift + 0", fix_screen)
        for i in range(1, len(SCREENS) + 1):
            keyboard.add_hotkey(f"ctrl + shift + {i}", force_screen, args=(i - 1,))
    except ImportError:
        print("Warning: missing root access, unable to register screen switching hotkeys")

    while True:
        # update screens
        for s in SCREENS:
            s.update()

        # repaint screen
        skip = False
        disp.draw.rectangle((0, 0, 127, 63), fill=0)
        screen = SCREENS[screen_id]
        skip = screen.render()

        # switch screens every SWITCH_PERIOD seconds
        # or if there's nothing to display on the current one
        if skip or (not screen_fixed and time() - screen_start >= SCREEN_SWITCH_PERIOD):
            screen_id += 1
            screen_id %= len(SCREENS)
            screen_start = time()
        if forced_screen >= 0:
            screen_id = forced_screen
            forced_screen = -1
            screen_start = time()

        # draw a rectangle in the top right corner to indicate that the screen is fixed
        if screen_fixed:
            disp.draw.rectangle((123, 0, 127, 4), fill=1)

        # transfer data to the display
        if not skip:
            disp.flip()

if __name__ == "__main__":
    display = SSD1306(I2C_ADAPTER, SSD1306_ADDR)
    display.init()

    # if there's a "blank" argument, clear GDDRAM, power the display down and exit
    if "blank" in sys.argv:
        display.flip()
        display.power(False)
        exit()

    thr = Thread(target=drawing_thread, args=(display,), name="Drawing thread")
    thr.start()
    thr.join()