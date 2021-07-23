## SMBus-SSD1306 by portasynthinca3, 2021
## Licensed under WTFPL

from PIL import ImageDraw
import psutil, time
from config import *
from media import get_song

## If you want to define your own screen, consider familiarizing
## yourself with the lifecycle:
## 1. Screen object gets created. Only this instance exists at any point in time.
## 2. Every frame:
##    2.1. update() of each screen gets called regardless of whether the screen
##         is currently selected or not;
##    2.2. render() of the currently selected screen gets called. it may return
##         False if there's nothing to display. If that screen is not currently
##         fixed by the user, it will get skipped in the auto-switch cycle.
## You only need to define the screen class here. The main code will automatically
## pick it up.

## Helper functions
def draw_progress(draw: ImageDraw, xy, wh, val, max):
    draw.rectangle((xy, (xy[0] + wh[0], xy[1] + wh[1])), fill=0, outline=1)
    draw.rectangle(((xy[0] + 2, xy[1] + 2), (xy[0] + 2 + int((wh[0] - 4) * val / max), xy[1] + 2 + wh[1] - 4)), fill=1)

def draw_text_center(draw: ImageDraw, y, text):
    w, _ = draw.textsize(text)
    draw.text((64 - (w // 2), y), text, fill=1)
def draw_text_right(draw: ImageDraw, y, text):
    draw.text((0, y), text, fill=1)
def draw_text_left(draw: ImageDraw, y, text):
    w, _ = draw.textsize(text)
    draw.text((128 - w, y), text, fill=1)

class Graph:
    def __init__(self, width, height, max_val=None):
        self.width = width
        self.height = height
        self.max = max_val
        self.history = [0] * width

    def shift(self, val):
        self.history = self.history[1:] + [val]

    def render(self, draw, xy):
        # scale the values so that they fit into the height
        max_val = max(1, max(self.history)) if self.max == None else self.max
        normalized = [x * self.height // max_val for x in self.history]
        # draw the graph
        for i, val in enumerate(normalized):
            x = xy[0] + i
            y = xy[1] + self.height
            draw.line((x, y, x, y - val), fill=1, width=1)

class Screen:
    def __init__(self, draw):
        self.draw = draw
    def update(self): ## updates internal values (even if the screen is not currently selected)
        pass
    def render(self): ## renders the screen
        pass

class CpuRamScreen(Screen):
    def __init__(self, draw):
        super().__init__(draw)
        self.total_ram = psutil.virtual_memory().total / (1024 ** 3)
        self.cpu = Graph(60, 48, 100)
        self.ram = Graph(60, 48, self.total_ram)

    def update(self):
        self.freq = psutil.cpu_freq().current / 1000
        self.used_ram = psutil.virtual_memory().used / (1024 ** 3)
        self.cpu.shift(psutil.cpu_percent())
        self.ram.shift(self.used_ram)

    def render(self):
        self.draw.line((0, 16, 127, 16), fill=1)
        self.cpu.render(self.draw, (0, 16))
        self.ram.render(self.draw, (64, 16))
        self.draw.text((0, 0), f"{round(self.freq, 1)} GHz", fill=1)
        self.draw.text((63, 0), f"{round(self.used_ram, 1)}/{round(self.total_ram, 1)} GB", fill=1)

class TempNetScreen(Screen):
    def __init__(self, draw):
        super().__init__(draw)
        critical_temp = psutil.sensors_temperatures()["coretemp"][0].critical
        self.last_query = time.time()
        self.last_net = 0
        self.tmp = Graph(60, 48, critical_temp)
        self.net_graph = Graph(60, 48)

    def update(self):
        # psutil doesn't provide a convenient "get download bitrate"
        # function, so we're using this mess
        net_raw = psutil.net_io_counters().bytes_recv
        self.net = net_raw - self.last_net
        self.last_net = net_raw
        self.net = 8 * self.net / (time.time() - self.last_query)
        self.last_query = time.time()
        self.cur_temp = psutil.sensors_temperatures()["coretemp"][0].current
        self.tmp.shift(self.cur_temp)
        self.net_graph.shift(self.net)

    def render(self):
        self.draw.line((0, 16, 127, 16), fill=1)
        self.tmp.render(self.draw, (0, 16))
        self.net_graph.render(self.draw, (64, 16))
        self.draw.text((0, 0), f"{int(self.cur_temp)}°C", fill=1)
        self.draw.text((63, 0), f"{round(self.net / 1000000, 2)}mbps", fill=1)

class MediaScreen(Screen):
    def __init__(self, draw):
        super().__init__(draw)
    
    def update(self):
        pass

    def render(self):
        should_skip = False
        song = get_song()
        if song == None:
            should_skip = True # we're going to render dummy data instead
            song = "---", "---", 1000000, 0, None
        artist, title, duration, pos, rating = song

        duration //= 1000000 # duration and pos are in microseconds
        pos //= 1000000
        if duration == 0:
            duration = 1
        draw_progress(self.draw, (0, 56), (127, 7), pos, duration)
        draw_text_center(self.draw, 0, title)
        if artist != None:
            draw_text_center(self.draw, 10, artist)
        if rating != None:
            draw_progress(self.draw, (50, 25), (27, 7), rating * 100, 100)
        duration_text = f"{duration // 60}:" + str(duration % 60).rjust(2, "0")
        draw_text_left(self.draw, 46, duration_text)
        pos_text = f"{pos // 60}:" + str(pos % 60).rjust(2, "0")
        draw_text_right(self.draw, 46, pos_text)

        return should_skip