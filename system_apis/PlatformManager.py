from system_apis.BasePlatformManagers import BaseMediaManager, BaseBackend
from packaging import version
import platform
import sys

REQUIRED_KERNEL_VERSION = "6.19.0"
REQUIRED_NT_VERSION = "10"


class PlatformManager:
    """
    Manages platform-specific operations and provides a unified interface for interacting with the underlying operating system.
    """
    backend: "BaseBackend"
    def __init__(self, contextManager):
        self.contextManager = contextManager
        
        if not self._is_supported():
            raise EnvironmentError(f"Unsupported platform: {platform.system()} {platform.release()}")
        
        if platform.system() == "Linux":
            from system_apis.Linux import LinuxBackend
            self.backend = LinuxBackend()
        elif platform.system() == "Windows":
            from system_apis.Windows import WindowsBackend
            self.backend = WindowsBackend()
            
        
        
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
