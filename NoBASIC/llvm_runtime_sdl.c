/*
 * NoBASIC SDL Runtime Library for x86-64
 * 
 * Provides implementations of Nova-16 hardware functions using SDL for
 * native execution. Creates a 256x256 window scaled 3x.
 * Link with generated LLVM IR: clang program.ll nobasic_sdl_runtime.c -o program.exe
 */

#include "nobasic_sdl_runtime.h"
#include <stdint.h>

/* Keyboard input state */
static int16_t g_key_state = 0;

/* Graphics functions - full SDL implementations */
void clrdraw(void) {
    nobasic_clrdraw();
    nobasic_gfx_present();
}

void pxlon(int16_t x, int16_t y, int16_t color) {
    nobasic_pxlon(x, y, color);
    nobasic_gfx_present();
}

void pxloff(int16_t x, int16_t y) {
    nobasic_pxloff(x, y);
    nobasic_gfx_present();
}

void line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, int16_t color) {
    nobasic_line(x1, y1, x2, y2, color);
    nobasic_gfx_present();
}

void circle(int16_t x, int16_t y, int16_t radius, int16_t color) {
    nobasic_circle(x, y, radius, color);
    nobasic_gfx_present();
}

void text(int16_t x, int16_t y, char* str, int16_t color) {
    nobasic_text(x, y, str, color);
    nobasic_gfx_present();
}

void setlayer(int16_t layer) {
    nobasic_setlayer(layer);
}

void scrroll(int16_t axis, int16_t amount) {
    /* TODO: Implement screen scroll */
}

void scrrotate(int16_t direction, int16_t amount) {
    /* TODO: Implement screen rotation */
}

void scrshift(int16_t axis, int16_t amount) {
    /* TODO: Implement screen shift */
}

void scrflip(int16_t axis) {
    /* TODO: Implement screen flip */
}

void spriteon(int16_t sprite_id, int16_t x, int16_t y) {
    /* TODO: Implement sprite system */
}

void spriteoff(int16_t sprite_id) {
    /* TODO: Implement sprite system */
}

/* Sound functions - stubs (could use SDL audio) */
void playtone(int16_t frequency, int16_t duration, int16_t volume) {
    /* TODO: Implement SDL audio tone playback */
}

void playwave(int16_t waveform, int16_t frequency, int16_t volume) {
    /* TODO: Implement SDL audio wave playback */
}

void stopsound(void) {
    /* TODO: Implement SDL audio stop */
}

void setchannel(int16_t channel) {
    /* TODO: Implement SDL audio channel selection */
}

/* Input/Output functions */
int16_t getkey(void) {
    /* Process events first */
    nobasic_process_events();
    int16_t key = g_key_state;
    g_key_state = 0;
    return key;
}

void pause(void) {
    /* Wait for a key press by blocking until event */
    SDL_Event event;
    while (1) {
        nobasic_process_events();
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_KEYDOWN || event.type == SDL_QUIT) {
                if (event.type == SDL_QUIT) {
                    g_key_state = -1;  /* Signal exit */
                } else {
                    g_key_state = event.key.keysym.sym & 0xFF;
                }
                return;
            }
        }
        /* Yield to prevent 100% CPU */
        SDL_Delay(10);
    }
}

void disp(char* text) {
    /* Display to console for now */
}

void input(char* prompt, int16_t* var) {
    /* Console input stub */
}

/* Serial functions - stubs */
void serout(int16_t value) {
    /* TODO: Implement serial output */
}

int16_t serin(void) {
    return 0;
}

int16_t serstat(void) {
    return 0;
}

void serctrl(int16_t value) {
    /* TODO: Implement serial control */
}

/* Math functions - basic implementations */
int16_t sin(int16_t x) {
    /* Placeholder - would need actual sine table */
    return 0;
}

int16_t cos(int16_t x) {
    return 0;
}

int16_t tan(int16_t x) {
    return 0;
}

int16_t sqrt(int16_t x) {
    /* Integer square root */
    if (x <= 0) return 0;
    int16_t r = x;
    while (1) {
        int16_t n = (r + x / r) / 2;
        if (n >= r) break;
        r = n;
    }
    return r;
}

int16_t abs(int16_t x) {
    return x < 0 ? -x : x;
}

