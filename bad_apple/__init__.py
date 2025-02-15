from cv2 import VideoCapture, resize, CAP_PROP_POS_MSEC
from os import path
from driver.ssd1306 import SSD1306
from time import time
from screen.runner import render_bars

def run(display: SSD1306):
    draw = display.draw
    cap = VideoCapture(path.join(path.dirname(__file__), "bad_apple.mp4"))
    start = time()
    
    while cap.isOpened():
        # read frame
        ok, frame = cap.read()
        if not ok:
            break

        # drop frames (display is slower)
        pos = cap.get(CAP_PROP_POS_MSEC)
        if pos < (time() - start) * 1000:
            continue

        # resize to fit display
        assert frame.shape == (360, 480, 3)
        frame = resize(frame, (85, 64))

        # clear screen
        draw.rectangle([(0, 0), (127, 63)], 0)

        # draw frame
        for y in range(64):
            for x in range(85):
                if frame[y][x][0] / 255 >= 0.5:
                    draw.point((x + 21, y), 1)
        
        # flip
        transfer_sz, max_transfer_sz = display.flip()
        BYTES_FOR_30FPS = 265
        print("bus load " + render_bars(80, BYTES_FOR_30FPS, max_transfer_sz / BYTES_FOR_30FPS, [transfer_sz]) + f" {int(100 * transfer_sz / max_transfer_sz)}% {transfer_sz}/{max_transfer_sz}")
