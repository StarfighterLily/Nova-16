/*
 * NoBASIC Runtime Stub Library for x86-64
 * 
 * Provides implementations of Nova-16 hardware functions for native execution.
 * Link with generated LLVM IR: clang program.ll runtime.c -o program.exe
 * 
 * Compile with: clang -fno-builtin runtime.c -c -o runtime.o
 * Then link: clang program.ll runtime.o -o program.exe
 */

#include <stdint.h>

/* Graphics functions - stubs for now (could implement basic terminal output) */
void clrdraw(void) { }
void pxlon(int16_t x, int16_t y, int16_t color) { }
void pxloff(int16_t x, int16_t y) { }
void line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, int16_t color) { }
void circle(int16_t x, int16_t y, int16_t radius, int16_t color) { }
void text(int16_t x, int16_t y, char* str, int16_t color) { }
void setlayer(int16_t layer) { }
void scrroll(int16_t axis, int16_t amount) { }
void scrrotate(int16_t direction, int16_t amount) { }
void scrshift(int16_t axis, int16_t amount) { }
void scrflip(int16_t axis) { }
void spriteon(int16_t sprite_id, int16_t x, int16_t y) { }
void spriteoff(int16_t sprite_id) { }

/* Sound functions - stubs */
void playtone(int16_t frequency, int16_t duration, int16_t volume) { }
void playwave(int16_t waveform, int16_t frequency, int16_t volume) { }
void stopsound(void) { }
void setchannel(int16_t channel) { }

/* Input/Output functions */
int16_t getkey(void) { return 0; }
void pause(void) { }
void disp(char* text) { }
void input(char* prompt, int16_t* var) { }

/* Serial functions */
void serout(int16_t value) { }
int16_t serin(void) { return 0; }
int16_t serstat(void) { return 0; }
void serctrl(int16_t value) { }

/* Math functions - stubs */
int16_t sin(int16_t x) { return x; }
int16_t cos(int16_t x) { return x; }
int16_t tan(int16_t x) { return x; }
int16_t sqrt(int16_t x) { return x; }
int16_t abs(int16_t x) { return x < 0 ? -x : x; }
int16_t intgr(int16_t x) { return x; }
int16_t round(int16_t x) { return x; }
int16_t powr(int16_t base, int16_t exp) { return exp; }
int16_t log(int16_t x) { return x; }
int16_t min(int16_t a, int16_t b) { return a < b ? a : b; }
int16_t max(int16_t a, int16_t b) { return a > b ? a : b; }
void itoa(int16_t val, char* str) { }

/* Random functions */
int16_t rand(void) { return 0; }
int16_t rndr(int16_t min, int16_t max) { return min; }
void randomize(int16_t seed) { }

/* String functions - minimal implementations */
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

int16_t strcmp(char* s1, char* s2, int16_t len) { return 0; }
int16_t strupr(char* str) { return 0; }
int16_t strlwr(char* str) { return 0; }
int16_t strrev(char* str) { return 0; }
int16_t strfind(char* haystack, char* needle) { return -1; }
int16_t strfindi(char* haystack, char* needle) { return -1; }
void strext(char* dest, int16_t start, int16_t len, char* haystack) { }

/* Memory access functions */
int16_t memread(int16_t addr) { return 0; }
void memwrite(int16_t addr, int16_t value) { }

/* Main entry point - calls the generated NoBASIC code */
int main(void) {
    extern int nobasic_main(void);
    return nobasic_main();
}
