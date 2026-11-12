#include "codex-browser-viewport.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    codex_browser_viewport v={0};
    codex_browser_point p={0};
    /* Headless NetSurf is currently 600x800; output is 1072x1448. */
    assert(codex_browser_make_viewport(1072,1448,600,800,&v)==0);
    assert(v.width==1072 && v.height==1429 && v.left==0 && v.top==9);
    assert(codex_browser_map_touch(0,0,1072,1448,600,800,&p)==0);
    assert(codex_browser_map_touch(0,8,1072,1448,600,800,&p)==0);
    assert(codex_browser_map_touch(0,9,1072,1448,600,800,&p)==1);
    assert(p.x==0 && p.y==0);
    assert(codex_browser_map_touch(1071,1437,1072,1448,600,800,&p)==1);
    assert(p.x==599 && p.y==799);
    assert(codex_browser_map_touch(1071,1438,1072,1448,600,800,&p)==0);
    assert(codex_browser_map_touch(536,723,1072,1448,600,800,&p)==1);
    assert(p.x==300 && p.y==399);
    /* Physically recorded swipe begins at (234,729), ends (780,700).
     * No software rotation: both points remain within content bounds. */
    assert(codex_browser_map_touch(234,729,1072,1448,600,800,&p)==1);
    assert(p.x==130 && p.y==403);
    assert(codex_browser_map_touch(780,700,1072,1448,600,800,&p)==1);
    assert(p.x==436 && p.y==386);
    /* Scaled down viewports are also mapped, retaining full source bounds. */
    assert(codex_browser_make_viewport(480,800,600,800,&v)==0);
    assert(v.width==480 && v.height==640 && v.top==80);
    assert(codex_browser_map_touch(240,400,480,800,600,800,&p)==1);
    assert(p.x==300 && p.y==400);
    assert(codex_browser_make_viewport(0,1448,600,800,&v)==-1);
    assert(codex_browser_map_touch(200,100,1072,1448,0,800,&p)==-1);
    assert(codex_browser_map_touch(500,500,1072,1448,600,800,0)==-1);
    puts("CODEX_BROWSER_TOUCH_VIEWPORT_MAPPING_PASS");
    return 0;
}
