## SMBus-SSD1306 by portasynthinca3, 2021
## Licensed under WTFPL

from PIL import ImageDraw
import psutil, time
from config import *
from media import get_song
from pynput import mouse

## If you want to define your own screen, consider familiarizing
## yourself with the lifecycle:
## 1. Screen object gets created. Only this instance exists at any point in time.
## 2. register_hotkeys() gets called on each of the screen instances so that
##    the can, well, register global hotkeys.
## 3. Every frame:
##    3.1. update() of each screen gets called regardless of whether the screen
##         is currently selected or not;
##    3.2. render() of the currently selected screen gets called. it may return
##         True if there's nothing to display. If that screen is not currently
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
    def register_hotkeys(self):
        return {}
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
        self.draw.text((0, 0), f"{int(self.cur_temp)}??C", fill=1)
        self.draw.text((63, 0), f"{round(self.net / 1000000, 2)}mbps", fill=1)


class MediaScreen(Screen):
    def __init__(self, draw):
        super().__init__(draw)

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


class CpsScreen(Screen):
    def __init__(self, draw):
        super().__init__(draw)
        self.events = []
        self.graph = Graph(128, 48)
        self.cps_cur = 0
        self.cps_peak = 0
        self.mode = None

    def key_pressed(self):
        if not self.mode:
            self.events.append(time.time())
    def mouse_clicked(self, x, y, btn, pressed):
        if pressed and (self.mode or self.mode == None):
            self.events.append(time.time())
    def switch_mode(self):
        if   self.mode == None:  self.mode = True
        elif self.mode == True:  self.mode = False
        elif self.mode == False: self.mode = None
        self.reset()

    def reset(self):
        self.cps_peak = 0

    def register_hotkeys(self):
        mouse.Listener(on_click=self.mouse_clicked).start()
        return {
            "<ctrl>+<alt>+l": self.reset,
            "<ctrl>+<alt>+o": self.switch_mode,
            "z": self.key_pressed,
            "x": self.key_pressed
        }

    def update(self):
        self.events = [x for x in self.events if time.time() - x <= 1]
        self.cps_cur = len(self.events)
        if self.cps_cur > self.cps_peak:
            self.cps_peak = self.cps_cur
        self.graph.shift(self.cps_cur)

    def render(self):
        self.graph.render(self.draw, (0, 16))
        self.draw.text((0, 0), {None: "B", False: "K", True: "M"}[self.mode], fill=1)
        self.draw.text((16, 0), f"{int(self.cps_cur)} cur", fill=1)
        self.draw.text((56, 0), f"{int(self.cps_peak)} peak", fill=1)

class ProcessScreen(Screen):
    def __init__(self, draw):
        super().__init__(draw)
        self.top = []
        self.last_query = 0

    def update(self):
        if time.time() - self.last_query > 1:
            processes = [(p.name(), p.cpu_percent()) for p in psutil.process_iter()]
            self.top = sorted(processes, reverse=True, key=lambda p: p[1])[:7]
            self.last_query = time.time()
        
    def render(self):
        for i, (name, cpu) in enumerate(self.top):
            offs = i * 8
            draw_progress(self.draw, (0, offs + 1), (31, 6), cpu, 100 * psutil.cpu_count())
            self.draw.text((34, offs - 2), name, fill=1)