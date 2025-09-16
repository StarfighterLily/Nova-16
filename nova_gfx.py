import numpy as np
from font import font_data

class GFX:
    def __init__( self, width = 256, height = 256 ):
        self.width = width
        self.height = height
        self.screen = np.zeros( ( self.height, self.width ), dtype=np.uint8 )
        self.Vregisters = np.zeros( 3, dtype=np.uint8 )  # VX, VY, VM (video mode)
        # Keep vmode for backward compatibility, but it will sync with Vregisters[2]
        self.vmode = 0
        self.vram = np.zeros( ( self.height, self.width ), dtype=np.uint8 )
        self.flags = np.zeros( 3, dtype=np.uint8 )
        self.flags[ 2 ] = 0 # VMode flag (M), set to 1 if the VMode is set to Coordinate mode
        self.flags[ 1 ] = 0 # VBlank flag (V), set to 1 if the VBlank period has started
        self.flags[ 0 ] = 0 # HBlank flag (H), set to 1 if the HBlank period has started
        
        # Video layers system
        self.VL = 0  # Video Layer register (0 = main screen, 1-4 = BG layers, 5-8 = Sprite layers)
        self.current_layer = 0  # Current active layer (same as VL initially)
        self.background_layers = [np.zeros((self.height, self.width), dtype=np.uint8) for _ in range(4)]  # BG layers 1-4
        self.sprite_layers = [np.zeros((self.height, self.width), dtype=np.uint8) for _ in range(4)]      # Sprite layers 5-8
        
        # Layer compositing optimization
        self.layers_dirty = False  # Track if layers need recompositing
        self.auto_composite = True  # Automatically composite when accessing screen
        
        # Layer visibility controls
        self.layer_visibility = {i: True for i in range(9)}  # All layers visible by default
        
        # Graphics blending system
        self.blend_mode = 0      # 0=normal, 1=add, 2=subtract, 3=multiply, 4=screen
        self.blend_alpha = 255   # Alpha/intensity for blending (0-255)
        
        # Graphics optimization - batching and dirty region tracking
        self.graphics_batch_counter = 0
        self.graphics_batch_frequency = 4  # Batch every 4 operations
        self.pending_vram_to_screen = False
        self.pending_screen_to_vram = False
        
        # Sprite System - Memory-mapped sprite control blocks
        # 16 sprites × 16 bytes each = 256 bytes (0xF000-0xF0FF)
        self.sprite_count = 16
        self.sprite_block_size = 16
        self.sprite_memory_base = 0xF000
        self.sprite_memory_end = 0xF0FF
        
        # Sprite data structure (per sprite):
        # Offset 0-1: Data address (16-bit, big-endian)
        # Offset 2: X position (8-bit)
        # Offset 3: Y position (8-bit) 
        # Offset 4: Width (8-bit)
        # Offset 5: Height (8-bit)
        # Offset 6: Flags (8-bit) - bit 0: active, bit 1: transparency enabled, bit 7: layer (0=sprite layer 5, 1=sprite layer 6)
        # Offset 7: Transparency color (8-bit)
        # Offset 8-15: Reserved for future use
        
        # Sprite rendering optimization
        self.sprites_dirty = False  # Track if sprites need re-rendering

    @property
    def vmode(self):
        """Video mode - now uses VM register (Vregisters[2])"""
        return int(self.Vregisters[2])
    
    @vmode.setter
    def vmode(self, value):
        """Set video mode through VM register (Vregisters[2])"""
        self.Vregisters[2] = value & 0xFF

    def blend_pixel(self, existing, new):
        """Apply current blend mode to combine existing and new pixel values"""
        # Ensure inputs are in valid range and use float for calculations
        existing = max(0, min(255, int(existing)))
        new = max(0, min(255, int(new)))
        alpha = max(0, min(255, int(self.blend_alpha))) / 255.0
        
        if self.blend_mode == 0:  # Normal (overwrite)
            return new
        elif self.blend_mode == 1:  # Additive
            result = existing + (new * alpha)
            return min(255, int(result))
        elif self.blend_mode == 2:  # Subtractive
            result = existing - (new * alpha)
            return max(0, int(result))
        elif self.blend_mode == 3:  # Multiply
            result = (existing * new * alpha) / 255.0
            return min(255, int(result))
        elif self.blend_mode == 4:  # Screen
            # Screen: 1 - (1-a) * (1-b)
            inv_existing = 255 - existing
            inv_new = 255 - new
            result = 255 - (inv_existing * inv_new * alpha) / 255.0
            return min(255, int(result))
        else:
            return new  # Default to normal

    def clear( self ):
        self.screen.fill( 0 )

    def VRAMtoScreen( self ):
        """Optimized VRAM to Screen transfer with batching"""
        # Mark operation as pending for batching
        self.pending_vram_to_screen = True
        
        # Increment batch counter
        self.graphics_batch_counter += 1
        
        # Only execute if we've reached batch frequency or immediate execution needed
        if self.graphics_batch_counter >= self.graphics_batch_frequency:
            self._execute_batched_operations()
        else:
            # For immediate responsiveness, still do the copy but skip expensive simulations
            self.screen[:, :] = self.vram[:, :]
            self.vram.fill( 0 )

    def _execute_batched_operations(self):
        """Execute all pending graphics operations in a batch"""
        self.graphics_batch_counter = 0  # Reset counter
        
        # Simulate VBlank only once per batch
        self.flags[ 1 ] = 1  # Set VBlank flag at start
        
        if self.pending_vram_to_screen:
            # Vectorized operation: copy entire VRAM to screen in one operation
            self.screen[:, :] = self.vram[:, :]
            self.vram.fill( 0 )
            self.pending_vram_to_screen = False
            
        if self.pending_screen_to_vram:
            # Vectorized operation: copy entire screen to VRAM in one operation
            self.vram[:, :] = self.screen[:, :]
            self.screen.fill( 0 )
            self.pending_screen_to_vram = False
        
        # Skip expensive HBlank simulation entirely for batched operations
        self.flags[ 1 ] = 0  # Clear VBlank flag at end

    def ScreenToVRAM( self ):
        """Optimized Screen to VRAM transfer with batching"""
        # Mark operation as pending for batching
        self.pending_screen_to_vram = True
        
        # Increment batch counter
        self.graphics_batch_counter += 1
        
        # Only execute if we've reached batch frequency or immediate execution needed
        if self.graphics_batch_counter >= self.graphics_batch_frequency:
            self._execute_batched_operations()
        else:
            # For immediate responsiveness, still do the copy but skip expensive simulations
            self.vram[:, :] = self.screen[:, :]
            self.screen.fill( 0 )

    def set_registers( self, registers ):
        self.registers = registers

    def get_registers( self ):
        return self.registers

    def set_vmode( self, vmode ):
        self.vmode = vmode

    def get_vmode( self ):
        return self.vmode

    def set_vram( self, vram ):
        self.vram = vram

    def get_vram( self ):
        return self.vram

    def set_flags( self, flags ):
        self.flags = flags

    def get_flags( self ):
        return self.flags
    
    def get_target_layer( self ):
        """Get the target layer buffer based on VL register value"""
        if self.VL == 0:
            return self.screen  # Main screen
        elif 1 <= self.VL <= 4:
            return self.background_layers[self.VL - 1]  # Background layers
        elif 5 <= self.VL <= 8:
            return self.sprite_layers[self.VL - 5]  # Sprite layers
        else:
            return self.screen  # Default to main screen for invalid values
    
    def clear_layer( self, layer_num=None ):
        """Clear a specific layer or the current VL layer"""
        if layer_num is None:
            layer_num = self.VL
        
        if layer_num == 0:
            self.screen.fill(0)
        elif 1 <= layer_num <= 4:
            self.background_layers[layer_num - 1].fill(0)
            self.layers_dirty = True
        elif 5 <= layer_num <= 8:
            self.sprite_layers[layer_num - 5].fill(0)
            self.layers_dirty = True
    
    def fill_layer( self, value, layer_num=None ):
        """Fill a specific layer or the current VL layer with a value"""
        if layer_num is None:
            layer_num = self.VL
        
        if layer_num == 0:
            self.screen.fill(value)
        elif 1 <= layer_num <= 4:
            self.background_layers[layer_num - 1].fill(value)
            self.layers_dirty = True
        elif 5 <= layer_num <= 8:
            self.sprite_layers[layer_num - 5].fill(value)
            self.layers_dirty = True
    
    def copy_layer( self, src_layer, dst_layer ):
        """Copy contents from one layer to another"""
        src_buffer = self.get_layer_buffer_by_num(src_layer)
        dst_buffer = self.get_layer_buffer_by_num(dst_layer)
        if src_buffer is not None and dst_buffer is not None:
            dst_buffer[:] = src_buffer[:]
    
    def get_layer_buffer_by_num( self, layer_num ):
        """Get layer buffer by layer number"""
        if layer_num == 0:
            return self.screen
        elif 1 <= layer_num <= 4:
            return self.background_layers[layer_num - 1]
        elif 5 <= layer_num <= 8:
            return self.sprite_layers[layer_num - 5]
        else:
            return None
    
    def set_layer_visibility( self, layer_num, visible ):
        """Set layer visibility for compositing (Phase 2 advanced feature)"""
        # For now, just store visibility state - we could extend this later
        if not hasattr(self, 'layer_visibility'):
            self.layer_visibility = {}
        self.layer_visibility[layer_num] = visible

    def set_screen( self, screen ):
        self.screen = screen
    
    def get_screen( self ):
        # Lazy compositing: only composite if layers are dirty and auto_composite is enabled
        if self.auto_composite and self.layers_dirty:
            self.composite_layers()
            self.layers_dirty = False
        return self.screen
    
    # Layer Management Methods
    
    def set_layer_visibility(self, layer, visible):
        """Set layer visibility for compositing"""
        if 0 <= layer <= 8:
            self.layer_visibility[layer] = visible
            self.layers_dirty = True  # Mark for recompositing
    
    def get_layer_visibility(self, layer):
        """Get layer visibility status"""
        if 0 <= layer <= 8:
            return self.layer_visibility[layer]
        return False
    
    def copy_layer(self, source_layer, dest_layer):
        """Copy contents from one layer to another"""
        if source_layer == dest_layer:
            return
            
        source_data = None
        if source_layer == 0:
            source_data = self.screen.copy()
        elif 1 <= source_layer <= 4:
            source_data = self.background_layers[source_layer - 1].copy()
        elif 5 <= source_layer <= 8:
            source_data = self.sprite_layers[source_layer - 5].copy()
        
        if source_data is not None:
            if dest_layer == 0:
                self.screen[:] = source_data
            elif 1 <= dest_layer <= 4:
                self.background_layers[dest_layer - 1][:] = source_data
            elif 5 <= dest_layer <= 8:
                self.sprite_layers[dest_layer - 5][:] = source_data
            
            self.layers_dirty = True
    
    def set_current_layer(self, layer):
        """Set the current graphics layer (0=screen, 1-4=background, 5-8=sprite)"""
        self.current_layer = layer & 0x0F  # Mask to 4 bits (0-15, but only 0-8 are valid)
        self.VL = self.current_layer  # Keep VL in sync
    
    def get_current_layer(self):
        """Get the current graphics layer"""
        return self.current_layer
    
    def clear_layer(self, layer=None):
        """Clear a specific layer or the current layer"""
        if layer is None:
            layer = self.current_layer
        
        if layer == 0:
            self.screen.fill(0)
        elif 1 <= layer <= 4:
            self.background_layers[layer - 1].fill(0)
        elif 5 <= layer <= 8:
            self.sprite_layers[layer - 5].fill(0)
    
    def composite_layers(self):
        """Composite all visible layers into the main screen buffer"""
        # Start with a clear screen
        self.screen.fill(0)
        
        # Add background layers (1-4) first
        for i, layer in enumerate(self.background_layers):
            layer_num = i + 1
            if self.layer_visibility.get(layer_num, True):  # Check visibility
                mask = layer != 0  # Non-zero pixels are opaque
                self.screen[mask] = layer[mask]
        
        # Add sprite layers (5-8) on top
        for i, layer in enumerate(self.sprite_layers):
            layer_num = i + 5
            if self.layer_visibility.get(layer_num, True):  # Check visibility
                mask = layer != 0  # Non-zero pixels are opaque
                self.screen[mask] = layer[mask]
        
        # Mark layers as clean
        self.layers_dirty = False
    
    def get_vram_val( self ):
        if self.vmode == 1:
            # Direct memory access: Vregisters[0] = VX (high byte), Vregisters[1] = VY (low byte)
            addr = int( self.Vregisters[ 1 ] ) | ( int( self.Vregisters[ 0 ] ) << 8 )
            if 0 <= addr < self.width * self.height:
                x = addr % self.width
                y = addr // self.width
                return self.screen[ y, x ]
            else:
                raise IndexError( f"Screen address out of range: {addr}" )
        elif self.vmode == 0:
            # Coordinate mode: Vregisters[0] = x, Vregisters[1] = y
            x = int( self.Vregisters[ 0 ] )
            y = int( self.Vregisters[ 1 ] )
            if 0 <= x < self.width and 0 <= y < self.height:
                return self.screen[ y, x ]
            else:
                raise IndexError( f"Screen coordinates out of range: x={x}, y={y}" )
        else:
            raise ValueError( f"Unknown vmode: {self.vmode}" )

    def set_vram_val( self, value ):
        if self.vmode == 1:
            # Direct memory access: Vregisters[0] = VX (high byte), Vregisters[1] = VY (low byte)
            addr = int( self.Vregisters[ 1 ] ) | ( int( self.Vregisters[ 0 ] ) << 8 )
            if 0 <= addr < self.width * self.height:
                x = addr % self.width
                y = addr // self.width
                self.vram[ y, x ] = value
            else:
                raise IndexError( f"Screen address out of range: {addr}" )
        elif self.vmode == 0:
            # Coordinate mode: Vregisters[0] = x, Vregisters[1] = y
            x = int( self.Vregisters[ 0 ] )
            y = int( self.Vregisters[ 1 ] )
            if 0 <= x < self.width and 0 <= y < self.height:
                self.vram[ y, x ] = value
            else:
                raise IndexError( f"Screen coordinates out of range: x={x}, y={y}" )
        else:
            raise ValueError( f"Unknown vmode: {self.vmode}" )

    def get_screen_val( self ):
        if self.vmode == 1:
            # Direct memory access: Vregisters[0] = VX (high byte), Vregisters[1] = VY (low byte)
            addr = int( self.Vregisters[ 1 ] ) | ( int( self.Vregisters[ 0 ] ) << 8 )
            if 0 <= addr < self.width * self.height:
                x = addr % self.width
                y = addr // self.width
                return self.screen[ y, x ]
            else:
                raise IndexError( f"Screen address out of range: {addr}" )
        elif self.vmode == 0:
            # Coordinate mode: Vregisters[0] = x, Vregisters[1] = y
            x = int( self.Vregisters[ 0 ] )
            y = int( self.Vregisters[ 1 ] )
            if 0 <= x < self.width and 0 <= y < self.height:
                return self.screen[ y, x ]
            else:
                raise IndexError( f"Screen coordinates out of range: x={x}, y={y}" )
        else:
            raise ValueError( f"Unknown vmode: {self.vmode}" )

    def set_screen_val( self, value ):
        if self.vmode == 1:
            # Linear addressing mode
            addr = int( self.Vregisters[ 1 ] ) | ( int( self.Vregisters[ 0 ] ) << 8 )
            if 0 <= addr < (self.width * self.height):  # Total pixels, not just first dimension
                x = addr % self.width
                y = addr // self.width
                if 0 <= x < self.width and 0 <= y < self.height:
                    self._set_pixel_to_layer(x, y, value)
        else:
            # Coordinate mode: Vregisters[0] = x, Vregisters[1] = y
            x = int( self.Vregisters[ 0 ] )
            y = int( self.Vregisters[ 1 ] )
            if 0 <= x < self.width and 0 <= y < self.height:
                self._set_pixel_to_layer(x, y, value)
    
    def _set_pixel_to_layer(self, x, y, value):
        """Set a pixel to the current layer specified by VL register with blending"""
        if self.VL == 0:
            # Write to main screen with blending
            existing = self.screen[y, x]
            blended = self.blend_pixel(existing, value)
            self.screen[y, x] = blended
        elif 1 <= self.VL <= 4:
            # Write to background layer with blending
            existing = self.background_layers[self.VL - 1][y, x]
            blended = self.blend_pixel(existing, value)
            self.background_layers[self.VL - 1][y, x] = blended
            self.layers_dirty = True  # Mark layers as needing recomposition
        elif 5 <= self.VL <= 8:
            # Write to sprite layer with blending
            existing = self.sprite_layers[self.VL - 5][y, x]
            blended = self.blend_pixel(existing, value)
            self.sprite_layers[self.VL - 5][y, x] = blended
            self.layers_dirty = True  # Mark layers as needing recomposition

    def roll_x( self, roll_x ):
        # Roll the screen by roll_x pixels, pixels roll over to the opposite side
        self.screen = np.roll( self.screen, roll_x, axis=1 )

    def roll_y( self, roll_y ):
        # Roll the screen by roll_y pixels, pixels roll over to the opposite side
        self.screen = np.roll( self.screen, roll_y, axis=0 )

    def shift_x( self, shift_x ):
        # Shift the screen by shift_x pixels, pixels that roll over are erased (set to 0)
        if shift_x > 0:
            self.screen[ :, shift_x: ] = self.screen[ :, :-shift_x ]
            self.screen[ :, :shift_x ] = 0
        elif shift_x < 0:
            self.screen[ :, :shift_x ] = self.screen[ :, -shift_x: ]
            self.screen[ :, shift_x: ] = 0
        # If shift_x == 0, do nothing

    def shift_y( self, shift_y ):
        # Shift the screen by shift_y pixels, pixels that roll over are erased (set to 0)
        if shift_y > 0:
            self.screen[ shift_y:, : ] = self.screen[ :-shift_y, : ]
            self.screen[ :shift_y, : ] = 0
        elif shift_y < 0:
            self.screen[ :shift_y, : ] = self.screen[ -shift_y:, : ]
            self.screen[ shift_y:, : ] = 0
        # If shift_y == 0, do nothing

    def rotate_r( self, times ):
        # Rotate the screen 90 degrees clockwise
        self.screen = np.rot90( self.screen, times, axes=(1,0) )

    def rotate_l( self, times ):
        # Rotate the screen 90 degrees counter-clockwise
        self.screen = np.rot90( self.screen, times, axes=(0,1) )
    
    def flip_x( self ):
        # Flip the screen horizontally
        self.screen = np.flip( self.screen, axis=1 )

    def flip_y( self ):
        # Flip the screen vertically
        self.screen = np.flip( self.screen, axis=0 )
    
    # Layer-aware transform operations for Phase 2
    def roll_x_layer( self, roll_x, layer_num=None ):
        """Roll a specific layer or current VL layer horizontally"""
        if layer_num is None:
            layer_num = self.VL
        
        target_buffer = self.get_layer_buffer_by_num(layer_num)
        if target_buffer is not None:
            target_buffer[:] = np.roll(target_buffer, roll_x, axis=1)
            if layer_num != 0:
                self.layers_dirty = True
    
    def roll_y_layer( self, roll_y, layer_num=None ):
        """Roll a specific layer or current VL layer vertically"""
        if layer_num is None:
            layer_num = self.VL
        
        target_buffer = self.get_layer_buffer_by_num(layer_num)
        if target_buffer is not None:
            target_buffer[:] = np.roll(target_buffer, roll_y, axis=0)
            if layer_num != 0:
                self.layers_dirty = True
    
    def flip_x_layer( self, layer_num=None ):
        """Flip a specific layer or current VL layer horizontally"""
        if layer_num is None:
            layer_num = self.VL
        
        target_buffer = self.get_layer_buffer_by_num(layer_num)
        if target_buffer is not None:
            target_buffer[:] = np.flip(target_buffer, axis=1)
            if layer_num != 0:
                self.layers_dirty = True
    
    def flip_y_layer( self, layer_num=None ):
        """Flip a specific layer or current VL layer vertically"""
        if layer_num is None:
            layer_num = self.VL
        
        target_buffer = self.get_layer_buffer_by_num(layer_num)
        if target_buffer is not None:
            target_buffer[:] = np.flip(target_buffer, axis=0)
            if layer_num != 0:
                self.layers_dirty = True
    
    # let's make a color palette for the 256 color screen
    # 0x00-0x0F: Grayscale ramp (16 colors)
    # 0x10-0x1F: Red ramp (16 colors)
    # 0x20-0x2F: Green ramp (16 colors)
    # 0x30-0x3F: Blue ramp (16 colors)
    # 0x40-0x4F: Yellow ramp (16 colors)
    # 0x50-0x5F: Magenta ramp (16 colors)
    # 0x60-0x6F: Cyan ramp (16 colors)
    # 0x70-0x7F: Orange ramp (16 colors)
    # 0x80-0x8F: Purple ramp (16 colors)
    # 0x90-0x9F: Lime ramp (16 colors)
    # 0xA0-0xAF: Pink ramp (16 colors)
    # 0xB0-0xBF: Teal ramp (16 colors)
    # 0xC0-0xCF: Brown ramp (16 colors)
    # 0xD0-0xDF: Light blue ramp (16 colors)
    # 0xE0-0xEF: Light green ramp (16 colors)
    # 0xF0-0xFF: Light red ramp (16 colors)
    
    def set_color_palette( self, palette=None ):
        # If a palette is provided, use it directly
        if palette is not None:
            self.palette = palette
            return

        # Otherwise, generate the palette as a list of 256 RGB tuples, each expressable as a sinVLe byte index
        self.palette = []
        for i in range( 256 ):
            if 0x00 <= i <= 0x0F:
                # Grayscale ramp
                val = int( i * 255 / 15 )
                color = ( val, val, val )
            elif 0x10 <= i <= 0x1F:
                # Red ramp
                val = int( ( i - 0x10 ) * 255 / 15 )
                color = ( val, 0, 0 )
            elif 0x20 <= i <= 0x2F:
                # Green ramp
                val = int( ( i - 0x20 ) * 255 / 15 )
                color = ( 0, val, 0 )
            elif 0x30 <= i <= 0x3F:
                # Blue ramp
                val = int( ( i - 0x30 ) * 255 / 15 )
                color = ( 0, 0, val )
            elif 0x40 <= i <= 0x4F:
                # Yellow ramp
                val = int( ( i - 0x40 ) * 255 / 15 )
                color = ( val, val, 0 )
            elif 0x50 <= i <= 0x5F:
                # Magenta ramp
                val = int( ( i - 0x50 ) * 255 / 15 )
                color = ( val, 0, val )
            elif 0x60 <= i <= 0x6F:
                # Cyan ramp
                val = int( ( i - 0x60 ) * 255 / 15 )
                color = ( 0, val, val )
            elif 0x70 <= i <= 0x7F:
                # Orange ramp
                val = int( ( i - 0x70 ) * 255 / 15 )
                color = ( val, int( val * 0.5 ), 0 )
            elif 0x80 <= i <= 0x8F:
                # Purple ramp
                val = int( ( i - 0x80 ) * 255 / 15 )
                color = ( int( val * 0.5 ), 0, val )
            elif 0x90 <= i <= 0x9F:
                # Lime ramp
                val = int( ( i - 0x90 ) * 255 / 15 )
                color = ( int( val * 0.5 ), val, 0 )
            elif 0xA0 <= i <= 0xAF:
                # Pink ramp
                val = int( ( i - 0xA0 ) * 255 / 15 )
                color = ( val, int( val * 0.5 ), int( val * 0.5 ) )
            elif 0xB0 <= i <= 0xBF:
                # Teal ramp
                val = int( ( i - 0xB0 ) * 255 / 15 )
                color = ( 0, int( val * 0.5 ), int( val * 0.5 ) )
            elif 0xC0 <= i <= 0xCF:
                # Brown ramp
                val = int( ( i - 0xC0 ) * 255 / 15 )
                color = ( int( val * 0.6 ), int( val * 0.3 ), 0 )
            elif 0xD0 <= i <= 0xDF:
                # Light blue ramp
                val = int( ( i - 0xD0 ) * 255 / 15 )
                color = ( int( val * 0.5 ), int( val * 0.5 ), val )
            elif 0xE0 <= i <= 0xEF:
                # Light green ramp
                val = int( ( i - 0xE0 ) * 255 / 15 )
                color = ( int( val * 0.5 ), val, int( val * 0.5 ) )
            elif 0xF0 <= i <= 0xFF:
                # Light red ramp
                val = int( ( i - 0xF0 ) * 255 / 15 )
                color = ( val, int( val * 0.5 ), int( val * 0.5 ) )
            else:
                color = ( 0, 0, 0 )
            self.palette.append( color )

    def get_color( self, index ):
        return self.palette[ index ]
    
    def set_color( self, index, color ):
        self.palette[ index ] = color

    def get_palette( self ):
        return self.palette
    
    # Text rendering methods
    def draw_char(self, char, x, y, color=0xFF, background=None):
        """Draw a sinVLe character at the specified position (8x8 characters)"""
        # Convert character to ASCII code
        if isinstance(char, str):
            ascii_code = ord(char)
        else:
            ascii_code = char
        
        # Map ASCII to font data index (space = 0x20 = 32, maps to index 0)
        if ascii_code < 32 or ascii_code > 127:
            ascii_code = 32  # Default to space for invalid characters
        
        # Adjust for the apparent 2-character shift in font data
        font_index = ascii_code - 32 + 2
        
        # Get the 8 bytes for this character
        char_data = font_data[font_index * 8:(font_index + 1) * 8]
        
        # Get the target buffer based on current layer
        target_buffer = self._get_layer_buffer()
        
        # Draw the character pixel by pixel to the appropriate layer (8x8 characters)
        for row in range(8):  # Use all 8 rows
            byte_data = char_data[row]
            for col in range(8):  # Use all 8 columns for 8x8 characters
                pixel_x = x + col
                pixel_y = y + row
                
                # Bounds check
                if 0 <= pixel_x < self.width and 0 <= pixel_y < self.height:
                    # Check if pixel should be set (bit 7 is leftmost pixel)
                    if byte_data & (0x80 >> col):
                        # Foreground pixel
                        target_buffer[pixel_y, pixel_x] = color
                    elif background is not None:
                        # Background pixel
                        target_buffer[pixel_y, pixel_x] = background
    
    def draw_string(self, text, x, y, color=0xFF, background=None, char_spacing=8):
        """Draw a string at the specified position (8x8 characters)"""
        current_x = x
        
        for char in text:
            if char == '\n':
                # Handle newline
                current_x = x
                y += 8  # Move down by character height (8 pixels)
            elif char == '\t':
                # Handle tab (4 characters)
                current_x += char_spacing * 4
            else:
                # Draw the character
                self.draw_char(char, current_x, y, color, background)
                current_x += char_spacing
                
                # Wrap to next line if we exceed screen width
                if current_x + char_spacing > self.width:
                    current_x = x
                    y += 8  # Move down by character height (8 pixels)

    def draw_string_to_screen(self, text, x, y, color=0xFF, background=None, char_spacing=8):
        """Draw a string to screen instead of VRAM (8x8 characters)"""
        # Ensure coordinates are valid integers and not overflowed
        x = int(x) & 0xFFFF  # Mask to 16-bit to prevent overflow
        y = int(y) & 0xFFFF  # Mask to 16-bit to prevent overflow
        
        # Handle overflow values that appear valid but are actually negative
        if x > 32767:  # Treat as negative due to overflow
            x = x - 65536
        if y > 32767:  # Treat as negative due to overflow  
            y = y - 65536
            
        current_x = x
        
        for char in text:
            if char == '\n':
                current_x = x
                y += 8  # Move down by character height (8 pixels)
            elif char == '\t':
                current_x += char_spacing * 4
            else:
                # Draw character to screen
                self.draw_char_to_screen(char, current_x, y, color, background)
                current_x += char_spacing
                
                if current_x + char_spacing > self.width:
                    current_x = x
                    y += 8  # Move down by character height (8 pixels)

    def draw_char_to_screen(self, char, x, y, color=0xFF, background=None):
        """Draw a sinVLe character to screen - optimized version (5x8 characters)"""
        # Convert character to ASCII code
        if isinstance(char, str):
            ascii_code = ord(char)
        else:
            ascii_code = char
        
        # Map ASCII to font data index
        if ascii_code < 32 or ascii_code > 127:
            ascii_code = 32  # Default to space
        
        # Ensure coordinates are valid integers and not overflowed
        x = int(x) & 0xFFFF  # Mask to 16-bit to prevent overflow
        y = int(y) & 0xFFFF  # Mask to 16-bit to prevent overflow
        
        # Additional bounds check for overflow values that appear valid but are actually negative
        if x > 32767:  # Treat as negative due to overflow
            x = x - 65536
        if y > 32767:  # Treat as negative due to overflow  
            y = y - 65536
        
        # Bounds check for entire character (5x8 instead of 8x8)
        if x + 8 > self.width or y + 8 > self.height or x < 0 or y < 0:
            return  # Skip if character would be off-screen
        
        # Adjust for the apparent 2-character shift in font data
        font_index = ascii_code - 32
        char_data = font_data[font_index * 8:(font_index + 1) * 8]
        
        # Vectorized bitmap generation - much faster than nested loops (all 8 columns)
        char_bytes = np.array(char_data, dtype=np.uint8)  # Use all 8 rows
        
        # Create bit mask matrix using numpy broadcasting (all 8 bits)
        bit_positions = np.array([0x80, 0x40, 0x20, 0x10, 0x08, 0x04, 0x02, 0x01], dtype=np.uint8)  # All 8 bits
        char_matrix = (char_bytes[:, np.newaxis] & bit_positions) != 0
        
        # Apply colors vectorized
        char_bitmap = np.where(char_matrix, color, 0 if background is None else background)
        
        # Get the target buffer based on current layer
        target_buffer = self._get_layer_buffer()
        
        # Copy character to the appropriate buffer (only non-transparent pixels if background is None)
        if background is None:
            # Only draw foreground pixels, leave background transparent
            mask = char_matrix
            target_buffer[y:y+8, x:x+8][mask] = color  # 8 rows, 5 columns
        else:
            # Draw entire character bitmap
            target_buffer[y:y+8, x:x+8] = char_bitmap  # 8 rows, 5 columns
        
        # Blit the entire character at once
        if background is not None:
            # Full character replacement
            target_buffer[y:y+8, x:x+8] = char_bitmap  # 8 rows, 5 columns
        else:
            # Only draw foreground pixels
            mask = char_bitmap != 0
            target_buffer[y:y+8, x:x+8][mask] = char_bitmap[mask]  # 8 rows, 5 columns
    
    def _get_layer_buffer(self):
        """Get the numpy array for the current layer specified by VL register"""
        if self.VL == 0:
            return self.screen
        elif 1 <= self.VL <= 4:
            return self.background_layers[self.VL - 1]
        elif 5 <= self.VL <= 8:
            return self.sprite_layers[self.VL - 5]
        else:
            return self.screen  # Fallback to screen for invalid layers    
    
    # ========================================
    # SPRITE SYSTEM IMPLEMENTATION
    # ========================================
    
    def get_sprite_control_block(self, sprite_id, memory):
        """Get sprite control block data from memory"""
        if sprite_id < 0 or sprite_id >= self.sprite_count:
            return None
            
        # Ensure we're working with regular Python integers to avoid numpy overflow
        base_addr = int(self.sprite_memory_base) + (int(sprite_id) * int(self.sprite_block_size))
        
        # Read sprite control block (16 bytes)
        control_block = memory.read_bytes_direct(base_addr, 16)
        
        return {
            'data_addr': (control_block[0] << 8) | control_block[1],  # Big-endian 16-bit
            'x': control_block[2],
            'y': control_block[3], 
            'width': control_block[4],
            'height': control_block[5],
            'flags': control_block[6],
            'transparency_color': control_block[7],
            'active': (control_block[6] & 0x01) != 0,
            'transparency_enabled': (control_block[6] & 0x02) != 0,
            'layer': 5 if (control_block[6] & 0x80) == 0 else 6  # Bit 7 selects sprite layer
        }
    
    def blit_sprite(self, sprite_id, memory):
        """Blit a sinVLe sprite to its designated layer"""
        sprite = self.get_sprite_control_block(sprite_id, memory)
        if not sprite or not sprite['active'] or sprite['width'] == 0 or sprite['height'] == 0:
            return
            
        # Get sprite data from memory
        sprite_size = sprite['width'] * sprite['height']
        if sprite['data_addr'] + sprite_size > memory.size:
            return  # Invalid sprite data address
            
        sprite_data = memory.read_bytes_direct(sprite['data_addr'], sprite_size)
        
        # Convert to 2D array
        sprite_bitmap = np.array(sprite_data, dtype=np.uint8).reshape(sprite['height'], sprite['width'])
        
        # Get target layer buffer
        target_layer = sprite['layer']
        if target_layer == 5:
            target_buffer = self.sprite_layers[0]
        elif target_layer == 6:
            target_buffer = self.sprite_layers[1]
        else:
            target_buffer = self.sprite_layers[0]  # Default to sprite layer 5
            
        # Calculate blit bounds
        x, y = sprite['x'], sprite['y']
        width, height = sprite['width'], sprite['height']
        
        # Clip to screen bounds
        if x >= self.width or y >= self.height or x + width <= 0 or y + height <= 0:
            return  # Sprite is completely off-screen
            
        # Calculate clipped region
        src_x_start = max(0, -x)
        src_y_start = max(0, -y)
        src_x_end = min(width, self.width - x)
        src_y_end = min(height, self.height - y)
        
        dst_x_start = max(0, x)
        dst_y_start = max(0, y)
        dst_x_end = dst_x_start + (src_x_end - src_x_start)
        dst_y_end = dst_y_start + (src_y_end - src_y_start)
        
        # Extract the visible portion of the sprite
        visible_sprite = sprite_bitmap[src_y_start:src_y_end, src_x_start:src_x_end]
        
        if sprite['transparency_enabled']:
            # Apply transparency
            transparent_color = sprite['transparency_color']
            mask = visible_sprite != transparent_color
            target_buffer[dst_y_start:dst_y_end, dst_x_start:dst_x_end][mask] = visible_sprite[mask]
        else:
            # No transparency, direct copy
            target_buffer[dst_y_start:dst_y_end, dst_x_start:dst_x_end] = visible_sprite
    
    def blit_all_sprites(self, memory):
        """Blit all active sprites to their designated layers"""
        # Clear sprite layers first
        for layer in self.sprite_layers:
            layer.fill(0)
            
        # Blit all sprites in order (0-15)
        for sprite_id in range(self.sprite_count):
            self.blit_sprite(sprite_id, memory)
            
        self.sprites_dirty = False  # Mark sprites as clean
        self.layers_dirty = True   # Mark layers as needing compositing