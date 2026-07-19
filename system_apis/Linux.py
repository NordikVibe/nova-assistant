from system_apis.BasePlatformManagers import BaseMediaManager, BaseBackend
import subprocess




class LinuxMediaManager(BaseMediaManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def volume_set(self, level: int) -> bool:
        try:
            subprocess.run(f"pactl set-sink-volume @DEFAULT_SINK@ {level}%")
        except subprocess.SubprocessError:
            return False
        return True

    def _volume_get(self) -> int | None:
        try:
            result = subprocess.run(
                "pactl get-sink-volume @DEFAULT_SINK@", capture_output=True, text=True
            )
            output = result.stdout
            volume_line = output.splitlines()[0]
            volume_percentage = volume_line.split()[4]
            return int(volume_percentage.strip("%"))
        except (subprocess.SubprocessError, IndexError):
            return None

    def mute(self) -> bool:
        try:
            subprocess.run("pactl set-sink-mute @DEFAULT_SINK@ 1")
            return True
        except subprocess.SubprocessError:
            return False

    def unmute(self) -> bool:
        try:
            subprocess.run("pactl set-sink-mute @DEFAULT_SINK@ 0")
            return True
        except subprocess.SubprocessError:
            return False

    def is_muted(self) -> bool | None:
        try:
            result = subprocess.run(
                "pactl get-sink-mute @DEFAULT_SINK@", capture_output=True, text=True
            )
            output = result.stdout
            mute_line = output.splitlines()[0]
            return "yes" in mute_line
        except (subprocess.SubprocessError, IndexError):
            return None

    def volume_up(self, increment: int) -> bool:
        current_volume = self._volume_get()
        if current_volume is not None and 0 <= current_volume + increment <= 100:
            return self.volume_set(current_volume + increment)
        return self.volume_set(self._volume_get() + increment)

    def volume_down(self, decrement: int) -> bool:
        current_volume = self._volume_get()
        if current_volume is not None and 0 <= current_volume - decrement <= 100:
            return self.volume_set(current_volume - decrement)
        return self.volume_set(0)

    def previous_track(self) -> bool:
        try:
            subprocess.run(["playerctl", "previous"])
            return True
        except subprocess.SubprocessError:
            return False

    def next_track(self) -> bool:
        try:
            subprocess.run(["playerctl", "next"])
            return True
        except subprocess.SubprocessError:
            return False

    def pause(self) -> bool:
        try:
            subprocess.run(["playerctl", "pause"])
            return True
        except subprocess.SubprocessError:
            return False

    def resume(self) -> bool:
        try:
            subprocess.run(["playerctl", "play"])
            return True
        except subprocess.SubprocessError:
            return False


class LinuxBackend(BaseBackend):
    def __init__(self) -> None:
        self.media = LinuxMediaManager()
