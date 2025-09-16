#!/usr/bin/env python3
"""
Enhanced Font Maker for Nova System
Creates fonts for the entire printable range with advanced editing capabilities
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os
from font import font_data
import copy

CELL_SIZE = 20
GRID_SIZE = 8

class EnhancedFontMaker:
    def __init__(self, master):
        self.master = master
        self.master.title("Nova Enhanced Font Maker")
        self.master.geometry("1200x800")
        
        # Font data storage - start with existing font_data
        self.font_data = {}
        self.load_existing_font_data()
        
        # Current character being edited
        self.current_char = 32  # Start with space
        
        # Character grid (8x8)
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.rects = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        
        # Setup UI
        self.setup_ui()
        self.load_character(self.current_char)
        
    def load_existing_font_data(self):
        """Load existing font data from font.py"""
        # Map existing font_data to character codes
        for i, char_code in enumerate(range(32, len(font_data) // 8 + 32)):
            if i * 8 + 8 <= len(font_data):
                char_bytes = font_data[i * 8:(i + 1) * 8]
                self.font_data[char_code] = list(char_bytes)
                
    def setup_ui(self):
        """Setup the user interface"""
        # Create main frames
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel for character editing
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right panel for controls and preview
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        
        self.setup_character_editor(left_frame)
        self.setup_controls(right_frame)
        
    def setup_character_editor(self, parent):
        """Setup the character editing canvas"""
        editor_frame = ttk.LabelFrame(parent, text="Character Editor")
        editor_frame.pack(fill=tk.BOTH, expand=True)
        
        # Character info
        info_frame = ttk.Frame(editor_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.char_info_label = ttk.Label(info_frame, text="", font=("Arial", 12, "bold"))
        self.char_info_label.pack()
        
        # Canvas for editing
        canvas_frame = ttk.Frame(editor_frame)
        canvas_frame.pack(expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, 
                               width=CELL_SIZE*GRID_SIZE + 2, 
                               height=CELL_SIZE*GRID_SIZE + 2,
                               bg='white', relief=tk.SUNKEN, bd=2)
        self.canvas.pack(padx=20, pady=20)
        
        self.draw_grid()
        self.canvas.bind("<Button-1>", self.toggle_cell)
        self.canvas.bind("<B1-Motion>", self.paint_cell)
        self.canvas.bind("<Button-3>", self.clear_cell)  # Right click to clear
        self.canvas.bind("<B3-Motion>", self.clear_cell_motion)
        
        # Editing tools
        tools_frame = ttk.Frame(editor_frame)
        tools_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(tools_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(tools_frame, text="Fill All", command=self.fill_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(tools_frame, text="Invert", command=self.invert_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(tools_frame, text="Shift Left", command=self.shift_left).pack(side=tk.LEFT, padx=2)
        ttk.Button(tools_frame, text="Shift Right", command=self.shift_right).pack(side=tk.LEFT, padx=2)
        ttk.Button(tools_frame, text="Shift Up", command=self.shift_up).pack(side=tk.LEFT, padx=2)
        ttk.Button(tools_frame, text="Shift Down", command=self.shift_down).pack(side=tk.LEFT, padx=2)
        
    def setup_controls(self, parent):
        """Setup control panels"""
        # Character selection
        char_frame = ttk.LabelFrame(parent, text="Character Selection")
        char_frame.pack(fill=tk.X, pady=5)
        
        # Character input
        input_frame = ttk.Frame(char_frame)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_frame, text="Character:").pack(side=tk.LEFT)
        self.char_entry = ttk.Entry(input_frame, width=5)
        self.char_entry.pack(side=tk.LEFT, padx=5)
        self.char_entry.bind('<Return>', self.on_char_entry)
        
        ttk.Label(input_frame, text="Code:").pack(side=tk.LEFT, padx=(10, 0))
        self.code_entry = ttk.Entry(input_frame, width=5)
        self.code_entry.pack(side=tk.LEFT, padx=5)
        self.code_entry.bind('<Return>', self.on_code_entry)
        
        # Navigation buttons
        nav_frame = ttk.Frame(char_frame)
        nav_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(nav_frame, text="Prev", command=self.prev_char).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="Next", command=self.next_char).pack(side=tk.LEFT, padx=2)
        
        # Character range buttons
        range_frame = ttk.Frame(char_frame)
        range_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(range_frame, text="Basic ASCII (32-126)", 
                  command=lambda: self.goto_char(32)).pack(fill=tk.X, pady=1)
        ttk.Button(range_frame, text="Extended (128-255)", 
                  command=lambda: self.goto_char(128)).pack(fill=tk.X, pady=1)
        ttk.Button(range_frame, text="Numbers (48-57)", 
                  command=lambda: self.goto_char(48)).pack(fill=tk.X, pady=1)
        ttk.Button(range_frame, text="Letters A-Z (65-90)", 
                  command=lambda: self.goto_char(65)).pack(fill=tk.X, pady=1)
        ttk.Button(range_frame, text="Letters a-z (97-122)", 
                  command=lambda: self.goto_char(97)).pack(fill=tk.X, pady=1)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(parent, text="Text Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Preview text input
        preview_input_frame = ttk.Frame(preview_frame)
        preview_input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(preview_input_frame, text="Preview Text:").pack(anchor=tk.W)
        self.preview_text = tk.Text(preview_input_frame, height=3, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.X, pady=2)
        self.preview_text.insert('1.0', "The quick brown fox jumps over the lazy dog!\n0123456789")
        self.preview_text.bind('<KeyRelease>', self.update_preview)
        
        # Preview canvas
        self.preview_canvas = tk.Canvas(preview_frame, height=200, bg='black')
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Export/Import controls
        file_frame = ttk.LabelFrame(parent, text="File Operations")
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(file_frame, text="Export Font Data", 
                  command=self.export_font_data).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(file_frame, text="Export Python Code", 
                  command=self.export_python_code).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(file_frame, text="Import Font Data", 
                  command=self.import_font_data).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(file_frame, text="Save Project", 
                  command=self.save_project).pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(file_frame, text="Load Project", 
                  command=self.load_project).pack(fill=tk.X, padx=5, pady=2)
                  
        # Character list
        list_frame = ttk.LabelFrame(parent, text="Character List")
        list_frame.pack(fill=tk.X, pady=5)
        
        # Create scrollable character list
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.X, padx=5, pady=5)
        
        self.char_listbox = tk.Listbox(list_container, height=8)
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.char_listbox.yview)
        self.char_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.char_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.char_listbox.bind('<<ListboxSelect>>', self.on_listbox_select)
        
        self.update_character_list()
        self.update_preview()
        
    def draw_grid(self):
        """Draw the editing grid"""
        self.canvas.delete("all")
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                x1 = x * CELL_SIZE + 1
                y1 = y * CELL_SIZE + 1
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                
                color = "black" if self.grid[y][x] else "white"
                self.rects[y][x] = self.canvas.create_rectangle(
                    x1, y1, x2, y2, fill=color, outline="gray")
                    
    def toggle_cell(self, event):
        """Toggle a cell on/off"""
        x = (event.x - 1) // CELL_SIZE
        y = (event.y - 1) // CELL_SIZE
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            self.grid[y][x] ^= 1
            color = "black" if self.grid[y][x] else "white"
            self.canvas.itemconfig(self.rects[y][x], fill=color)
            self.save_current_character()
            self.update_preview()
            
    def paint_cell(self, event):
        """Paint cells when dragging"""
        x = (event.x - 1) // CELL_SIZE
        y = (event.y - 1) // CELL_SIZE
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            if not self.grid[y][x]:  # Only set, don't unset
                self.grid[y][x] = 1
                self.canvas.itemconfig(self.rects[y][x], fill="black")
                self.save_current_character()
                self.update_preview()
                
    def clear_cell(self, event):
        """Clear a cell"""
        x = (event.x - 1) // CELL_SIZE
        y = (event.y - 1) // CELL_SIZE
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            self.grid[y][x] = 0
            self.canvas.itemconfig(self.rects[y][x], fill="white")
            self.save_current_character()
            self.update_preview()
            
    def clear_cell_motion(self, event):
        """Clear cells when dragging with right mouse"""
        self.clear_cell(event)
        
    def load_character(self, char_code):
        """Load a character into the editor"""
        self.current_char = char_code
        
        # Load character data or create empty
        if char_code in self.font_data:
            char_bytes = self.font_data[char_code]
        else:
            char_bytes = [0] * 8
            
        # Convert bytes to grid
        for y in range(8):
            byte_val = char_bytes[y] if y < len(char_bytes) else 0
            for x in range(8):
                self.grid[y][x] = 1 if (byte_val & (0x80 >> x)) else 0
                
        self.draw_grid()
        self.update_character_info()
        self.update_entries()
        self.update_character_list()
        
    def save_current_character(self):
        """Save current grid to font data"""
        char_bytes = []
        for y in range(8):
            byte_val = 0
            for x in range(8):
                if self.grid[y][x]:
                    byte_val |= (0x80 >> x)
            char_bytes.append(byte_val)
        self.font_data[self.current_char] = char_bytes
        
    def update_character_info(self):
        """Update character information display"""
        char = chr(self.current_char) if 32 <= self.current_char <= 126 else "?"
        if self.current_char < 32:
            char_name = f"Control-{self.current_char}"
        elif self.current_char > 126:
            char_name = f"Extended-{self.current_char}"
        else:
            char_name = f"'{char}'"
            
        self.char_info_label.config(
            text=f"Character: {char_name} (Code: {self.current_char}, Hex: 0x{self.current_char:02X})")
            
    def update_entries(self):
        """Update character and code entry fields"""
        self.char_entry.delete(0, tk.END)
        self.code_entry.delete(0, tk.END)
        
        if 32 <= self.current_char <= 126:
            self.char_entry.insert(0, chr(self.current_char))
        self.code_entry.insert(0, str(self.current_char))
        
    def update_character_list(self):
        """Update the character list display"""
        self.char_listbox.delete(0, tk.END)
        
        for char_code in sorted(self.font_data.keys()):
            if 32 <= char_code <= 126:
                char_display = chr(char_code)
            else:
                char_display = "?"
            display_text = f"{char_code:3d} (0x{char_code:02X}) '{char_display}'"
            self.char_listbox.insert(tk.END, display_text)
            
        # Select current character
        try:
            sorted_codes = sorted(self.font_data.keys())
            index = sorted_codes.index(self.current_char)
            self.char_listbox.selection_set(index)
            self.char_listbox.see(index)
        except ValueError:
            pass
            
    def update_preview(self, event=None):
        """Update the text preview"""
        self.preview_canvas.delete("all")
        
        text = self.preview_text.get('1.0', tk.END).strip()
        if not text:
            return
            
        x, y = 5, 5
        char_width, char_height = 8, 8
        
        for line in text.split('\n'):
            current_x = x
            for char in line:
                char_code = ord(char)
                if char_code in self.font_data:
                    self.draw_preview_char(char_code, current_x, y)
                current_x += char_width + 1
            y += char_height + 2
            
    def draw_preview_char(self, char_code, x, y):
        """Draw a character in the preview canvas"""
        if char_code not in self.font_data:
            return
            
        char_bytes = self.font_data[char_code]
        
        for row in range(8):
            byte_val = char_bytes[row] if row < len(char_bytes) else 0
            for col in range(8):
                if byte_val & (0x80 >> col):
                    self.preview_canvas.create_rectangle(
                        x + col, y + row, x + col + 1, y + row + 1,
                        fill="white", outline="white")
                        
    # Event handlers
    def on_char_entry(self, event):
        """Handle character entry"""
        char = self.char_entry.get()
        if char:
            self.load_character(ord(char[0]))
            
    def on_code_entry(self, event):
        """Handle code entry"""
        try:
            code = int(self.code_entry.get())
            if 0 <= code <= 255:
                self.load_character(code)
        except ValueError:
            pass
            
    def on_listbox_select(self, event):
        """Handle listbox selection"""
        selection = self.char_listbox.curselection()
        if selection:
            sorted_codes = sorted(self.font_data.keys())
            char_code = sorted_codes[selection[0]]
            self.load_character(char_code)
            
    def prev_char(self):
        """Go to previous character"""
        new_code = max(0, self.current_char - 1)
        self.load_character(new_code)
        
    def next_char(self):
        """Go to next character"""
        new_code = min(255, self.current_char + 1)
        self.load_character(new_code)
        
    def goto_char(self, char_code):
        """Go to specific character"""
        self.load_character(char_code)
        
    # Editing tools
    def clear_all(self):
        """Clear all pixels"""
        for y in range(8):
            for x in range(8):
                self.grid[y][x] = 0
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    def fill_all(self):
        """Fill all pixels"""
        for y in range(8):
            for x in range(8):
                self.grid[y][x] = 1
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    def invert_all(self):
        """Invert all pixels"""
        for y in range(8):
            for x in range(8):
                self.grid[y][x] ^= 1
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    def shift_left(self):
        """Shift character left"""
        for y in range(8):
            for x in range(7):
                self.grid[y][x] = self.grid[y][x + 1]
            self.grid[y][7] = 0
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    def shift_right(self):
        """Shift character right"""
        for y in range(8):
            for x in range(7, 0, -1):
                self.grid[y][x] = self.grid[y][x - 1]
            self.grid[y][0] = 0
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    def shift_up(self):
        """Shift character up"""
        for y in range(7):
            for x in range(8):
                self.grid[y][x] = self.grid[y + 1][x]
        for x in range(8):
            self.grid[7][x] = 0
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    def shift_down(self):
        """Shift character down"""
        for y in range(7, 0, -1):
            for x in range(8):
                self.grid[y][x] = self.grid[y - 1][x]
        for x in range(8):
            self.grid[0][x] = 0
        self.draw_grid()
        self.save_current_character()
        self.update_preview()
        
    # File operations
    def export_font_data(self):
        """Export font data as raw bytes"""
        filename = filedialog.asksaveasfilename(
            title="Export Font Data",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("# Nova Font Data Export\n")
                    f.write("# Character code: bytes (hex values)\n\n")
                    
                    for char_code in sorted(self.font_data.keys()):
                        char_bytes = self.font_data[char_code]
                        hex_bytes = ",".join(f"0x{b:02X}" for b in char_bytes)
                        
                        if 32 <= char_code <= 126:
                            char_display = repr(chr(char_code))
                        else:
                            char_display = f"code_{char_code}"
                            
                        f.write(f"# {char_code:3d} {char_display}\n")
                        f.write(f"{hex_bytes},\n\n")
                        
                messagebox.showinfo("Export Complete", f"Font data exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")
                
    def export_python_code(self):
        """Export as Python font_data array"""
        filename = filedialog.asksaveasfilename(
            title="Export Python Code",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("# Nova Font Data - Generated by Enhanced Font Maker\n")
                    f.write("# 8x8 pixel characters, 8 bytes per character\n\n")
                    f.write("font_data = [\n")
                    
                    for char_code in sorted(self.font_data.keys()):
                        char_bytes = self.font_data[char_code]
                        
                        if 32 <= char_code <= 126:
                            char_display = chr(char_code)
                            comment = f" # {char_display} ({char_code})"
                        else:
                            comment = f" # code {char_code}"
                            
                        hex_bytes = ",".join(f"0x{b:02X}" for b in char_bytes)
                        f.write(f"    {hex_bytes},{comment}\n")
                        
                    f.write("]\n")
                    
                messagebox.showinfo("Export Complete", f"Python code exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export: {e}")
                
    def import_font_data(self):
        """Import font data from file"""
        filename = filedialog.askopenfilename(
            title="Import Font Data",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'r') as f:
                        data = json.load(f)
                        for char_code_str, char_bytes in data.items():
                            char_code = int(char_code_str)
                            self.font_data[char_code] = char_bytes
                else:
                    # Try to parse as hex data
                    with open(filename, 'r') as f:
                        content = f.read()
                        # Simple parser for hex data
                        import re
                        hex_pattern = r'0x[0-9A-Fa-f]{2}'
                        matches = re.findall(hex_pattern, content)
                        
                        if len(matches) % 8 == 0:
                            char_code = 32  # Start from space
                            for i in range(0, len(matches), 8):
                                char_bytes = [int(h, 16) for h in matches[i:i+8]]
                                self.font_data[char_code] = char_bytes
                                char_code += 1
                                
                self.load_character(self.current_char)
                messagebox.showinfo("Import Complete", f"Font data imported from {filename}")
            except Exception as e:
                messagebox.showerror("Import Error", f"Failed to import: {e}")
                
    def save_project(self):
        """Save project as JSON"""
        filename = filedialog.asksaveasfilename(
            title="Save Project",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                project_data = {
                    'font_data': {str(k): v for k, v in self.font_data.items()},
                    'current_char': self.current_char,
                    'preview_text': self.preview_text.get('1.0', tk.END).strip()
                }
                with open(filename, 'w') as f:
                    json.dump(project_data, f, indent=2)
                messagebox.showinfo("Save Complete", f"Project saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save: {e}")
                
    def load_project(self):
        """Load project from JSON"""
        filename = filedialog.askopenfilename(
            title="Load Project",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    project_data = json.load(f)
                    
                self.font_data = {int(k): v for k, v in project_data['font_data'].items()}
                
                if 'current_char' in project_data:
                    self.current_char = project_data['current_char']
                    
                if 'preview_text' in project_data:
                    self.preview_text.delete('1.0', tk.END)
                    self.preview_text.insert('1.0', project_data['preview_text'])
                    
                self.load_character(self.current_char)
                messagebox.showinfo("Load Complete", f"Project loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load: {e}")

def create_full_printable_range():
    """Create a font maker with the full printable range pre-populated"""
    root = tk.Tk()
    app = EnhancedFontMaker(root)
    
    # Add commonly needed characters that aren't in the basic set
    extended_chars = {
        # Currency symbols
        163: "£", 164: "¤", 165: "¥", 
        # Accented letters
        192: "À", 193: "Á", 194: "Â", 195: "Ã", 196: "Ä", 197: "Å",
        199: "Ç", 200: "È", 201: "É", 202: "Ê", 203: "Ë",
        204: "Ì", 205: "Í", 206: "Î", 207: "Ï",
        209: "Ñ", 210: "Ò", 211: "Ó", 212: "Ô", 213: "Õ", 214: "Ö",
        217: "Ù", 218: "Ú", 219: "Û", 220: "Ü",
        224: "à", 225: "á", 226: "â", 227: "ã", 228: "ä", 229: "å",
        231: "ç", 232: "è", 233: "é", 234: "ê", 235: "ë",
        236: "ì", 237: "í", 238: "î", 239: "ï",
        241: "ñ", 242: "ò", 243: "ó", 244: "ô", 245: "õ", 246: "ö",
        249: "ù", 250: "ú", 251: "û", 252: "ü",
        # Common symbols
        161: "¡", 162: "¢", 166: "¦", 167: "§", 168: "¨", 169: "©",
        170: "ª", 171: "«", 172: "¬", 173: "­", 174: "®", 175: "¯",
        176: "°", 177: "±", 178: "²", 179: "³", 180: "´", 181: "µ",
        182: "¶", 183: "·", 184: "¸", 185: "¹", 186: "º", 187: "»",
        188: "¼", 189: "½", 190: "¾", 191: "¿",
    }
    
    # Create empty character data for extended characters
    for char_code in extended_chars.keys():
        if char_code not in app.font_data:
            app.font_data[char_code] = [0] * 8
            
    app.update_character_list()
    return root, app

if __name__ == "__main__":
    root, app = create_full_printable_range()
    root.mainloop()
