from . import Screen
from dbus import SessionBus, Interface
from PIL.ImageDraw import ImageDraw
import pyaudio
import struct
from math import sqrt

from config import VOLUME_DEVICE, VOLUME_MULTIPLY

SERVICE1 = "org.mpris.MediaPlayer2"
SERVICE2 = "org.mpris.MediaPlayer2.Player"

pa = pyaudio.PyAudio()

class MediaScreen(Screen):
    def __init__(self):
        self.vu = (0, 0)

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

        # overtake for 2 seconds if playback status changed
        if self.playback_status != status:
            self.playback_status = status
            return (True, 2)
        else:
            return (True, None)

    def draw(self, overtaking, image_draw: ImageDraw):
        # playback status
        if self.playback_status == "Playing":
            image_draw.polygon([(0, 0), (7, 3), (0, 7)], 1) # triangle
        elif self.playback_status == "Paused":
            image_draw.rectangle([(0, 0), (2, 7)], 1)
            image_draw.rectangle([(5, 0), (7, 7)], 1)
        elif self.playback_status == "stopped":
            image_draw.rectangle([(0, 0), (7, 7)], 1)

        # player, artist and title
        image_draw.text((63, 0), self.name, 1, anchor="mt") # player
        image_draw.text((63, 17), self.artist, 1, anchor="mt") # artist
        image_draw.text((63, 29), self.title, 1, anchor="mt") # title

        # progress bar and associated times
        if self.position is not None and self.length:
            image_draw.rectangle([(0, 56), (127, 63)], 0, 1) # progress bar frame
            image_draw.rectangle([(2, 58), (2 + (self.position * 123 / self.length), 61)], 1) # progress bar
            image_draw.text((0, 54), f"{self.position // 60_000_000}:{(self.position // 1_000_000) % 60 :02}", 1, anchor="lb") # playback position
            image_draw.text((127, 54), f"{self.length // 60_000_000}:{(self.length // 1_000_000) % 60 :02}", 1, anchor="rb") # song length
        
        # VU meter
        VU_MAX = 32
        if self.vu[0] > 1e-5:
            image_draw.rectangle([(62 - (VU_MAX * self.vu[0]), 48), (62, 52)], 1) # left bar
        if self.vu[1] > 1e-5:
            image_draw.rectangle([(64, 48), (64 + (VU_MAX * self.vu[1]), 52)], 1) # right bar
