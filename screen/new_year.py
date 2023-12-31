from . import Screen
from PIL.ImageDraw import ImageDraw
from random import random, randint
from time import time

from config import MAX_SNOW

class NewYearScreen(Screen):
    def _generate_snow(self):
        return (
            randint(0, 127), # X
            randint(0, 10),  # Y
            time(),          # last change
            random() * 0.3,  # period
        )

    def __init__(self):
        self.snow = []
        self.next_flake = time() + (random() * 0.1)

    def update(self, display):
        return (True, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        # draw snow
        SNOW_LINES = [
            # y   x0 x1
            (63, (0, 127)),
            (62, (0, 127)),
            (61, (0, 61)), (61, (72, 127)),
            (60, (3, 21)), (60, (30, 40)), (60, (46, 54)), (60, (80, 91)),
            (59, (6, 18)), (59, (32, 39)), (59, (50, 52)), (59, (81, 86)),
            (58, (14, 16)), (58, (34, 38)),
            (57, (37, 37))
        ]
        for y, (x0, x1) in SNOW_LINES:
            image_draw.line([(x0, y), (x1, y)], 1, 1)
        
        # draw house
        image_draw.rectangle([(103, 46), (125, 61)], 0, 1) # body
        image_draw.line([(103, 45), (113, 35), (115, 35), (125, 45)], 1, 1) # roof
        image_draw.rectangle([(107, 51), (114, 57)], 0, 1) # window frame
        image_draw.line([(108, 54), (113, 54)], 1, 1) # window line 1
        image_draw.line([(110, 52), (110, 56)], 1, 1) # window line 2
        image_draw.rectangle([(118, 54), (122, 61)], 0, 1) # door frame
        image_draw.point((121, 57), 1) # door handle

        # draw christmas tree
        image_draw.rectangle([(57, 57), (58, 60)], 1) # trunk
        image_draw.polygon([(53, 56), (57, 52), (58, 52), (62, 56)], 1) # level 1
        image_draw.polygon([(54, 51), (57, 48), (58, 48), (61, 51)], 1) # level 2
        image_draw.polygon([(55, 47), (57, 45), (58, 45), (60, 47)], 1) # level 3

        # draw snow
        for i, (x, y, last, period) in enumerate(self.snow):
            image_draw.point((x, y), 1)
            if time() - last >= period:
                y = (y + 1) % 64
                # check if can move down
                if image_draw._image.getdata()[y * 128 + x] == 0:
                    self.snow[i] = (x, y, time(), period)

        # generate new snow
        if time() >= self.next_flake:
            self.snow.append(self._generate_snow())
            self.next_flake = time() + (random() * 0.1)
        if len(self.snow) > MAX_SNOW:
            self.snow = []
