import threading
import warnings
warnings.filterwarnings("ignore", message="pkg_resources is deprecated", category=UserWarning)
import pygame
from collections import deque
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import time

# Keep these imports for type hinting and the __main__ block
import nova_gfx as gpu
import nova_cpu as cpu
from nova.memory import Memory as mem
import nova_uart as uart


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
        self.target_fps = 60
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
                    if self.cpu.halted:
                        self.running = False
                        self.paused.set()
                        break
                
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
            if hasattr(self.cpu.keyboard_device, 'clear_buffer'):
                self.cpu.keyboard_device.clear_buffer()
        
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


def open_uart_config_dialog(current_config):
    selected_config = {'value': None}
    dialog = tk.Tk()
    dialog.title('UART Configuration')
    dialog.resizable(False, False)

    mode_var = tk.StringVar(value=current_config.mode)
    tcp_role_var = tk.StringVar(value=current_config.tcp_role)
    host_var = tk.StringVar(value=current_config.host)
    port_var = tk.StringVar(value='' if current_config.port is None else str(current_config.port))
    timeout_var = tk.StringVar(value=str(current_config.timeout))

    frame = ttk.Frame(dialog, padding=12)
    frame.grid(row=0, column=0, sticky='nsew')

    ttk.Label(frame, text='Bridge').grid(row=0, column=0, sticky='w')
    mode_frame = ttk.Frame(frame)
    mode_frame.grid(row=0, column=1, columnspan=2, sticky='w')
    ttk.Radiobutton(mode_frame, text='Off', value='none', variable=mode_var).grid(row=0, column=0, padx=(0, 8))
    ttk.Radiobutton(mode_frame, text='Terminal', value='terminal', variable=mode_var).grid(row=0, column=1, padx=(0, 8))
    ttk.Radiobutton(mode_frame, text='TCP', value='tcp', variable=mode_var).grid(row=0, column=2)

    ttk.Label(frame, text='TCP Role').grid(row=1, column=0, sticky='w', pady=(10, 0))
    tcp_role_box = ttk.Combobox(frame, textvariable=tcp_role_var, values=('client', 'server'), state='readonly', width=10)
    tcp_role_box.grid(row=1, column=1, sticky='w', pady=(10, 0))

    ttk.Label(frame, text='Host').grid(row=2, column=0, sticky='w', pady=(8, 0))
    host_entry = ttk.Entry(frame, textvariable=host_var, width=24)
    host_entry.grid(row=2, column=1, columnspan=2, sticky='ew', pady=(8, 0))

    ttk.Label(frame, text='Port').grid(row=3, column=0, sticky='w', pady=(8, 0))
    port_entry = ttk.Entry(frame, textvariable=port_var, width=12)
    port_entry.grid(row=3, column=1, sticky='w', pady=(8, 0))

    ttk.Label(frame, text='Timeout (s)').grid(row=4, column=0, sticky='w', pady=(8, 0))
    timeout_entry = ttk.Entry(frame, textvariable=timeout_var, width=12)
    timeout_entry.grid(row=4, column=1, sticky='w', pady=(8, 0))

    button_frame = ttk.Frame(frame)
    button_frame.grid(row=5, column=0, columnspan=3, sticky='e', pady=(12, 0))

    def sync_tcp_fields(*_args):
        state = 'normal' if mode_var.get() == 'tcp' else 'disabled'
        for entry in (tcp_role_box, host_entry, port_entry, timeout_entry):
            entry.configure(state=state)

    def cancel():
        dialog.destroy()

    def submit():
        try:
            port_value = port_var.get().strip()
            config = uart.validate_bridge_config(
                uart.UARTBridgeConfig(
                    mode=mode_var.get(),
                    tcp_role=tcp_role_var.get(),
                    host=host_var.get(),
                    port=int(port_value) if port_value else None,
                    timeout=float(timeout_var.get().strip() or uart.DEFAULT_TCP_TIMEOUT),
                )
            )
        except ValueError as exc:
            messagebox.showerror('UART Configuration', str(exc), parent=dialog)
            return

        selected_config['value'] = config
        dialog.destroy()

    ttk.Button(button_frame, text='Cancel', command=cancel).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(button_frame, text='Apply', command=submit).grid(row=0, column=1)

    mode_var.trace_add('write', sync_tcp_fields)
    sync_tcp_fields()
    dialog.protocol('WM_DELETE_WINDOW', cancel)
    dialog.mainloop()
    return selected_config['value']

