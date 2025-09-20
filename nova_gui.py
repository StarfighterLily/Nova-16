import threading
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
import pygame
from collections import deque
import tkinter as tk
from tkinter import filedialog
import time

# Keep these imports for type hinting and the __main__ block
import nova_gfx as gpu
import nova_cpu as cpu
import nova_memory as mem


class CPUController:
    def __init__( self, cpu, gfx, mem ):
        self.cpu = cpu
        self.gfx = gfx
        self.mem = mem
        self.update_queue = deque( maxlen=1 )
        self.running = False
        self.paused = threading.Event()
        self.stepping = threading.Event()
        self.stop_event = threading.Event()
        
        # Frame-rate limiting optimization
        self.target_fps = 120
        self.frame_time = 1.0 / self.target_fps
        self.last_screen_update = 0
        self.force_update = False
        
        self.thread = threading.Thread( target=self.run_cpu, daemon=True )
        self.thread.start()

    def run_cpu( self ):
        while not self.stop_event.is_set():
            current_time = time.time()
            
            if self.running:
                # Execute multiple CPU steps between screen updates
                steps_per_frame = max(1, int(self.cpu.clock_speed / self.target_fps) if hasattr(self.cpu, 'clock_speed') else 1000)
                
                for _ in range(steps_per_frame):
                    if not self.running or self.stop_event.is_set():
                        break
                    self.cpu.step()
                
                # Only update screen if enough time has passed or forced
                if (current_time - self.last_screen_update >= self.frame_time) or self.force_update:
                    self.update_queue.appendleft( self.gfx.get_screen().copy() )
                    self.last_screen_update = current_time
                    self.force_update = False
                    
            elif self.stepping.is_set():
                self.cpu.step()
                # Always update screen for single steps
                self.update_queue.appendleft( self.gfx.get_screen().copy() )
                self.stepping.clear()
            else:
                # Small sleep to prevent busy waiting
                time.sleep(0.001)

    def start( self ):
        self.running = True
        self.paused.clear()

    def stop( self ):
        self.running = False
        self.paused.set()

    def reset( self ):
        """Perform a complete system reset - CPU, memory, graphics, and peripherals"""
        self.running = False
        
        # Reset CPU state (registers, flags, PC, stack, etc.)
        self.cpu.reinit()
        
        # Clear all graphics layers and screen
        self.gfx.clear()
        if hasattr(self.gfx, 'clear_layer'):
            # Clear all graphics layers if layer system is available
            for i in range(8):  # Assuming up to 8 layers
                try:
                    self.gfx.clear_layer(i)
                except:
                    pass
        
        # Reset any graphics state variables
        if hasattr(self.gfx, 'vmode'):
            self.gfx.vmode = 0
        if hasattr(self.gfx, 'flags'):
            self.gfx.flags[:] = 0
        if hasattr(self.gfx, 'Vregisters'):
            self.gfx.Vregisters[:] = 0
            
        # Clear memory completely
        self.mem.memory[:] = 0
        
        # Reset any keyboard state if available
        if hasattr(self.cpu, 'keyboard_device') and self.cpu.keyboard_device:
            if hasattr(self.cpu.keyboard_device, 'key_buffer'):
                self.cpu.keyboard_device.key_buffer.clear()
        
        # Force immediate screen update after reset
        self.force_update = True
        self.update_queue.appendleft( self.gfx.get_screen().copy() )
        self.paused.clear()
        
        print("System reset completed - all components reinitialized")

    def force_screen_update(self):
        """Force an immediate screen update (useful for static graphics)"""
        self.force_update = True
        screen_data = self.gfx.get_screen().copy()
        self.update_queue.appendleft( screen_data )

    def set_target_fps(self, fps):
        """Adjust the target frame rate for screen updates"""
        self.target_fps = max(1, min(fps, 120))  # Clamp between 1-120 FPS
        self.frame_time = 1.0 / self.target_fps

    def step( self ):
        self.stepping.set()

    def shutdown( self ):
        self.stop_event.set()
        self.thread.join()

def draw_button_cached( surface, rect, text, font, color, text_color, active, cache ):
    pygame.draw.rect( surface, color if active else ( 100, 100, 100 ), rect, border_radius=6 )
    cache_key = (text, color, text_color, active)
    if cache_key not in cache:
        cache[cache_key] = font.render( text, True, text_color )
    label = cache[cache_key]
    label_rect = label.get_rect( center=rect.center )
    surface.blit( label, label_rect )

