from system_apis.Linux import LinuxBackend, REQUIRED_KERNEL_VERSION
from system_apis.Windows import WindowsBackend, REQUIRED_NT_VERSION
from abc import ABC, abstractmethod
from packaging import version
import platform
import sys

class PlatformManager:
    backend: "BaseBackend"
    def __init__(self, contextManager):
        self.contextManager = contextManager
        
        if not self._is_supported():
            raise EnvironmentError(f"Unsupported platform: {platform.system()} {platform.release()}")
        
        self.backend = LinuxBackend() if platform.system() == "Linux" else WindowsBackend() if platform.system() == "Windows" else None
    
    @property
    def media(self) -> "BaseMediaManager":
        return self.backend.media

    def get_platform_info(self) -> dict[str, str]:
        """
        Returns information about the platform.

        {
            "platform": "Linux" or "Windows"
        }
        """
        return {
            "platform": platform.system(),
            "version": platform.version(),
        }

    def _is_supported(self) -> bool:
        """
        Checks if the current platform is supported.
        """
        if platform.system() == "Linux":
            clean_version = platform.release().split('-')[0].split(' ')[0]
        
            if version.parse(clean_version) < version.parse(REQUIRED_KERNEL_VERSION):
                return False
            else:
                return True
        elif platform.system() == "Windows":
            v = sys.getwindowsversion()
            if v.major < int(REQUIRED_NT_VERSION):
                return False
            else:
                return True
        else:
            return False
class BaseMediaManager(ABC):  
    @abstractmethod
    def volume_set(self, volume_level: int) -> bool:
        """
        Sets the system volume to the specified level.
        """
        pass
    @abstractmethod
    def _volume_get(self) -> int | None:
        """
        Gets the current system volume level.
        """
        pass
    @abstractmethod
    def mute(self) -> bool:
        """
        Mutes the system audio.
        """
        pass
    @abstractmethod
    def unmute(self) -> bool:
        """
        Unmutes the system audio.
        """
        pass
    @abstractmethod
    def is_muted(self) -> bool | None:
        """
        Checks if the system audio is muted.
        """
        pass
    @abstractmethod
    def volume_up(self, increment: int) -> bool:
        """
        Increases the system volume by the specified increment.
        """
        pass
    @abstractmethod
    def volume_down(self, decrement: int) -> bool:
        """
        Decreases the system volume by the specified decrement.
        """
        pass
    @abstractmethod
    def previous_track(self) -> bool:
        """
        Goes back to the previous media track.
        """
        pass
    @abstractmethod
    def next_track(self) -> bool:
        """
        Skips to the next media track.
        """
        pass
    @abstractmethod
    def pause(self) -> bool:
        """
        Pauses the currently playing media.
        """
        pass
    @abstractmethod
    def resume(self) -> bool:
        """
        Resumes the currently playing media.
        """
        pass

class BaseBackend:
    media: BaseMediaManager
    def __init__(self):
        self.media = None