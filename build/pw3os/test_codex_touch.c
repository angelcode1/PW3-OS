#include "codex-touch-bridge.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    codex_touch_transform tf={1072,1448,1072,1448,0,0,0};
    codex_touch_state state={0,0,0};
    codex_pointer_event out[2];
    int n=codex_touch_translate(&state,&tf,CODEX_TOUCH_DOWN,13,42,out);
    assert(n==2 && state.active);
    assert(out[0].type==CODEX_PTR_MOVE && out[0].x==13 && out[0].y==42);
    assert(out[1].type==CODEX_PTR_DOWN);
    n=codex_touch_translate(&state,&tf,CODEX_TOUCH_MOVE,30,50,out);
    assert(n==1 && out[0].type==CODEX_PTR_MOVE && out[0].x==30);
    n=codex_touch_translate(&state,&tf,CODEX_TOUCH_UP,30,50,out);
    assert(n==2 && out[1].type==CODEX_PTR_UP && !state.active);
    assert(codex_touch_translate(&state,&tf,CODEX_TOUCH_UP,30,50,out)==0);
    assert(codex_touch_translate(&state,&tf,CODEX_TOUCH_DOWN,50,60,out)==2);
    assert(codex_touch_translate(&state,&tf,CODEX_TOUCH_DOWN,70,80,out)==0);
    assert(codex_touch_translate(&state,&tf,CODEX_TOUCH_CANCEL,0,0,out)==1);
    assert(out[0].type==CODEX_PTR_UP && !state.active);
    tf.swap_xy=1;tf.invert_x=1;tf.invert_y=1;
    n=codex_touch_translate(&state,&tf,CODEX_TOUCH_DOWN,0,0,out);
    assert(n==2 && out[0].x==1071 && out[0].y==1447);
    assert(codex_touch_translate(&state,&tf,CODEX_TOUCH_CANCEL,0,0,out)==1);
    tf.raw_w=0;
    assert(codex_touch_translate(&state,&tf,CODEX_TOUCH_DOWN,0,0,out)==-1);
    puts("CODEX_TOUCH_OFFSCREEN_BRIDGE_PASS");
    return 0;
}
