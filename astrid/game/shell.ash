int cursor[2] = {0, 0};

char key(int keycode) {
    switch (keycode) {
        case 48:
            return "0";
            break;
        case 49:
            return "1";
            break;
        case 50:
            return "2";
            break;
        case 51:
            return "3";
            break;
        case 52:
            return "4";
            break;
        case 53:
            return "5";
            break;
        case 54:
            return "6";
            break;
        case 55:
            return "7";
            break;
        case 56:
            return "8";
            break;
        case 57:
            return "9";
            break;
        case 65:
            return "A";
            break;
        case 66:
            return "B";
            break;
        case 67:
            return "C";
            break;
        case 68:
            return "D";
            break;
        case 69:
            return "E";
            break;
        case 70:
            return "F";
            break;
        case 71:
            return "G";
            break;
        case 72:
            return "H";
            break;
        case 73:
            return "I";
            break;
        case 74:
            return "J";
            break;
        case 75:
            return "K";
            break;
        case 76:
            return "L";
            break;
        case 77:
            return "M";
            break;
        case 78:
            return "N";
            break;
        case 79:
            return "O";
            break;
        case 80:
            return "P";
            break;
        case 81:
            return "Q";
            break;
        case 82:
            return "R";
            break;
        case 83:
            return "S";
            break;
        case 84:
            return "T";
            break;
        case 85:
            return "U";
            break;
        case 86:
            return "V";
            break;
        case 87:
            return "W";
            break;
        case 88:
            return "X";
            break;
        case 89:
            return "Y";
            break;
        case 90:
            return "Z";
            break;
        case 97:
            return "a";
            break;
        case 98:
            return "b";
            break;
        case 99:
            return "c";
            break;
        case 100:
            return "d";
            break;
        case 101:
            return "e";
            break;
        case 102:
            return "f";
            break;
        case 103:
            return "g";
            break;
        case 104:
            return "h";
            break;
        case 105:
            return "i";
            break;
        case 106:
            return "j";
            break;
        case 107:
            return "k";
            break;
        case 108:
            return "l";
            break;
        case 109:
            return "m";
            break;
        case 110:
            return "n";
            break;
        case 111:
            return "o";
            break;
        case 112:
            return "p";
            break;
        case 113:
            return "q";
            break;
        case 114:
            return "r";
            break;
        case 115:
            return "s";
            break;
        case 116:
            return "t";
            break;
        case 117:
            return "u";
            break;
        case 118:
            return "v";
            break;
        case 119:
            return "w";
            break;
        case 120:
            return "x";
            break;
        case 121:
            return "y";
            break;
        case 122:
            return "z";
            break;
    }
}

string input() {
    string word;
    if (key_available()) {
        while (key_read() != 10) {
            if (key_read()) {
                set_pos(cursor[0], cursor[1]);
                draw_char(key(key_read()), 0x0F);
                strcat(word, key(key_read()));
                if (cursor[0] == 255) {
                    cursor[0] = 0;
                    cursor[1] += 8;
                }
                if (cursor[1] == 255) {
                    cursor[1] = 0;
                    screen_shift(0, 8);
                }
                cursor[0] += 8;
                key_clear();
            }
        }
        return word;
    } else {
        return "";
    }
}