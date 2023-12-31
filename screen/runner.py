from time import time, sleep
from multiprocessing import Lock

from driver.ssd1306 import SSD1306
from config import DEBUG, MAX_UPDATE_RATE, SCREEN_SWITCH_PERIOD

class ScreenRunner:
    def __init__(self, screens: SSD1306):
        self.screens = [x() for x in screens]
        self.screen_stack = [(0, SCREEN_SWITCH_PERIOD)]
        self.ext_overtake = []
        self.pinned = False

    def external_overtake(self, number, duration):
        self.ext_overtake = (number, duration)
        if DEBUG:
            print(f"screen #{number} overtake for {duration}ms")

    def external_pin_switch(self):
        self.pinned = not self.pinned
        if DEBUG:
            print(f"screen pin switch: {self.pinned}")

    def frame(self, display: SSD1306):
        # update all screens
        update_results = [screen.update(display) for screen in self.screens]

        # process overtake requests
        for idx, (_runnable, overtake_for) in enumerate(update_results):
            if overtake_for:
                if self.screen_stack[-1][0] != idx:
                    self.screen_stack.append((idx, overtake_for))
                else:
                    self.screen_stack[-1] = (idx, overtake_for)
        if self.ext_overtake:
            self.screen_stack = [self.ext_overtake]
            self.ext_overtake = None

        # determine which screen is to be drawn
        idx, timeout = self.screen_stack.pop()
        if (timeout <= 0) or (not update_results[idx][0]):
            if len(self.screen_stack) == 0:
                self.screen_stack.append(((idx + 1) % len(self.screens), SCREEN_SWITCH_PERIOD))
            return False

        # draw
        draw_start = time()
        display.draw.rectangle([(0, 0), (127, 63)], 0)
        skip_flip = self.screens[idx].draw(len(self.screen_stack) > 0, display.draw) # if there are other screens in the stack, this one is overtaking
        
        # draw timeout bar
        if not self.pinned:
            display.draw.rectangle([(127 - (10 * timeout / SCREEN_SWITCH_PERIOD), 0), (127, 1)], 1)

        # flip
        if not skip_flip:
            display.flip()
        draw_took = time() - draw_start

        # maintain max refresh rate
        sleep(max(0, (1 / MAX_UPDATE_RATE) - draw_took))
        draw_took = time() - draw_start
        if DEBUG:
            print(f"frame took {draw_took * 1000 :.0f}ms, effective {1 / draw_took :.1f}fps")

        # return screen to stack
        self.screen_stack.append((idx, timeout - (0 if self.pinned else draw_took)))

        return True
