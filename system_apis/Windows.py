from system_apis.PlatformManagers import BaseMediaManager, BaseBackend
import pycaw.pycaw as pycaw
from ctypes import POINTER, cast
from comtypes import CLSCTX_ALL

REQUIRED_NT_VERSION = "10"


class WindowsMediaManager(BaseMediaManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def volume_set(self, level: int) -> bool:
        try:
            pycaw.SetMasterVolume(level / 100.0)
            return True
        except Exception:
            return False
        pass

    def _volume_get(self) -> int | None:
        try:
            p = pycaw.AudioUtilities.GetSpeakers()
            interface = p.Activate(pycaw.IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(pycaw.IAudioEndpointVolume))
            current_volume = volume.GetMasterVolumeLevelScalar()
            return int(current_volume * 100)
        except Exception:
            return None

    def mute(self) -> bool:
        try:
            p = pycaw.AudioUtilities.GetSpeakers()
            interface = p.Activate(pycaw.IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(pycaw.IAudioEndpointVolume))
            volume.SetMute(1, None)
            return True
        except Exception:
            return False

    def unmute(self) -> bool:
        try:
            p = pycaw.AudioUtilities.GetSpeakers()
            interface = p.Activate(pycaw.IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(pycaw.IAudioEndpointVolume))
            volume.SetMute(0, None)
            return True
        except Exception:
            return False

    def is_muted(self) -> bool | None:
        try:
            p = pycaw.AudioUtilities.GetSpeakers()
            interface = p.Activate(pycaw.IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(pycaw.IAudioEndpointVolume))
            return volume.GetMute() == 1
        except Exception:
            return None
        pass

    def volume_up(self, increment: int) -> bool:
        current_volume = self._volume_get()
        if current_volume is not None:
            return self.volume_set(min(current_volume + increment, 100))
        return False

    def volume_down(self, decrement: int) -> bool:
        current_volume = self._volume_get()
        if current_volume is not None:
            return self.volume_set(max(current_volume - decrement, 0))
        return False

    def previous_track(self) -> bool:
        try:
            pycaw.MediaControl.previous()
            return True
        except Exception:
            return False

    def next_track(self) -> bool:
        try:
            pycaw.MediaControl.next()
            return True
        except Exception:
            return False

    def pause(self) -> bool:
        try:
            pycaw.MediaControl.pause()
            return True
        except Exception:
            return False

    def play(self) -> bool:
        try:
            pycaw.MediaControl.play()
            return True
        except Exception:
            return False


class WindowsBackend(BaseBackend):
    def __init__(self) -> None:
        self.media = WindowsMediaManager()
