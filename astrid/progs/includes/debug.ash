struct dbg {
    int x;
    int y;
} dbg = {0,0};

impl dbg {
    void print(self, string text) {
        set_pos(self.x, self.y);
        write_text(text, 0x1F);
        self.y += 8;
        if (self.y > 240) {
            y = 0;
        }
    }
}