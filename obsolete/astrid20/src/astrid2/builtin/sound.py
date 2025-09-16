"""
Astrid 2.0 Built-in Sound Functions
Provides hardware-accelerated sound operations for Nova-16.
"""

from typing import Dict, List, Any
from ..utils.logger import get_logger

logger = get_logger(__name__)


class SoundBuiltins:
    """Built-in sound functions for Astrid 2.0."""

    def __init__(self):
        self.functions = {
            'play_tone': self._play_tone,
            'stop_channel': self._stop_channel,
            'set_volume': self._set_volume,
            'set_waveform': self._set_waveform,
            'play_sample': self._play_sample,
            'set_master_volume': self._set_master_volume,
            'set_channel_pan': self._set_channel_pan,
        }

    def get_function(self, name: str):
        """Get a built-in function by name."""
        return self.functions.get(name)

    def _play_tone(self, frequency: int, volume: int, channel: int = 0) -> str:
        """
        Play a tone on the specified channel.

        Args:
            frequency: Frequency in Hz
            volume: Volume (0-255)
            channel: Sound channel (0-7), defaults to 0

        Returns:
            Assembly code for playing the tone
        """
        return f"""
; Play tone on channel {channel}: {frequency}Hz, vol={volume}, wave=square
MOV SA, {channel * 8}        ; Channel {channel} base address
MOV SF, {frequency}          ; Set frequency
MOV SV, {volume}             ; Set volume
MOV SW, 0                    ; Set waveform (square)
SPLAY                        ; Start playback
"""

    def _stop_channel(self, channel: int) -> str:
        """
        Stop playback on the specified channel.

        Args:
            channel: Sound channel (0-7)

        Returns:
            Assembly code for stopping the channel
        """
        return f"""
; Stop channel {channel}
MOV SA, {channel * 8}        ; Channel {channel} base address
SSTOP                        ; Stop playback
"""

    def _set_volume(self, channel: int, volume: int) -> str:
        """
        Set the volume for the specified channel.

        Args:
            channel: Sound channel (0-7)
            volume: Volume (0-255)

        Returns:
            Assembly code for setting volume
        """
        return f"""
; Set channel {channel} volume to {volume}
MOV SA, {channel * 8}        ; Channel {channel} base address
MOV SV, {volume}             ; Set volume
"""

    def _set_waveform(self, channel: int, waveform: str) -> str:
        """
        Set the waveform for the specified channel.

        Args:
            channel: Sound channel (0-7)
            waveform: Waveform type ('square', 'sine', 'sawtooth', 'triangle', 'noise')

        Returns:
            Assembly code for setting waveform
        """
        waveform_map = {
            'square': 0,
            'sine': 1,
            'sawtooth': 2,
            'triangle': 3,
            'noise': 4
        }

        wave_value = waveform_map.get(waveform.lower(), 0)

        return f"""
; Set channel {channel} waveform to {waveform}
MOV SA, {channel * 8}        ; Channel {channel} base address
MOV SW, {wave_value}         ; Set waveform
"""

    def _play_sample(self, channel: int, sample_address: int, volume: int = 128) -> str:
        """
        Play a sample from memory on the specified channel.

        Args:
            channel: Sound channel (0-7)
            sample_address: Memory address of the sample
            volume: Volume (0-255)

        Returns:
            Assembly code for playing the sample
        """
        return f"""
; Play sample on channel {channel} from address 0x{sample_address:04X}
MOV SA, {channel * 8}        ; Channel {channel} base address
MOV P0, 0x{sample_address:04X}  ; Sample address
MOV SF, 0                    ; Sample mode (frequency = 0)
MOV SV, {volume}             ; Set volume
MOV SW, 5                    ; Sample waveform
SPLAY                        ; Start playback
"""

    def _set_master_volume(self, volume: int) -> str:
        """
        Set the master volume for all sound channels.

        Args:
            volume: Master volume (0-255)

        Returns:
            Assembly code for setting master volume
        """
        return f"""
; Set master volume to {volume}
MOV R0, {volume}
SMASTER R0
"""

    def _set_channel_pan(self, channel: int, pan: int) -> str:
        """
        Set the pan position for the specified channel.

        Args:
            channel: Sound channel (0-7)
            pan: Pan position (0=left, 64=center, 127=right)

        Returns:
            Assembly code for setting pan
        """
        return f"""
; Set channel {channel} pan to {pan}
MOV SA, {channel * 8}        ; Channel {channel} base address
MOV R0, {pan}
SPAN R0
"""


# Global instance for use by the compiler
sound_builtins = SoundBuiltins()
