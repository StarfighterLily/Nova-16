import tkinter as tk

CELL_SIZE = 30
GRID_SIZE = 8

class FontEditor:
    def __init__(self, master):
        self.master = master
        self.master.title("Fantasy Font Editor")
        self.canvas = tk.Canvas(master, width=CELL_SIZE*GRID_SIZE, height=CELL_SIZE*GRID_SIZE)
        self.canvas.pack()

        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.rects = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.draw_grid()

        self.canvas.bind("<Button-1>", self.toggle_cell)

        self.button = tk.Button(master, text="Export Font Data", command=self.export_data)
        self.button.pack()

        self.output = tk.Text(master, height=2, width=40)
        self.output.pack()

    def draw_grid(self):
        for y in range(GRID_SIZE):
            for x in range(GRID_SIZE):
                x1 = x * CELL_SIZE
                y1 = y * CELL_SIZE
                x2 = x1 + CELL_SIZE
                y2 = y1 + CELL_SIZE
                self.rects[y][x] = self.canvas.create_rectangle(x1, y1, x2, y2, fill="white", outline="black")

    def toggle_cell(self, event):
        x = event.x // CELL_SIZE
        y = event.y // CELL_SIZE
        if 0 <= x < GRID_SIZE and 0 <= y < GRID_SIZE:
            self.grid[y][x] ^= 1
            color = "black" if self.grid[y][x] else "white"
            self.canvas.itemconfig(self.rects[y][x], fill=color)

    def export_data(self):
        bytes_out = []
        for row in self.grid:
            bits = ''.join(str(b) for b in row)
            byte = int(bits, 2)
            bytes_out.append(f"0x{byte:02X}")
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, ",".join(bytes_out))

if __name__ == "__main__":
    root = tk.Tk()
    app = FontEditor(root)
    root.mainloop()
