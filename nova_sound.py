"""
Nova Sound System Implementation

This module implements a hybrid register-based sound system for the Nova-16 computer.
It provides multiple waveforms, sound channels, and effects using pygame.mixer.

Sound Registers:
- SA: Sound Address (16-bit) - points to sound data in memory
- SF: Sound Frequency (8-bit) - base frequency (0-255)
- SV: Sound Volume (8-bit) - volume level (0-255)
- SW: Sound Waveform (8-bit) - waveform type and channel control

Instructions:
- SPLAY: Start playing sound on specified channel
- SSTOP: Stop sound on specified channel or all channels
- STRIG: Trigger sound effect or envelope

Waveforms:
0 = Silence
1 = Square wave
2 = Sine wave  
3 = Sawtooth wave
4 = Triangle wave
5 = White noise
6 = Pink noise
7 = Memory-based sample data

Channel Control (SW register bits):
- Bits 0-2: Waveform type (0-7)
- Bits 3-5: Channel number (0-7, allows 8 simultaneous sounds)
- Bit 6: Loop flag (0=one-shot, 1=loop)
- Bit 7: Enable flag (0=disabled, 1=enabled)
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
import pygame
import pygame.mixer
import threading
import time
import math
from typing import Dict, List, Optional, Tuple

class NovaSound:
    def __init__(self, sample_rate: int = 22050, buffer_size: int = 512, channels: int = 8):
        """
        Initialize the Nova Sound System
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: Audio buffer size for low latency
            channels: Maximum number of simultaneous sound channels
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.max_channels = channels
        
        # Initialize pygame mixer
        # pygame.mixer.pre_init(
        #     frequency=sample_rate,
        #     size=-16,  # 16-bit signed
        #     channels=2,  # Stereo
        #     buffer=buffer_size
        # )
        # pygame.mixer.init()
        
        # Sound registers (accessible via CPU)
        self.sound_registers = [0] * 4
        self.SA = 0  # Sound Address (16-bit)
        self.SF = 0  # Sound Frequency (8-bit, but stored as 16-bit for consistency)
        self.SV = 0  # Sound Volume (8-bit, but stored as 16-bit for consistency)
        self.SW = 0  # Sound Waveform and control (8-bit, but stored as 16-bit for consistency)
        
        # Sound channels
        self.sound_channels: List[Optional[pygame.mixer.Sound]] = [None] * self.max_channels
        self.channel_states: List[Dict] = [
            {
                'playing': False,
                'frequency': 440.0,
                'volume': 0.5,
                'waveform': 0,
                'loop': False,
                'phase': 0.0,
                'envelope': 1.0
            }
            for _ in range(self.max_channels)
        ]
        
        # Memory reference for sample data
        self.memory = None
        
        # Pre-generated waveform tables for efficiency
        # self.waveform_table_size = 1024
        # self.waveform_tables = self._generate_waveform_tables()
        
        # Sound effects and envelope system
        self.envelope_stages = ['attack', 'decay', 'sustain', 'release']
        self.default_envelope = {
            'attack_time': 0.1,
            'decay_time': 0.1, 
            'sustain_level': 0.7,
            'release_time': 0.2
        }
        
        # Background thread for continuous sound generation
        self.sound_thread_running = False
        self.sound_thread = None
        
        print("Nova Sound System initialized")
        print(f"Sample Rate: {sample_rate}Hz, Channels: {channels}, Buffer: {buffer_size}")
    
    def set_memory_reference(self, memory):
        """Set reference to system memory for sample data access"""
        self.memory = memory
    
    def _generate_waveform_tables(self) -> Dict[int, np.ndarray]:
        """Pre-generate waveform lookup tables for efficient sound synthesis"""
        tables = {}
        size = self.waveform_table_size
        
        # Generate one cycle of each waveform
        x = np.linspace(0, 2 * np.pi, size, dtype=np.float32)
        
        # Silence
        tables[0] = np.zeros(size, dtype=np.float32)
        
        # Square wave
        tables[1] = np.where(x < np.pi, 1.0, -1.0)
        
        # Sine wave
        tables[2] = np.sin(x)
        
        # Sawtooth wave
        tables[3] = 2.0 * (x / (2 * np.pi)) - 1.0
        
        # Triangle wave
        tables[4] = 2.0 * np.abs(2.0 * (x / (2 * np.pi)) - 1.0) - 1.0
        
        # White noise (generated fresh each time, this is just a template)
        tables[5] = np.random.uniform(-1.0, 1.0, size).astype(np.float32)
        
        # Pink noise (1/f noise approximation)
        white = np.random.uniform(-1.0, 1.0, size)
        # Simple pink noise filter (not perfect but adequate)
        pink = np.zeros_like(white)
        for i in range(1, len(white)):
            pink[i] = 0.99 * pink[i-1] + 0.01 * white[i]
        tables[6] = pink.astype(np.float32)
        
        return tables
    
    def _frequency_to_note_number(self, frequency: float) -> int:
        """Convert frequency in Hz to MIDI note number"""
        if frequency <= 0:
            return 0
        return max(0, min(127, int(69 + 12 * math.log2(frequency / 440.0))))
    
    def _register_to_frequency(self, reg_value: int) -> float:
        """Convert register value (0-255) to frequency in Hz"""
        if reg_value == 0:
            return 0.0
        # Map 0-255 to roughly 55Hz (A1) to 1760Hz (A6)
        # Using exponential mapping for musical intervals
        min_freq = 55.0   # A1
        max_freq = 1760.0 # A6
        normalized = reg_value / 255.0
        return min_freq * (max_freq / min_freq) ** normalized
    
    def _generate_waveform_sample(self, waveform_type: int, frequency: float, 
                                  duration: float, volume: float = 1.0) -> np.ndarray:
        """Generate a sample buffer for the specified waveform"""
        if frequency <= 0 or volume <= 0:
            return np.zeros(int(self.sample_rate * duration), dtype=np.float32)
        
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, dtype=np.float32)
        
        if waveform_type == 0:  # Silence
            return np.zeros(samples, dtype=np.float32)
        
        elif waveform_type in [1, 2, 3, 4]:  # Table-based waveforms
            # Use pre-generated tables with interpolation
            table = self.waveform_tables[waveform_type]
            phase_increment = frequency * len(table) / self.sample_rate
            phases = np.cumsum(np.full(samples, phase_increment)) % len(table)
            
            # Linear interpolation for smooth sound
            indices = phases.astype(int)
            fractions = phases - indices
            
            samples_out = table[indices] * (1 - fractions)
            samples_out += table[(indices + 1) % len(table)] * fractions
            
            return samples_out * volume
        
        elif waveform_type == 5:  # White noise
            return np.random.uniform(-volume, volume, samples).astype(np.float32)
        
        elif waveform_type == 6:  # Pink noise
            white = np.random.uniform(-1.0, 1.0, samples)
            pink = np.zeros_like(white)
            for i in range(1, len(white)):
                pink[i] = 0.99 * pink[i-1] + 0.01 * white[i]
            return (pink * volume).astype(np.float32)
        
        elif waveform_type == 7:  # Memory-based sample
            return self._load_sample_from_memory(duration, volume)
        
        else:
            # Unknown waveform, return silence
            return np.zeros(samples, dtype=np.float32)
    
    def _load_sample_from_memory(self, duration: float, volume: float = 1.0) -> np.ndarray:
        """Load sample data from memory starting at SA register address"""
        if self.memory is None or self.SA == 0:
            return np.zeros(int(self.sample_rate * duration), dtype=np.float32)
        
        # Read sample data from memory
        # Format: 8-bit unsigned samples, convert to float32 range [-1, 1]
        try:
            samples_needed = int(self.sample_rate * duration)
            memory_data = []
            
            for i in range(min(samples_needed, 1024)):  # Limit to prevent excessive memory reads
                addr = (self.SA + i) & 0xFFFF  # 16-bit address wrap
                sample_byte = self.memory.read_byte(addr)
                # Convert 8-bit unsigned (0-255) to float (-1 to 1)
                float_sample = (sample_byte / 127.5) - 1.0
                memory_data.append(float_sample)
            
            # If we need more samples, loop the data
            if len(memory_data) < samples_needed:
                loops = (samples_needed // len(memory_data)) + 1
                memory_data = (memory_data * loops)[:samples_needed]
            
            return np.array(memory_data, dtype=np.float32) * volume
            
        except Exception as e:
            print(f"Error loading sample from memory: {e}")
            return np.zeros(int(self.sample_rate * duration), dtype=np.float32)
    
    def update_registers(self, sa: int = None, sf: int = None, sv: int = None, sw: int = None):
        """Update sound registers (called by CPU during register writes)"""
        if sa is not None:
            self.SA = sa & 0xFFFF
            self.sound_registers[0] = self.SA
        
        if sf is not None:
            self.SF = sf & 0xFF
            self.sound_registers[1] = self.SF
        
        if sv is not None:
            self.SV = sv & 0xFF
            self.sound_registers[2] = self.SV
        
        if sw is not None:
            self.SW = sw & 0xFF
            self.sound_registers[3] = self.SW
    
    def get_register(self, register_name: str) -> int:
        """Get current value of a sound register"""
        register_map = {'SA': 0, 'SF': 1, 'SV': 2, 'SW': 3}
        if register_name in register_map:
            return int(self.sound_registers[register_map[register_name]])
        return 0
    
    def splay(self, channel: int = None) -> bool:
        """
        SPLAY instruction implementation
        Start playing sound on specified channel using current register values
        """
        # Extract channel from SW register if not specified
        if channel is None:
            channel = (self.SW >> 3) & 0x07  # Bits 3-5
        
        if channel >= self.max_channels:
            return False
        
        # Extract waveform and control flags
        waveform_type = self.SW & 0x07          # Bits 0-2
        loop_flag = bool(self.SW & 0x40)        # Bit 6
        enable_flag = bool(self.SW & 0x80)      # Bit 7
        
        if not enable_flag:
            return False
        
        # Convert register values to audio parameters
        frequency = self._register_to_frequency(self.SF)
        volume = self.SV / 255.0
        
        # Generate sound sample (0.5 second duration for one-shot, longer for loops)
        duration = 2.0 if loop_flag else 0.5
        sample_data = self._generate_waveform_sample(waveform_type, frequency, duration, volume)
        
        # Convert to stereo (duplicate mono to both channels)
        if len(sample_data) > 0:
            stereo_data = np.column_stack((sample_data, sample_data))
            
            # Convert to 16-bit integer format for pygame
            audio_data = (stereo_data * 32767).astype(np.int16)
            
            # Create pygame Sound object and play
            try:
                sound = pygame.mixer.Sound(audio_data)
                loops = -1 if loop_flag else 0  # -1 = infinite loop
                
                # Stop any existing sound on this channel
                if self.sound_channels[channel] is not None:
                    pygame.mixer.stop()
                
                # Play the new sound
                sound.play(loops=loops)
                self.sound_channels[channel] = sound
                
                # Update channel state
                self.channel_states[channel].update({
                    'playing': True,
                    'frequency': frequency,
                    'volume': volume,
                    'waveform': waveform_type,
                    'loop': loop_flag
                })
                
                return True
                
            except Exception as e:
                print(f"Error playing sound on channel {channel}: {e}")
                return False
        
        return False
    
    def sstop(self, channel: int = None) -> bool:
        """
        SSTOP instruction implementation
        Stop sound on specified channel, or all channels if channel is None
        """
        try:
            # Check if mixer is initialized before trying to stop sounds
            if not pygame.mixer.get_init():
                # Mixer not initialized, just reset our internal state
                for i in range(self.max_channels):
                    self.sound_channels[i] = None
                    self.channel_states[i]['playing'] = False
                return True
            
            if channel is None:
                # Stop all channels
                pygame.mixer.stop()
                for i in range(self.max_channels):
                    self.sound_channels[i] = None
                    self.channel_states[i]['playing'] = False
            else:
                if channel < self.max_channels:
                    # Stop specific channel
                    if self.sound_channels[channel] is not None:
                        self.sound_channels[channel].stop()
                        self.sound_channels[channel] = None
                        self.channel_states[channel]['playing'] = False
            
            return True
            
        except Exception as e:
            print(f"Error stopping sound: {e}")
            return False
    
    def strig(self, effect_type: int = 0) -> bool:
        """
        STRIG instruction implementation
        Trigger sound effects or envelope changes
        
        Effect types:
        0 = Simple beep
        1 = Rising tone
        2 = Falling tone  
        3 = Explosion effect
        4 = Laser shot
        5 = Jump sound
        6 = Coin pickup
        7 = Power-up
        """
        try:
            if effect_type == 0:  # Simple beep
                self._play_effect_beep()
            elif effect_type == 1:  # Rising tone
                self._play_effect_sweep(start_freq=200, end_freq=800, duration=0.3)
            elif effect_type == 2:  # Falling tone
                self._play_effect_sweep(start_freq=800, end_freq=200, duration=0.3)
            elif effect_type == 3:  # Explosion
                self._play_effect_explosion()
            elif effect_type == 4:  # Laser shot
                self._play_effect_laser()
            elif effect_type == 5:  # Jump
                self._play_effect_jump()
            elif effect_type == 6:  # Coin pickup
                self._play_effect_coin()
            elif effect_type == 7:  # Power-up
                self._play_effect_powerup()
            else:
                return False
            
            return True
            
        except Exception as e:
            print(f"Error triggering sound effect {effect_type}: {e}")
            return False
    
    def _play_effect_beep(self):
        """Play a simple beep sound"""
        frequency = 800
        duration = 0.2
        volume = 0.5
        sample_data = self._generate_waveform_sample(2, frequency, duration, volume)  # Sine wave
        self._play_sample_direct(sample_data)
    
    def _play_effect_sweep(self, start_freq: float, end_freq: float, duration: float):
        """Play a frequency sweep effect"""
        samples = int(self.sample_rate * duration)
        frequencies = np.linspace(start_freq, end_freq, samples)
        
        sample_data = np.zeros(samples, dtype=np.float32)
        phase = 0.0
        
        for i, freq in enumerate(frequencies):
            phase_increment = 2 * np.pi * freq / self.sample_rate
            sample_data[i] = np.sin(phase) * 0.5
            phase += phase_increment
        
        self._play_sample_direct(sample_data)
    
    def _play_effect_explosion(self):
        """Play an explosion sound effect using filtered noise"""
        duration = 0.8
        samples = int(self.sample_rate * duration)
        
        # Start with white noise
        noise = np.random.uniform(-1.0, 1.0, samples)
        
        # Apply envelope (sharp attack, long decay)
        envelope = np.exp(-np.linspace(0, 8, samples))
        
        # Apply low-pass filter effect (simple moving average)
        filtered = np.convolve(noise, np.ones(10)/10, mode='same')
        
        sample_data = (filtered * envelope * 0.7).astype(np.float32)
        self._play_sample_direct(sample_data)
    
    def _play_effect_laser(self):
        """Play a laser sound effect"""
        duration = 0.15
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Descending frequency with some modulation
        base_freq = 1200 * np.exp(-t * 8)
        modulation = 50 * np.sin(2 * np.pi * 30 * t)
        frequency = base_freq + modulation
        
        # Generate the waveform
        phase = np.cumsum(2 * np.pi * frequency / self.sample_rate)
        sample_data = (np.sin(phase) * 0.6).astype(np.float32)
        
        self._play_sample_direct(sample_data)
    
    def _play_effect_jump(self):
        """Play a jump sound effect"""
        duration = 0.25
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Rising then falling tone
        frequency = 400 + 300 * np.sin(np.pi * t / duration)
        phase = np.cumsum(2 * np.pi * frequency / self.sample_rate)
        
        # Square wave for retro feel
        sample_data = (np.sign(np.sin(phase)) * 0.4).astype(np.float32)
        
        self._play_sample_direct(sample_data)
    
    def _play_effect_coin(self):
        """Play a coin pickup sound effect"""
        # Two-tone ascending sound
        freq1, freq2 = 660, 880  # E5, A5
        duration = 0.15
        
        # First tone
        sample1 = self._generate_waveform_sample(2, freq1, duration, 0.5)
        # Second tone
        sample2 = self._generate_waveform_sample(2, freq2, duration, 0.5)
        
        # Concatenate
        sample_data = np.concatenate([sample1, sample2])
        self._play_sample_direct(sample_data)
    
    def _play_effect_powerup(self):
        """Play a power-up sound effect"""
        duration = 0.6
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples)
        
        # Ascending arpeggio-like effect
        base_freq = 220  # A3
        harmonics = [1, 1.25, 1.5, 2.0]  # Major triad progression
        
        sample_data = np.zeros(samples, dtype=np.float32)
        
        for i, harmonic in enumerate(harmonics):
            start_idx = i * samples // len(harmonics)
            end_idx = (i + 1) * samples // len(harmonics)
            length = end_idx - start_idx
            
            freq = base_freq * harmonic
            tone = self._generate_waveform_sample(2, freq, length / self.sample_rate, 0.3)
            
            if len(tone) > 0:
                sample_data[start_idx:start_idx + len(tone)] += tone[:end_idx - start_idx]
        
        self._play_sample_direct(sample_data)
    
    def _play_sample_direct(self, sample_data: np.ndarray):
        """Play a sample directly using pygame mixer"""
        if len(sample_data) == 0:
            return
        
        try:
            # Convert to stereo
            stereo_data = np.column_stack((sample_data, sample_data))
            # Convert to 16-bit integer
            audio_data = (stereo_data * 32767).astype(np.int16)
            
            # Create and play sound
            sound = pygame.mixer.Sound(audio_data)
            sound.play()
            
        except Exception as e:
            print(f"Error playing sample: {e}")
    
    def get_channel_status(self, channel: int) -> Dict:
        """Get the current status of a sound channel"""
        if 0 <= channel < self.max_channels:
            return self.channel_states[channel].copy()
        return {'playing': False}
    
    def get_all_channel_status(self) -> List[Dict]:
        """Get status of all sound channels"""
        return [state.copy() for state in self.channel_states]
    
    def cleanup(self):
        """Clean up sound system resources"""
        try:
            # Check if mixer is still initialized before trying to stop sounds
            if pygame.mixer.get_init():
                self.sstop()  # Stop all sounds
                pygame.mixer.quit()
                print("Nova Sound System cleaned up")
            else:
                print("Nova Sound System already cleaned up")
        except Exception as e:
            print(f"Error during sound cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass  # Ignore cleanup errors during destruction


# Example usage and testing functions
def test_sound_system():
    """Test the Nova Sound System functionality"""
    print("Testing Nova Sound System...")
    
    sound = NovaSound()
    
    # Test different waveforms
    waveforms = ['silence', 'square', 'sine', 'sawtooth', 'triangle', 'white noise', 'pink noise']
    
    for i, waveform_name in enumerate(waveforms[1:6], 1):  # Skip silence and memory sample
        print(f"Testing {waveform_name} wave...")
        
        # Set up registers for this waveform
        sound.update_registers(
            sa=0x1000,  # Sample address (not used for generated waveforms)
            sf=128,      # Mid-range frequency
            sv=128,      # Half volume
            sw=i | 0x80  # Waveform type + enable flag
        )
        
        # Play the sound
        if sound.splay():
            print(f"  ✓ {waveform_name} playing")
            time.sleep(1)  # Let it play
            sound.sstop()
            time.sleep(0.5)
        else:
            print(f"  ✗ Failed to play {waveform_name}")
    
    # Test sound effects
    print("\nTesting sound effects...")
    effects = ['beep', 'rising', 'falling', 'explosion', 'laser', 'jump', 'coin', 'powerup']
    
    for i, effect_name in enumerate(effects):
        print(f"Testing {effect_name} effect...")
        if sound.strig(i):
            print(f"  ✓ {effect_name} triggered")
            time.sleep(1)
        else:
            print(f"  ✗ Failed to trigger {effect_name}")
    
    print("\nSound system test complete!")
    sound.cleanup()


if __name__ == "__main__":
    # Initialize pygame for standalone testing
    import pygame
    pygame.init()
    
    # Run tests
    test_sound_system()
