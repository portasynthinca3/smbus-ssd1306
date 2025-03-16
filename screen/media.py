from . import Screen
from dbus import SessionBus, Interface
from PIL.ImageDraw import ImageDraw
from PIL import Image
import pyaudio
import struct
from math import sqrt
from urllib import request
from time import time

from config import PLAYER_IGNORE, VOLUME_DEVICE, VOLUME_MULTIPLY

SERVICE1 = "org.mpris.MediaPlayer2"
SERVICE2 = "org.mpris.MediaPlayer2.Player"

pa = pyaudio.PyAudio()

def scrolling_text(image_draw: ImageDraw, text: str, w_limit: int, pos: tuple[int, int]):
    _, _, w, h = image_draw.textbbox((0, 0), text)
    temp_image = Image.new("1", (w, h))
    temp_draw = ImageDraw(temp_image)
    temp_draw.text((0, 0), text, 1)

    if temp_image.width > w_limit:
        x_pos = 0
        phase = int(time() / 2 * 1000) % 2000
        if phase < 500:
            x_pos = 0
        elif phase > 1500:
            x_pos = temp_image.width - w_limit
        else:
            x_pos = ((phase - 500) / (1500 - 500)) * (temp_image.width - w_limit)
        temp_image = temp_image.crop((x_pos, 0, x_pos + w_limit, temp_image.height))

    image_draw.bitmap(pos, temp_image, 1)

class MediaScreen(Screen):
    def __init__(self):
        self.vu = (0, 0)
        self.album_cover_url = None

        # list audio devices
        devices = []
        print("Available input devices:")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info["maxInputChannels"] > 0:
                print(f"{info['index']}\t{info['name']}")
                devices.append(info['name'])

        # init audio device
        if VOLUME_DEVICE:
            index = [i for (i, dev) in enumerate(devices) if dev == VOLUME_DEVICE][0]
            pa.open(format=pyaudio.paInt16,
                    input_device_index=index,
                    channels=2,
                    rate=48000,
                    frames_per_buffer=512,
                    input=True,
                    stream_callback=self.audio_data_cb)

        self.playback_status = None
        self.update(None)

    def get_player_iface(self, name):
        obj = SessionBus().get_object(name, "/org/mpris/MediaPlayer2")
        return Interface(obj, "org.freedesktop.DBus.Properties")
    
    def audio_data_cb(self, data, _frames, _time, _flags):
        # convert input buffer to float
        quarter_len = len(data) // 4
        l_sqsum, r_sqsum = 0, 0
        for i in range(0, len(data), 4):
            l_sqsum += (struct.unpack("h", data[i : i + 2])[0] / 32768) ** 2
            r_sqsum += (struct.unpack("h", data[i + 2 : i + 4])[0] / 32768) ** 2

        # calculate volume
        self.vu = tuple(min(1, sqrt(sq_sum / quarter_len) * VOLUME_MULTIPLY)
                        for sq_sum in (l_sqsum, r_sqsum))

        return None, pyaudio.paContinue

    def update(self, display):
        # get all players
        players = [name for name in SessionBus().list_names() if name.startswith("org.mpris.MediaPlayer2.")]
        for ignore in PLAYER_IGNORE:
            players = [name for name in players if ignore not in name]
        if len(players) == 0:
            return (False, 0)
        
        # find first active player
        # or the last one if none are playing
        iface = None
        for player in players:
            iface = self.get_player_iface(player)
            if iface.Get(SERVICE2, "PlaybackStatus") == "Playing":
                break
        
        # get info
        self.name = iface.Get(SERVICE1, "Identity")
        status = iface.Get(SERVICE2, "PlaybackStatus")
        metadata = iface.Get(SERVICE2, "Metadata")
        self.artist = ", ".join(metadata["xesam:artist"])
        self.title = metadata["xesam:title"]
        try:
            self.position = iface.Get(SERVICE2, "Position")
            self.length = metadata["mpris:length"]
        except:
            self.position = None
            self.length = None
        try:
            cover_url = metadata["mpris:artUrl"]
            if cover_url != self.album_cover_url:
                cover_path, _ = request.urlretrieve(cover_url)
                cover = Image.open(cover_path).resize((64, 64)).convert("1")
                self.album_cover = cover
                self.album_cover_url = cover_url
        except:
            self.album_cover = None

        # overtake for 2 seconds if playback status changed
        if self.playback_status != status:
            self.playback_status = status
            return (True, 2)

        return (True, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        if self.album_cover:
            image_draw.bitmap((0, 0), self.album_cover, 1)
        else:
            image_draw.rectangle(((0, 0), (63, 63)))

        # artist and title
        scrolling_text(image_draw, self.title, 63, (65, 15))
        scrolling_text(image_draw, self.artist, 63, (65, 29))

        # progress bar and associated times
        if self.position is not None and self.length:
            image_draw.rectangle([(65, 56), (127, 63)], 0, 1) # progress bar frame
            image_draw.rectangle([(67, 58), (67 + (self.position * 58 / self.length), 61)], 1) # progress bar
            image_draw.text((65, 54), f"{self.position // 60_000_000}:{(self.position // 1_000_000) % 60 :02}", 1, anchor="lb") # playback position
            image_draw.text((127, 54), f"{self.length // 60_000_000}:{(self.length // 1_000_000) % 60 :02}", 1, anchor="rb") # song length

        # playback status
        x = 92
        y = 46
        if self.playback_status == "Playing":
            image_draw.polygon([(x, y), (x + 6, y + 3), (x, y + 7)], 1) # triangle
        elif self.playback_status == "Paused":
            image_draw.rectangle([(x, y), (x + 2, y + 7)], 1)
            image_draw.rectangle([(x + 5, y), (x + 7, y + 7)], 1)
        elif self.playback_status == "stopped":
            image_draw.rectangle([(x, y), (x + 7, y + 7)], 1)
        
        # VU meter
        VU_MAX = 32
        if self.vu[0] > 1e-5:
            image_draw.rectangle([(65, 0), (65 + (VU_MAX * self.vu[0]), 3)], 1)
        if self.vu[1] > 1e-5:
            image_draw.rectangle([(65, 5), (65 + (VU_MAX * self.vu[1]), 8)], 1)