def main( cpu, memory, gfx, kbd=None ):
    scale = 2
    toolbar_height = 50
    status_height = 25  # Add status bar at bottom
    screen_width = gfx.width * scale
    screen_height = gfx.height * scale
    window_height = screen_height + toolbar_height + status_height

    gfx.set_color_palette()
    pygame.init()
    screen = pygame.display.set_mode( ( screen_width, window_height ) )
    pygame.display.set_caption( "Nova-16" )
    surface = pygame.Surface( ( gfx.width, gfx.height ), depth=8 )
    surface.set_palette( [ tuple( color ) for color in gfx.get_palette() ] )
    clock = pygame.time.Clock()
    cpu_controller = CPUController( cpu, gfx, memory )
    
    # Force initial screen update to show any existing graphics
    cpu_controller.force_screen_update()
    
    # Performance optimizations
    target_fps = 32
    update_queue = cpu_controller.update_queue 


    font = pygame.font.SysFont( None, 24 )
    small_font = pygame.font.SysFont( None, 18 )
    button_w, button_h = 75, 32
    margin = 10
    buttons = {
        'Start/Pause': pygame.Rect( margin, margin, button_w + 20, button_h ),
        'Stop': pygame.Rect( margin + button_w + 20 + margin, margin, button_w, button_h ),
        'Reset': pygame.Rect( margin + 2 * ( button_w + margin ) + 20, margin, button_w, button_h ),
        'Step': pygame.Rect( margin + 3 * ( button_w + margin ) + 20, margin, button_w, button_h ),
        'Load': pygame.Rect( margin + 4 * ( button_w + margin ) + 20, margin, button_w, button_h )
    }
    button_colors = {
        'Start/Pause': ( 0, 200, 0 ), 'Stop': ( 200, 0, 0 ), 'Reset': ( 0, 0, 200 ),
        'Step': ( 200, 200, 0 ), 'Load': ( 0, 200, 200 )
    }

    # Cache for status text to avoid re-rendering every frame
    cached_status_text = ""
    cached_status_label = None
    prev_pc = cpu.pc
    prev_running = cpu_controller.running
    prev_halted = cpu.halted

    # Cache for scaled surface
    cached_scaled_surface = None

    # Cache for button labels
    button_label_cache = {}

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Handle GUI shortcut keys first
                if event.key == pygame.K_F5:  # F5 = Start/Pause toggle
                    if cpu_controller.running:
                        cpu_controller.stop()
                    else:
                        cpu_controller.start()
                elif event.key == pygame.K_F6:  # F6 = Stop
                    cpu_controller.stop()
                elif event.key == pygame.K_F7:  # F7 = Reset
                    cpu_controller.reset()
                elif event.key == pygame.K_F8:  # F8 = Step
                    cpu_controller.step()
                elif event.key == pygame.K_F9:  # F9 = Load
                    root = tk.Tk()
                    root.withdraw()
                    file_path = filedialog.askopenfilename( 
                        filetypes=[ ( "Binary files", "*.bin" ) ],
                        initialdir="asm"
                    )
                    root.destroy()
                    if file_path:
                        cpu_controller.stop()
                        cpu_controller.reset()
                        entry_point = memory.load( file_path )
                        cpu_controller.cpu.pc = entry_point
                        cpu_controller.start()  # Auto-start after loading
                        print(f"Loaded {file_path}")
                        print(f"Entry point: 0x{entry_point:04X}")
                elif kbd is not None:
                    # Handle keyboard input for Nova-16
                    key_name = None
                    if event.key == pygame.K_RETURN:
                        key_name = 'enter'
                    elif event.key == pygame.K_BACKSPACE:
                        key_name = 'backspace'
                    elif event.key == pygame.K_TAB:
                        key_name = 'tab'
                    elif event.key == pygame.K_ESCAPE:
                        key_name = 'escape'
                    elif event.key == pygame.K_LEFT:
                        key_name = 'left'
                    elif event.key == pygame.K_RIGHT:
                        key_name = 'right'
                    elif event.key == pygame.K_UP:
                        key_name = 'up'
                    elif event.key == pygame.K_DOWN:
                        key_name = 'down'
                    elif event.key == pygame.K_F1:
                        key_name = 'f1'
                    elif event.key == pygame.K_F2:
                        key_name = 'f2'
                    elif event.key == pygame.K_F3:
                        key_name = 'f3'
                    elif event.key == pygame.K_F4:
                        key_name = 'f4'
                    elif event.key == pygame.K_F10:
                        key_name = 'f10'
                    elif event.key == pygame.K_F11:
                        key_name = 'f11'
                    elif event.key == pygame.K_F12:
                        key_name = 'f12'
                    elif event.key == pygame.K_INSERT:
                        key_name = 'insert'
                    elif event.key == pygame.K_DELETE:
                        key_name = 'delete'
                    elif event.key == pygame.K_HOME:
                        key_name = 'home'
                    elif event.key == pygame.K_END:
                        key_name = 'end'
                    elif event.key == pygame.K_PAGEUP:
                        key_name = 'page_up'
                    elif event.key == pygame.K_PAGEDOWN:
                        key_name = 'page_down'
                    elif event.unicode and len(event.unicode) == 1:
                        # Handle printable characters
                        key_name = event.unicode
                    
                    if key_name:
                        kbd.press_key(key_name)
                    
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos
                for name, rect in buttons.items():
                    if rect.collidepoint( pos ):
                        if name == 'Start/Pause':
                            # Toggle between start and pause
                            if cpu_controller.running:
                                cpu_controller.stop()
                            else:
                                cpu_controller.start()
                        elif name == 'Stop':
                            cpu_controller.stop()
                        elif name == 'Reset':
                            cpu_controller.reset()
                        elif name == 'Step':
                            cpu_controller.step()
                        elif name == 'Load':
                            root = tk.Tk()
                            root.withdraw()
                            file_path = filedialog.askopenfilename( 
                                filetypes=[ ( "Binary files", "*.bin" ) ],
                                initialdir="asm"
                            )
                            root.destroy()
                            if file_path:
                                cpu_controller.stop()
                                cpu_controller.reset()
                                entry_point = memory.load( file_path )
                                cpu_controller.cpu.pc = entry_point  # Set PC to entry point from ORG
                                cpu_controller.start()  # Auto-start after loading
                                print(f"Loaded {file_path}")
                                print(f"Entry point: 0x{entry_point:04X}")

        # Update screen only when needed
        screen_updated = False
        
        # Check for screen updates from CPU
        try:
            if update_queue:
                arr = update_queue.popleft()
                pygame.surfarray.blit_array( surface, arr.T )
                screen_updated = True
        except Exception as e:
            # Silently handle any display errors
            pass

        # Always redraw UI elements to ensure they're visible
        screen.fill( ( 40, 40, 40 ), rect=pygame.Rect( 0, 0, screen_width, toolbar_height ) )
        for name, rect in buttons.items():
            if name == 'Start/Pause':
                # Show current state and toggle functionality
                button_text = 'Pause' if cpu_controller.running else 'Start'
                button_color = ( 200, 200, 0 ) if cpu_controller.running else ( 0, 200, 0 )
                active = True  # Always show as active since it's always clickable
            else:
                button_text = name
                button_color = button_colors[ name ]
                active = True
            draw_button_cached( screen, rect, button_text, font, button_color, ( 255, 255, 255 ), active, button_label_cache )

        # Draw status bar at bottom
        status_y = screen_height + toolbar_height
        screen.fill( ( 30, 30, 30 ), rect=pygame.Rect( 0, status_y, screen_width, status_height ) )
        
        # Display CPU status information
        current_pc = cpu.pc
        current_running = cpu_controller.running
        current_halted = cpu.halted
        
        # Only update status text if something changed
        if (current_pc != prev_pc or current_running != prev_running or current_halted != prev_halted):
            status_text = f"PC: 0x{current_pc:04X} | "
            if current_running:
                status_text += "RUNNING"
            elif current_halted:
                status_text += "HALTED"
            else:
                status_text += "STOPPED"
            
            status_text += " | Hotkeys: F5=Start/Pause F6=Stop F7=Reset F8=Step F9=Load"
            
            if status_text != cached_status_text:
                cached_status_text = status_text
                cached_status_label = small_font.render( status_text, True, ( 200, 200, 200 ) )
            
            prev_pc = current_pc
            prev_running = current_running
            prev_halted = current_halted
        
        if cached_status_label:
            screen.blit( cached_status_label, ( 5, status_y + 5 ) )

        # Always scale and blit to ensure display updates
        if screen_updated or cached_scaled_surface is None:
            cached_scaled_surface = pygame.transform.scale( surface, ( screen_width, screen_height ) )
        screen.blit( cached_scaled_surface, ( 0, toolbar_height ) )
        pygame.display.flip()
        
        clock.tick( target_fps )

    cpu_controller.shutdown()
    pygame.quit()

if __name__ == '__main__':
    proc = cpu.CPU( mem.Memory(), gpu.GFX() )
    main( proc, proc.memory, proc.gfx )