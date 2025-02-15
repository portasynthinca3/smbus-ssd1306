from typing import List, Tuple
from . import Screen
from PIL.ImageDraw import ImageDraw
from random import random, randint
from time import time
from math import sin

from config import N_FISH, N_SEAWEED

FISH_IMAGES = [
    [
        "   X   ",
        "  XX  X",
        " XXX XX",
        "X.XXXXX",
        "XXXXXXX",
        " XXX XX",
        "  XX  X",
        "   X   ",
    ],
    [
        "  XXXXX     XX X",
        " XXXXXXXXX   XXX",
        "XX.XXXXXXXXXXXX ",
        "XXXXXXXXXXXXXX  ",
        " XXXXXXXXXXXX",
        "  XXXXXXXXX",
    ],
    [
        "     X       ",
        "  XXXXX      ",
        " XXXXXXX    X",
        "XXXXXXXXX  XX",
        "XX.XXXXXXXXXX",
        "XX.XXXXXXXXX ",
        "XXXXXXXXX XXX",
        " XXXXXX    XX",
    ],
]

CASTLE = [
    "        X        ",
    "       XXX       ",
    "      XXXXX      ",
    "     XXXXXXX     ",
    "      X...X      ",
    "      X.X.X      ",
    "      X...X      ",
    "  XXXXXXXXXXXXX  ",
    " XX.X.X.X.X.X.XX ",
    "XX.X.X.X.XXXXX.XX",
    "X.X.X.X.X.X..XX.X",
    "XX.X.X.X.XX..X.XX",
    "X.X.X.X.X.XXXXX.X",
    "XX.X.XXXXXXX.X.XX",
    "X.X.XXX...XXX.X.X",
    "XX.X.X.....X.X.XX",
    "X.X.XX.....XX.X.X",
    "XX.X.X.....X.X.XX",
    "XXXXXX.....XXXXXX",
]

def draw_fish(image_draw: ImageDraw, sprite: List[str], pos: Tuple[int, int]):
    for y in range(len(sprite)):
        for x in range(len(sprite[y])):
            pixel = sprite[y][x]
            canvas_pos = (pos[0] + x, pos[1] + y)
            if pixel == "X":
                image_draw.point(canvas_pos, 1)
            elif pixel == ".":
                image_draw.point(canvas_pos, 0)

def draw_water(image_draw: ImageDraw, start: Tuple[int, int], size: Tuple[int, int]):
    STEP = 5
    for y in range(start[1], start[1] + size[1], STEP):
        for x in range(start[0], start[0] + size[0], STEP):
            image_draw.point((x, y), 1)

class FishTankScreen(Screen):
    def __init__(self):
        self.fish = []
        for _ in range(N_FISH):
            x = randint(0, 128)
            y = randint(20, 55)
            fish = (FISH_IMAGES[randint(0, len(FISH_IMAGES) - 1)], x, x, y, y, -(random() / 2) - 0.5)
            self.fish.append(fish)

        self.seaweed = []
        for _ in range(N_SEAWEED):
            self.seaweed.append((randint(0, 127), randint(5, 30)))

    def update(self, display):
        for (i, (image, x, xorig, y, yorig, speed)) in enumerate(self.fish):
            x += speed
            if x < -len(image[0]):
                x = 128
            y = yorig + (sin(xorig + (time())) * speed)
            self.fish[i] = (image, x, xorig, y, yorig, speed)
        return (True, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        # water
        draw_water(image_draw, (0, 20), (128, 44))

        # foam
        ms = (time() * 1000) % 1000
        image_draw.line(((0, 20), (127, 20)), 1, 1)
        for i in range(6):
            x_offs = [1 if ms > 300 else 0, 0 if ms > 500 else 1, 1 if ms < 600 else 0]
            image_draw.line(((i * 22 + 6 + x_offs[0], 18), (i * 22 + 6 + x_offs[0], 18)), 1, 1)
            image_draw.line(((i * 22 + 3 + x_offs[1], 19), (i * 22 + 8 + x_offs[1], 19)), 1, 1)
            image_draw.line(((i * 22 + 15 + x_offs[2], 21), (i * 22 + 20 + x_offs[2], 21)), 1, 1)

        # fish
        for (image, x, _xorig, y, _yorig, _speed) in self.fish[:N_FISH // 2]:
            draw_fish(image_draw, image, (x, y))

        # castle
        draw_fish(image_draw, CASTLE, (20, 45))

        # other fish (in front of castle)
        for (image, x, _xorig, y, _yorig, _speed) in self.fish[N_FISH // 2:]:
            draw_fish(image_draw, image, (x, y))

        # seaweed
        for (x, height) in self.seaweed:
            for y in range(64 - height, 63):
                x_offs = (y + (1 if ms > 500 else 0)) % 2
                image_draw.point((x + x_offs, y), 1)
