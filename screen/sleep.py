from . import Screen
from dbus import SystemBus
from PIL.ImageDraw import ImageDraw

class SleepScreen(Screen):
    def __init__(self):
        self.entering_sleep = False
        self.sleep_lock = False
        SystemBus().add_signal_receiver(
            self._sleep_callback,
            "PrepareForSleep",
            "org.freedesktop.login1.Manager",
            "org.freedesktop.login1"
        )

    def _sleep_callback(self, sleeping):
        self.entering_sleep = sleeping
        self.sleep_lock = sleeping

    def update(self, display):
        if self.entering_sleep:
            if self.sleep_lock:
                # since we're overtaking, we can be sure that no one is going to overwrite our "zzz" except us
                # that's why the "sleep lock" is in place - update() might be called several times
                display.draw.rectangle((0, 0, 127, 63), 0)
                display.draw.text((63,31), "zzz", 1, anchor="mm")
                display.flip()
                display.sleep_mode(True)
                self.sleep_lock = False
            return (True, 100)
        
        display.sleep_mode(False)
        return (False, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        return True