int16_t intgr(int16_t x) {
    return x;
}

int16_t round(int16_t x) {
    return x;
}

int16_t powr(int16_t base, int16_t exp) {
    int16_t result = 1;
    if (exp < 0) return 0;
    for (int16_t i = 0; i < exp; i++) {
        result *= base;
        if (result > 32767 || result < -32768) return 32767;
    }
    return result;
}

int16_t log(int16_t x) {
    /* Natural log approximation stub */
    return 0;
}

int16_t min(int16_t a, int16_t b) {
    return a < b ? a : b;
}

int16_t max(int16_t a, int16_t b) {
    return a > b ? a : b;
}

void itoa(int16_t val, char* str) {
    /* Convert to string - simple implementation */
    if (val < 0) {
        *str++ = '-';
        val = -val;
    }
    int16_t temp[5];
    int i = 0;
    do {
        temp[i++] = '0' + (val % 10);
        val /= 10;
    } while (val > 0);
    while (i > 0) {
        *str++ = temp[--i];
    }
    *str = 0;
}

/* Random functions */
static int16_t g_rnd_seed = 1;

int16_t rand(void) {
    /* Simple LCG random */
    g_rnd_seed = (g_rnd_seed * 1103515245 + 12345) & 0x7FFF;
    return (int16_t)g_rnd_seed;
}

int16_t rndr(int16_t min, int16_t max) {
    int16_t range = max - min + 1;
    return min + (rand() % range);
}

void randomize(int16_t seed) {
    g_rnd_seed = seed;
    if (g_rnd_seed == 0) g_rnd_seed = 1;
}

/* String functions */
int16_t strlen(char* str) {
    int16_t len = 0;
    while (str[len] != 0) len++;
    return len;
}

void strcpy(char* dest, char* src) {
    while (*src) *dest++ = *src++;
    *dest = 0;
}

void strcat(char* dest, char* src) {
    while (*dest) dest++;
    while (*src) *dest++ = *src++;
    *dest = 0;
}

int16_t strcmp(char* s1, char* s2, int16_t len) {
    for (int16_t i = 0; i < len; i++) {
        if (s1[i] != s2[i]) return (s1[i] < s2[i]) ? -1 : 1;
        if (s1[i] == 0) return 0;
    }
    return 0;
}

int16_t strupr(char* str) {
    for (int i = 0; str[i]; i++) {
        if (str[i] >= 'a' && str[i] <= 'z') {
            str[i] -= 32;
        }
    }
    return 0;
}

int16_t strlwr(char* str) {
    for (int i = 0; str[i]; i++) {
        if (str[i] >= 'A' && str[i] <= 'Z') {
            str[i] += 32;
        }
    }
    return 0;
}

int16_t strrev(char* str) {
    int len = 0;
    while (str[len]) len++;
    for (int i = 0; i < len / 2; i++) {
        char tmp = str[i];
        str[i] = str[len - 1 - i];
        str[len - 1 - i] = tmp;
    }
    return 0;
}

int16_t strfind(char* haystack, char* needle) {
    for (int i = 0; haystack[i]; i++) {
        int found = 1;
        for (int j = 0; needle[j]; j++) {
            if (haystack[i + j] != needle[j]) {
                found = 0;
                break;
            }
        }
        if (found) return i;
    }
    return -1;
}

int16_t strfindi(char* haystack, char* needle) {
    /* Case-insensitive find - stub */
    return strfind(haystack, needle);
}

void strext(char* dest, int16_t start, int16_t len, char* haystack) {
    for (int16_t i = 0; i < len && haystack[start + i]; i++) {
        dest[i] = haystack[start + i];
    }
    dest[len] = 0;
}

/* Memory access functions - stubs (no actual memory access in native mode) */
int16_t memread(int16_t addr) {
    return 0;
}

void memwrite(int16_t addr, int16_t value) {
    /* No-op in native mode */
}

/* SDL initialization and main entry point */
int main(void) {
    /* Initialize SDL graphics */
    if (nobasic_gfx_init() < 0) {
        return 1;  /* Failed to initialize */
    }
    
    /* Call NoBASIC main (the generated LLVM code) */
    extern int nobasic_main(void);
    int result = nobasic_main();
    
    /* Cleanup SDL */
    nobasic_gfx_shutdown();
    
    return result;
}
