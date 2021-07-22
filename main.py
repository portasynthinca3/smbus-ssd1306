#!/usr/bin/env python3

## SMBus-SSD1306 by portasynthinca3, 2021
## SSD1306 driver based on thom_tl's C++ code
## Licensed under WTFPL
##
## Uses the Linux SMBus userland interface to display
## data on an 128x64 SSD1306 screen connected directly to
## the system SMBus.
##
## Please be aware of the logic levels though. My SMBus
## uses 3.3V on the data lines. Those blue SSD1306
## breakout boards (such as the one I own) are designed for that.
## They also feature a 5V-to-3.3V charge pump. I powered
## mine with a nearby 5V line. If you want to use one
## of those boards make sure to either connect it to a 5V
## line or short the charge pump and connect it to a 3.3V
## line.

from smbus import SMBus
from PIL import Image, ImageDraw
from threading import Thread
import psutil
from time import time

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
        # also decresase the percharge period
        # "normal" value: 0xF1
        self.cmd(SSD1306Vals.SET_PRECHARGE_PERIOD, 0x81)
        self.cmd(SSD1306Vals.SET_VCOM_LEVEL, 0x40)
        self.cmd(SSD1306Vals.DISPLAY_VRAM)
        self.cmd(SSD1306Vals.DISPLAY_NORMAL)
        self.cmd(SSD1306Vals.DISABLE_SCROLL)
        self.cmd(SSD1306Vals.DISPLAY_ON)

        self.flip()

def shift_history(hist, new):
    return hist[1:] + [int(new)]

def draw_history(draw: ImageDraw, xy, height, history):
    for i, val in enumerate(history):
        x = xy[0] + i
        y = xy[1] + height
        draw.line((x, y, x, y - val), fill=1, width=1)

SCREENS = ["cpu_ram_%", "cpu_temp_net", "music"]
SWITCH_PERIOD = 3
def drawing_thread(disp: SSD1306):
    graph_height = 48
    graph_scale_y, history_depth = graph_height / 100, 60
    cpu_history = [0] * history_depth
    ram_history = [0] * history_depth
    temp_history = [0] * history_depth
    net_history, last_net = [0] * history_depth, psutil.net_io_counters().bytes_recv

    screen_id = 0
    start = time()
    last_query = time()

    while True:
        # get new values
        cpu, ram = psutil.cpu_percent(), psutil.virtual_memory()
        used_gb = ram.used / (1024 ** 3)
        total_gb = ram.total / (1024 ** 3)
        cpu_temp = psutil.sensors_temperatures()["coretemp"][0]
        net_raw = psutil.net_io_counters().bytes_recv
        net = net_raw - last_net
        last_net = net_raw
        net = 8 * net / (time() - last_query)
        last_query = time()

        cpu_history = shift_history(cpu_history, cpu * graph_scale_y)
        ram_history = shift_history(ram_history, (used_gb / total_gb) * 100 * graph_scale_y)
        temp_history = shift_history(temp_history, (cpu_temp.current / cpu_temp.critical) * 100 * graph_scale_y)
        net_history = shift_history(net_history, (net / 1000000) * graph_scale_y)

        # repaint screen
        disp.draw.rectangle((0, 0, 127, 63), fill=0)
        screen = SCREENS[screen_id]
        if screen == "cpu_ram_%":
            disp.draw.line((0, 16, 127, 16), fill=1)
            draw_history(disp.draw, (0, 16), graph_height, cpu_history)
            draw_history(disp.draw, (64, 16), graph_height, ram_history)
            disp.draw.text((0, 0), f"{round(psutil.cpu_freq().current / 1000, 1)} GHz", fill=1)
            disp.draw.text((63, 0), f"{round(used_gb, 1)}/{round(total_gb, 1)} GB", fill=1)
        elif screen == "cpu_temp_net":
            disp.draw.line((0, 16, 127, 16), fill=1)
            draw_history(disp.draw, (0, 16), graph_height, temp_history)
            draw_history(disp.draw, (64, 16), graph_height, net_history)
            disp.draw.text((0, 0), f"{int(cpu_temp.current)}°C", fill=1)
            disp.draw.text((63, 0), f"{int(net / 1000000)}mbps", fill=1)
        elif screen == "music":
            disp.draw.text((0, 0), "nothin' here yet!", fill=1)

        # switch screens every SWITCH_PERIOD seconds
        if time() - start >= SWITCH_PERIOD:
            screen_id += 1
            screen_id %= len(SCREENS)
            start = time()

        # transfer data to the display
        disp.flip()

if __name__ == "__main__":
    display = SSD1306()
    display.init()

    thr = Thread(target=drawing_thread, args=(display,), name="Drawing thread")
    thr.start()
    thr.join()