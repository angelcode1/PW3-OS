/* Pure pointer-event translation; no evdev opens and no libnsfb dependency.
 * A future surface driver converts CODEX_PTR events to libnsfb nsfb_event_t.
 */
#ifndef CODEX_TOUCH_BRIDGE_H
#define CODEX_TOUCH_BRIDGE_H
typedef enum { CODEX_TOUCH_DOWN, CODEX_TOUCH_MOVE, CODEX_TOUCH_UP, CODEX_TOUCH_CANCEL } codex_touch_phase;
typedef enum { CODEX_PTR_MOVE, CODEX_PTR_DOWN, CODEX_PTR_UP } codex_pointer_type;
typedef struct { int x, y; codex_pointer_type type; } codex_pointer_event;
typedef struct {
    int raw_w, raw_h, screen_w, screen_h;
    int swap_xy, invert_x, invert_y;
} codex_touch_transform;
typedef struct { int active, x, y; } codex_touch_state;

/* Returns events produced (0..2), or -1 on invalid transform/output. */
int codex_touch_translate(codex_touch_state *state,
                          const codex_touch_transform *transform,
                          codex_touch_phase phase, int raw_x, int raw_y,
                          codex_pointer_event events[2]);
#endif
