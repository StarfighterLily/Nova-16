/*
 * NoBASIC SDL Runtime Graphics Header
 * 
 * Provides SDL-based implementations of Nova-16 graphics functions.
 * This header defines the graphics state and pixel buffer for the runtime.
 */

#ifndef NOBASIC_SDL_RUNTIME_H
#define NOBASIC_SDL_RUNTIME_H

#include "SDL.h"
#include "SDL_render.h"
#include "SDL_pixels.h"
#include <stdint.h>

/* Nova-16 graphics dimensions */
#define NOVA_WIDTH 256
#define NOVA_HEIGHT 256
#define NOVA_SCALE 3

/* Color palette: 256 colors matching Nova-16 palette */
extern SDL_Color nova_palette[256];

/* Graphics state - globals for SDL window/renderer/texture */
extern SDL_Window *g_window;
extern SDL_Renderer *g_renderer;
extern SDL_Texture *g_texture;

/* Entry point for NoBASIC programs */
int main(void);

/* Initialize SDL graphics */
int nobasic_gfx_init(void);

/* Shutdown SDL graphics */
void nobasic_gfx_shutdown(void);

/* Present the frame buffer to the screen */
void nobasic_gfx_present(void);

/* Clear the screen (ClrDraw) */
void nobasic_clrdraw(void);

/* Draw pixel on (PxlOn) */
void nobasic_pxlon(int16_t x, int16_t y, int16_t color);

/* Draw pixel off (PxlOff) */
void nobasic_pxloff(int16_t x, int16_t y);

/* Draw line */
void nobasic_line(int16_t x1, int16_t y1, int16_t x2, int16_t y2, int16_t color);

/* Draw circle */
void nobasic_circle(int16_t x, int16_t y, int16_t radius, int16_t color);

/* Draw text */
void nobasic_text(int16_t x, int16_t y, const char *str, int16_t color);

/* Set current layer */
void nobasic_setlayer(int16_t layer);

/* Process SDL events (for non-blocking key input) */
void nobasic_process_events(void);

#endif /* NOBASIC_SDL_RUNTIME_H */