/* Match the Python browser capture's integer-rational fit exactly. */
#include "codex-browser-viewport.h"
#include <stdint.h>

int codex_browser_make_viewport(int screen_w, int screen_h, int browser_w,
                                int browser_h, codex_browser_viewport *out) {
    if (!out || screen_w < 2 || screen_h < 2 ||
        browser_w < 2 || browser_h < 2 ||
        screen_w > 2048 || screen_h > 2048 ||
        browser_w > 2048 || browser_h > 2048)
        return -1;
    int w, h;
    if ((int64_t)screen_w * browser_h <= (int64_t)screen_h * browser_w) {
        w=screen_w;
        h=(int)((int64_t)browser_h * screen_w / browser_w);
        if (h < 1) h=1;
    } else {
        h=screen_h;
        w=(int)((int64_t)browser_w * screen_h / browser_h);
        if (w < 1) w=1;
    }
    if (w > screen_w || h > screen_h) return -1;
    *out=(codex_browser_viewport){(screen_w-w)/2, (screen_h-h)/2, w, h};
    return 0;
}

int codex_browser_map_touch(int screen_x, int screen_y,
                            int screen_w, int screen_h,
                            int browser_w, int browser_h,
                            codex_browser_point *out) {
    if (!out) return -1;
    codex_browser_viewport v;
    if (codex_browser_make_viewport(screen_w,screen_h,browser_w,browser_h,&v))
        return -1;
    if (screen_x < v.left || screen_x >= v.left+v.width ||
        screen_y < v.top || screen_y >= v.top+v.height)
        return 0;
    int x=(int)((int64_t)(screen_x-v.left)*browser_w/v.width);
    int y=(int)((int64_t)(screen_y-v.top)*browser_h/v.height);
    if (x >= browser_w) x=browser_w-1;
    if (y >= browser_h) y=browser_h-1;
    *out=(codex_browser_point){x,y};
    return 1;
}
