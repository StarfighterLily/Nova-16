struct Player {
    int x;
    int y;
    int oldx;
    int oldy;
    int facing;
    int counter;
    int swx;
    int swy;
    int swinging;
} Player = {120, 120};

struct Enemy {
    int ex;
    int ey;
    int oldex;
    int oldey;
    int ehit;
} Enemy = {0, 128};

void clearSwing() {
    if (Player.swinging == 1) {
        set_layer(5);
        set_pos(Player.swx, Player.swy);
        write_text("--", 0x00);
        Player.swinging = 0;
    }
}

void swordSwing() {
    string sword;
    clearSwing();   
    Player.counter = 0;
    sword = "--";
    if (Player.facing == 1) {
        Player.swx = Player.x - 16;
        Player.swy = Player.y + 8;
    }
    if (Player.facing == 2) {
        Player.swx = Player.x + 8;
        Player.swy = Player.y + 8;
    }
    if (Player.facing != 0) {
        set_layer(5);
        set_pos(Player.swx, Player.swy);
        write_text(sword, 0x1F);
        Player.swinging = 1;
    }
}

void chkKey() {
    int key;
    int ox, oy;
    if (key_available()) {
        key = key_read();
        ox = Player.x;
        oy = Player.y;
        if (key) {
            clearSwing();
        }
        if (key == 101) {
            // sword swing
            swordSwing();
        }
        if (key == 97 && Player.x > 8) {
            // move left
            Player.x -= 8;
            if (Player.x < 8) {
                Player.x = 8;
            }
            Player.facing = 1;
        }
        if (key == 128 && Player.x > 8) {
            // move left (alternative key)
            Player.x -= 8;
            if (Player.x < 8) {
                Player.x = 8;
            }
            Player.facing = 1;
        }
        if (key == 100 && Player.x < 248) {
            // move right
            Player.x += 8;
            if (Player.x > 248) {
                Player.x = 248;
            }
            Player.facing = 2;
        }
        if (key == 129 && Player.x < 248) {
            // move right (alternative key)
            Player.x += 8;
            if (Player.x > 248) {
                Player.x = 248;
            }
            Player.facing = 2;
        }
        if (key == 119 && Player.y > 8) {
            // move up
            Player.y -= 8;
            if (Player.y < 8) {
                Player.y = 8;
            }
        }
        if (key == 130 && Player.y > 8) {
            // move up (alternative key)
            Player.y -= 8;
            if (Player.y < 8) {
                Player.y = 8;
            }
        }
        if (key == 115 && Player.y < 240) {
            // move down
            Player.y += 8;
            if (Player.y > 240) {
                Player.y = 240;
            }
        }
        if (key == 131 && Player.y < 240) {
            // move down (alternative key)
            Player.y += 8;
            if (Player.y > 240) {
                Player.y = 240;
            }
        }
        if (ox != Player.x || oy != Player.y) {
            Player.oldx = ox;
            Player.oldy = oy;
        }
    }
}

void drawPlayer(int x, int y) {
    set_layer(5);
    if (Player.oldx != x || Player.oldy != y) {
        set_pos(Player.oldx, Player.oldy);
        write_text("O", 0x00);
        set_pos(Player.oldx, Player.oldy + 8);
        write_text("X", 0x00);
    }
    set_pos(x, y);
    write_text("O", 0x1F);
    set_pos(x, y + 8);
    write_text("X", 0x1F);
}

void enemy(){
    Enemy.oldex = Enemy.ex;
    Enemy.oldey = Enemy.ey;
    int walk = random_range(1, 4089);

    if (Enemy.ex < 8) {
        Enemy.ex = 8;
    }
    if (Enemy.ey < 8) {
        Enemy.ey = 8;
    }
    if (Enemy.ex > 240) {
        Enemy.ex = 240;
    }
    if (Enemy.ey > 240) {
        Enemy.ey = 240;
    }

    if (walk == 1 && Enemy.ex > 8) {
        // move left
        Enemy.ex -= 8;
    }
    if (walk == 64 && Enemy.ex < 240) {
        // move right
        Enemy.ex += 8;
    }
    if (walk == 256 && Enemy.ey > 8) {
        // move up
        Enemy.ey -= 8;
    }
    if (walk == 1024 && Enemy.ey < 232) {
        // move down
        Enemy.ey += 8;
    }
    if (walk != 1 && walk != 8 && walk != 16 && walk != 32) {
        // stay in place
    }

    if (Enemy.ex == Player.swx && Enemy.ey == Player.swy) {
        Enemy.ehit = 1;
    } else if (Enemy.ex == Player.swx + 8 && Enemy.ey == Player.swy) {
        Enemy.ehit = 1;
    } else if (Enemy.ex == Player.swx - 8 && Enemy.ey == Player.swy) {
        Enemy.ehit = 1;
    } else {
        Enemy.ehit = 0;
    }

    set_layer(6);
    set_pos(Enemy.ex, Enemy.ey);
    write_text("m", 0x0F);
    if (Enemy.oldex != Enemy.ex || Enemy.oldey != Enemy.ey) {
        set_pos(Enemy.oldex, Enemy.oldey);
        write_text("m", 0x00);
    }
}

void print(int layer, int x, int y, string text, int color) {
    set_layer(layer);
    set_pos(x, y);
    write_text((string)text, color);
}

void levelDraw() {
    for (int i = 0; i < 256; i + 8) {
        set_layer(1);
        set_pos(0, i);
        write_text("X                              X", 0x1F);
    }
    screen_rotate(0,1);
    for (int i = 0; i < 256; i + 8) {
        set_layer(1);
        set_pos(0, i);
        write_text("X                              X", 0x1F);
    }
}

void clearSword() {
    if (Player.counter > 255) {
        Player.counter = 0;
        clearSwing();
    }
}

void clearLayers() {
    for (int i = 0; i < 8; i++) {
        set_layer(i);
        screen_fill(0x00);
    }
}