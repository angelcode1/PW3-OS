#include "codex-touch-bridge.h"
#include <stdint.h>
#include <stddef.h>

static int clamp(int n, int lo, int hi) {
    return n<lo ? lo : n>hi ? hi : n;
}
static int scale(int value,int max_from,int max_to) {
    return (int)((int64_t)value*(max_to-1)/(max_from-1));
}

int codex_touch_translate(codex_touch_state *state,
                          const codex_touch_transform *tf,
                          codex_touch_phase phase, int raw_x, int raw_y,
                          codex_pointer_event events[2]) {
    if (!state || !tf || !events || tf->raw_w<2 || tf->raw_h<2 ||
        tf->screen_w<2 || tf->screen_h<2 || phase<CODEX_TOUCH_DOWN ||
        phase>CODEX_TOUCH_CANCEL) return -1;
    if (phase==CODEX_TOUCH_CANCEL) {
        if (!state->active) return 0;
        events[0]=(codex_pointer_event){state->x,state->y,CODEX_PTR_UP};
        state->active=0;
        return 1;
    }
    int x=clamp(raw_x,0,tf->raw_w-1),y=clamp(raw_y,0,tf->raw_h-1);
    int rw=tf->raw_w,rh=tf->raw_h;
    if (tf->swap_xy) {
        int t=x;x=y;y=t;t=rw;rw=rh;rh=t;
    }
    x=scale(x,rw,tf->screen_w);
    y=scale(y,rh,tf->screen_h);
    if (tf->invert_x) x=tf->screen_w-1-x;
    if (tf->invert_y) y=tf->screen_h-1-y;
    if (phase==CODEX_TOUCH_DOWN) {
        if (state->active) return 0;  /* Ignore overlapping fingers. */
        state->active=1;state->x=x;state->y=y;
        events[0]=(codex_pointer_event){x,y,CODEX_PTR_MOVE};
        events[1]=(codex_pointer_event){x,y,CODEX_PTR_DOWN};
        return 2;
    }
    if (!state->active) return 0;
    state->x=x;state->y=y;
    events[0]=(codex_pointer_event){x,y,CODEX_PTR_MOVE};
    if (phase==CODEX_TOUCH_MOVE) return 1;
    events[1]=(codex_pointer_event){x,y,CODEX_PTR_UP};
    state->active=0;
    return 2;
}
