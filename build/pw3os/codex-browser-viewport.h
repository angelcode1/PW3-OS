/* Browser frame and touch viewport mapping for PW3.
 * Pure math: no evdev, framebuffer, SDL, kernel ioctls or device writes.
 * Must agree exactly with verify_direct_sdl.py's nearest-neighbour
 * letterbox conversion. A touch outside the content area is ignored.
 */
#ifndef CODEX_BROWSER_VIEWPORT_H
#define CODEX_BROWSER_VIEWPORT_H
typedef struct { int left, top, width, height; } codex_browser_viewport;
typedef struct { int x, y; } codex_browser_point;
/* returns 0 on success, -1 for unsupported dimensions */
int codex_browser_make_viewport(int screen_w, int screen_h, int browser_w,
                                int browser_h, codex_browser_viewport *out);
/* returns 1 if mapped, 0 for the letterbox, -1 for invalid inputs */
int codex_browser_map_touch(int screen_x, int screen_y,
                            int screen_w, int screen_h,
                            int browser_w, int browser_h,
                            codex_browser_point *out);
#endif
