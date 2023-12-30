from . import Screen
from dbus import SessionBus, Interface
from PIL.ImageDraw import ImageDraw

SERVICE1 = "org.mpris.MediaPlayer2"
SERVICE2 = "org.mpris.MediaPlayer2.Player"

class MediaScreen(Screen):
    def __init__(self):
        self.playback_status = None
        self.update(None)

    def get_player_iface(self, name):
        obj = SessionBus().get_object(name, "/org/mpris/MediaPlayer2")
        return Interface(obj, "org.freedesktop.DBus.Properties")

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
