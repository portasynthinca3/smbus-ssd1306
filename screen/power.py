from . import Screen
from dbus import SystemBus, Interface
from PIL.ImageDraw import ImageDraw
from datetime import datetime

from config import BATTERY
from fonts import JB_MONO_20, JB_MONO_10

SERVICE = "org.freedesktop.UPower.Device"

WEEKDAY_STR = [
    "mon",
    "tue",
    "wed",
    "thu",
    "fri",
    "sat",
    "sun",
]

class PowerScreen(Screen):
    def __init__(self):
        self.object = SystemBus().get_object("org.freedesktop.UPower",
                                             f"/org/freedesktop/UPower/devices/battery_{BATTERY}")
        self.interface = Interface(self.object, "org.freedesktop.DBus.Properties")
        self.state = None
        self.update(None)

    def update(self, display):
        state = self.interface.Get(SERVICE, "State")
        self.percentage = self.interface.Get(SERVICE, "Percentage")
        self.watts = abs(self.interface.Get(SERVICE, "EnergyRate"))
        self.time = None
        if state in [1, 2]:
            self.time = self.interface.Get(SERVICE, "TimeToFull" if state == 1 else "TimeToEmpty")

        # overtake for 2 seconds if charger status changed
        if self.state != state:
            self.state = state
            return (True, 2)
        else:
            return (True, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        # battery icon and percentage
        image_draw.rectangle([(0, 0), (40, 20)], 0, 1, 1) # battery frame
        image_draw.rectangle([(40, 7), (43, 13)], 1) # battery nipple
        image_draw.rectangle([(3, 3), (3 + (self.percentage * 34 / 100), 17)], 1) # battery charge
        image_draw.text((50, -3), f"{self.percentage:.0f}%", 1, JB_MONO_20) # battery percentage

        # direction arrow and wattage
        if self.state in [1, 2]:
            image_draw.rectangle([(10, 29), (30, 31)], 1) # arrow line
            # arrow head
            if self.state == 1: # charging
                image_draw.polygon([(31, 30), (25, 24), (25, 36)], 1)
            elif self.state == 2: # discharging
                image_draw.polygon([(9, 30), (15, 24), (15, 36)], 1)
        if self.watts:
            image_draw.text((50, 17), f"{self.watts:.1f}W", 1, JB_MONO_20) # wattage

        if self.time:
            # time to empty/full
            image_draw.text((50, 37), f"{self.time // 3600}:{(self.time % 3600) // 60 :02}", 1, JB_MONO_20) # remaining time
        else:
            # system time
            now = datetime.now()
            clock_str = f"{now.hour:02}{':' if now.microsecond > 500_000 else ' '}{now.minute:02}"
            image_draw.text((0, 37), clock_str, 1, JB_MONO_20)
            image_draw.text((65, 40), f"{now.day:02}/{now.month:02} {WEEKDAY_STR[now.weekday()]}", 1, JB_MONO_10)
            image_draw.text((65, 49), str(now.year), 1, JB_MONO_10)
