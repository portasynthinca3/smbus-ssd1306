from time import time, sleep
from multiprocessing import Lock

from driver.ssd1306 import SSD1306
from config import DEBUG, MAX_UPDATE_RATE, SCREEN_SWITCH_PERIOD

def render_bars(length, target, overshoot, sections):
    SYMBOLS = ["#", "|", "/", "+"]
    chars = ["-"] * length
    last_pos = 0
    overflow = False

    for i, s in enumerate(sections):
        fraction = s / target
        bars = int(length / overshoot * fraction)
        for j in range(bars):
            if last_pos + j >= length:
                overflow = True
            else:
                chars[last_pos + j] = SYMBOLS[i]
        last_pos += bars

    if overshoot != 1:
        chars[int(length / overshoot)] = "^"
    return "[" + "".join(chars) + (">" if overflow else "]")

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
        update_results = []
        for screen in self.screens:
            try:
                update_results.append(screen.update(display))
            except:
                update_results.append((False, None))

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
        flip_start = time()
        if not skip_flip:
            transfer_sz, max_transfer_sz = display.flip()
        flip_took = time() - flip_start
        draw_took = time() - draw_start

        # maintain max refresh rate
        artificial_delay = max(0, (1 / MAX_UPDATE_RATE) - draw_took)
        sleep(artificial_delay)
        draw_took = time() - draw_start

        # print debug into
        if DEBUG:
            print(f"FRAME render#={1000 * (draw_took - flip_took - artificial_delay):.1f}ms\tflip|={1000 * flip_took:.1f}ms\ttotal={1000 * draw_took:.1f}ms\tfps={1 / draw_took:.1f}")
            overshoot = 10 if flip_took >= 3 / MAX_UPDATE_RATE else 5
            print("   |- breakdown " + render_bars(80, 1 / MAX_UPDATE_RATE, overshoot, [draw_took - flip_took - artificial_delay, flip_took]))
            if not skip_flip:
                print("   |- bus load  " + render_bars(80, max_transfer_sz, 1, [transfer_sz]) + f" {int(100 * transfer_sz / max_transfer_sz)}% {transfer_sz}/{max_transfer_sz} ")
            print()

        # return screen to stack
        self.screen_stack.append((idx, timeout - (0 if self.pinned else draw_took)))

        return True
