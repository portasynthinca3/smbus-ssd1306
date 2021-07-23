from config import *
import os, dbus

class MediaGetter:
    def __init__(self, provider):
        self.dbus = dbus.SessionBus()
        self.media_bus = self.dbus.get_object(f"org.mpris.MediaPlayer2.{provider}", "/org/mpris/MediaPlayer2")
        self.iface = dbus.Interface(self.media_bus, "org.freedesktop.DBus.Properties")

    def get_song(self):
        meta = self.iface.Get("org.mpris.MediaPlayer2.Player", "Metadata")
        pos = int(self.iface.Get("org.mpris.MediaPlayer2.Player", "Position"))
        artist = meta.get("xesam:albumArtist")
        if artist == None:
            artist = meta.get("xesam:artist")
        if artist != None:
            try:
                artist = str(next(iter(artist)))
            except StopIteration:
                artist = None
        rating = meta.get("xesam:autoRating")
        length = meta.get("mpris:length")
        return (artist,
                str(meta.get("xesam:title")),
                int(length) if length != None else None,
                pos,
                float(rating) if rating != None else None)

def get_song():
    song = None
    for prov in MEDIA_PROVIDERS:
        try:
            song = MediaGetter(prov).get_song()
        except dbus.exceptions.DBusException:
            pass
    if song == None:
        return None
    else:
        return song