def main( cpu, memory, gfx, kbd=None ):
    scale = 2
    toolbar_height = 46
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
    mouse_device = getattr(cpu, 'mouse', None)
    
    # Force initial screen update to show any existing graphics
    cpu_controller.force_screen_update()
    
    # Performance optimizations
    target_fps = 32
    update_queue = cpu_controller.update_queue 


    font = pygame.font.SysFont( None, 22 )
    small_font = pygame.font.SysFont( None, 17 )
    button_h = 30
    button_y = 8
    button_gap = 6
    button_specs = [
        ( 'Start/Pause', 74 ),
        ( 'Stop', 56 ),
        ( 'Reset', 58 ),
        ( 'Step', 52 ),
        ( 'Load', 54 ),
        ( 'UART', 60 ),
    ]
    buttons = {}
    next_x = 8
    for name, width in button_specs:
        buttons[ name ] = pygame.Rect( next_x, button_y, width, button_h )
        next_x += width + button_gap
    button_colors = {
        'Start/Pause': ( 0, 200, 0 ), 'Stop': ( 200, 0, 0 ), 'Reset': ( 0, 0, 200 ),
        'Step': ( 200, 200, 0 ), 'Load': ( 0, 200, 200 ), 'UART': ( 170, 110, 20 )
    }

    # Cache for status text to avoid re-rendering every frame
    cached_status_text = ""
    cached_status_label = None
    prev_pc = None
    prev_running = None
    prev_halted = None
    current_uart_config = uart.get_bridge_config( cpu.uart.host_bridge )
    prev_uart_status = None

    # Cache for scaled surface
    cached_scaled_surface = None

    # Cache for button labels
    button_label_cache = {}

    # Physical key repeat settings for Nova-16 input (independent of pygame global repeat)
    key_repeat_initial_delay = 0.28
    key_repeat_interval = 0.05
    held_nova_keys = {}

    def map_event_to_nova_key(event):
        """Map a pygame key event to a Nova-16 key name."""
        key_name = None
        if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            key_name = 'shift'
        elif event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
            key_name = 'ctrl'
        elif event.key in (pygame.K_LALT, pygame.K_RALT):
            key_name = 'alt'
        elif event.key == pygame.K_RETURN:
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
        elif getattr(event, 'unicode', None) and len(event.unicode) == 1:
            key_name = event.unicode
        return key_name

    def load_binary_program():
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            filetypes=[ ( 'Binary files', '*.bin' ) ],
            initialdir='asm'
        )
        root.destroy()
        if file_path:
            cpu_controller.stop()
            cpu_controller.reset()
            held_nova_keys.clear()
            entry_point = memory.load( file_path )
            cpu_controller.cpu.pc = entry_point
            cpu_controller.start()
            print(f"Loaded {file_path}")
            print(f"Entry point: 0x{entry_point:04X}")

    def configure_uart_bridge():
        nonlocal current_uart_config
        requested_config = open_uart_config_dialog( current_uart_config )
        if requested_config is None:
            return

        was_running = cpu_controller.running
        cpu_controller.stop()
        try:
            new_bridge = uart.create_host_bridge( requested_config )
            cpu.uart.set_host_bridge( new_bridge )
            current_uart_config = requested_config
            print( uart.describe_bridge( current_uart_config ) )
        except ( OSError, ValueError ) as exc:
            messagebox.showerror( 'UART Configuration', f'Unable to configure UART bridge:\n{exc}' )
        finally:
            if was_running:
                cpu_controller.start()

    def map_window_to_emulator(pos):
        x, y = pos
        if x < 0 or x >= screen_width:
            return None
        if y < toolbar_height or y >= toolbar_height + screen_height:
            return None
        return x // scale, (y - toolbar_height) // scale

    def update_mouse_position(pos):
        if mouse_device is None:
            return False
        mapped = map_window_to_emulator(pos)
        if mapped is None:
            return False
        mouse_device.move_to(mapped[0], mapped[1], from_host=True)
        cpu_controller.force_screen_update()
        return True

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
                    held_nova_keys.clear()
                elif event.key == pygame.K_F8:  # F8 = Step
                    cpu_controller.step()
                elif event.key == pygame.K_F9:  # F9 = Load
                    load_binary_program()
                elif kbd is not None:
                    # Handle keyboard input for Nova-16
                    key_name = map_event_to_nova_key(event)
                    
                    if key_name:
                        kbd.press_key(key_name, apply_debounce=True)
                        if event.key not in held_nova_keys:
                            now = time.monotonic()
                            held_nova_keys[event.key] = {
                                'key_name': key_name,
                                'down_time': now,
                                'last_repeat': now
                            }

            elif event.type == pygame.KEYUP and kbd is not None:
                held_nova_keys.pop(event.key, None)
                # Keep modifier state synchronized with key releases.
                if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    kbd.release_key('shift')
                elif event.key in (pygame.K_LCTRL, pygame.K_RCTRL):
                    kbd.release_key('ctrl')
                elif event.key in (pygame.K_LALT, pygame.K_RALT):
                    kbd.release_key('alt')
            elif event.type == pygame.MOUSEMOTION:
                update_mouse_position(event.pos)
                    
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos
                handled_toolbar_click = False
                if event.button == 1:
                    for name, rect in buttons.items():
                        if rect.collidepoint( pos ):
                            handled_toolbar_click = True
                            if name == 'Start/Pause':
                                if cpu_controller.running:
                                    cpu_controller.stop()
                                else:
                                    cpu_controller.start()
                            elif name == 'Stop':
                                cpu_controller.stop()
                            elif name == 'Reset':
                                cpu_controller.reset()
                                held_nova_keys.clear()
                            elif name == 'Step':
                                cpu_controller.step()
                            elif name == 'Load':
                                load_binary_program()
                            elif name == 'UART':
                                configure_uart_bridge()
                            break

                if not handled_toolbar_click and event.button in (1, 3) and mouse_device is not None:
                    if update_mouse_position(pos):
                        mouse_device.set_button(event.button, True, from_host=True)
                        cpu_controller.force_screen_update()
            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 3) and mouse_device is not None:
                update_mouse_position(event.pos)
                mouse_device.set_button(event.button, False, from_host=True)
                cpu_controller.force_screen_update()

        # Synthesize key repeat while physical keys remain held.
        if kbd is not None and held_nova_keys:
            now = time.monotonic()
            for state in held_nova_keys.values():
                if state['key_name'] in ('shift', 'ctrl', 'alt', 'caps_lock'):
                    continue
                if (now - state['down_time']) >= key_repeat_initial_delay and (now - state['last_repeat']) >= key_repeat_interval:
                    kbd.press_key(state['key_name'], apply_debounce=False)
                    state['last_repeat'] = now

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
        current_uart_status = uart.describe_bridge( current_uart_config )
        
        # Only update status text if something changed
        if (current_pc != prev_pc or current_running != prev_running or current_halted != prev_halted or current_uart_status != prev_uart_status):
            status_text = f"PC: 0x{current_pc:04X} | "
            if current_halted:
                status_text += "HALTED"
            elif current_running:
                status_text += "RUNNING"
            else:
                status_text += "STOPPED"
            
            status_text += f" | {current_uart_status} | Hotkeys: F5=Start/Pause F6=Stop F7=Reset F8=Step F9=Load"
            
            if status_text != cached_status_text:
                cached_status_text = status_text
                cached_status_label = small_font.render( status_text, True, ( 200, 200, 200 ) )
            
            prev_pc = current_pc
            prev_running = current_running
            prev_halted = current_halted
            prev_uart_status = current_uart_status
        
        if cached_status_label:
            screen.blit( cached_status_label, ( 5, status_y + 5 ) )

        # Always scale and blit to ensure display updates
        if screen_updated or cached_scaled_surface is None:
            cached_scaled_surface = pygame.transform.scale( surface, ( screen_width, screen_height ) )
        screen.blit( cached_scaled_surface, ( 0, toolbar_height ) )
        pygame.display.flip()
        
        clock.tick( target_fps )

    cpu_controller.shutdown()
    cpu.uart.close_host_bridge()
    pygame.quit()

if __name__ == '__main__':
    proc = cpu.CPU( mem.Memory(), gpu.GFX() )
    main( proc, proc.memory, proc.gfx )