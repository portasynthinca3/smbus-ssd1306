from . import Screen
from PIL.ImageDraw import ImageDraw
from time import time
import psutil

from config import SPEC_SMOOTH_SPEED, TEMP_SENSOR
from fonts import JB_MONO_20

class LoadScreen(Screen):
    def __init__(self):
        self.cpu = [0] * psutil.cpu_count()
        self.last_upd = time() - 100
        self.last_smooth = time()
        self.temp = None

    def update(self, display):
        if time() - self.last_upd > 0.5:
            # get data
            self.last_upd = time()
            self.cpu_actual = psutil.cpu_percent(percpu=True)
            self.mem_actual = psutil.virtual_memory()
            if TEMP_SENSOR:
                self.temp = [temp.current for temp in psutil.sensors_temperatures()[TEMP_SENSOR[0]] if temp.label == TEMP_SENSOR[1]][0]
        else:
            # apply smoothing
            delta_t = time() - self.last_smooth
            self.last_smooth = time()
            for i in range(len(self.cpu)):
                delta = self.cpu_actual[i] - self.cpu[i]
                self.cpu[i] += delta * delta_t * SPEC_SMOOTH_SPEED

        return (True, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        # per-core CPU bars
        x, y = 0, 0
        for percent in self.cpu:
            image_draw.rectangle([(x, y), (x + 15, y + 6)], 0, 1) # bar frame
            if percent > 1:
                image_draw.rectangle([(x + 2, y + 2), (x + 2 + (percent / 100 * 12), y + 4)], 1) # bar body
            # advance position
            y += 6
            if y >= 57:
                y = 0
                x += 15

        # overall stats
        if y != 0:
            x += 20
            y = 0
        
        # CPU percentage
        cpu_percent = sum(self.cpu) / len(self.cpu)
        image_draw.text((x, y - 7), f"{cpu_percent:2.0f}%", 1, JB_MONO_20)
        y += 20

        # CPU temperature
        if self.temp is not None:
            image_draw.text((x, y - 7), f"{self.temp:2.0f}C", 1, JB_MONO_20)
