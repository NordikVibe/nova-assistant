from abc import ABC, abstractmethod

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
    """
    Base class for platform-specific backend implementations.
    """
    media: BaseMediaManager
    def __init__(self):
        self.media = None