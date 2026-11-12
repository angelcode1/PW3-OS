/* Host unit test: exercise actual SDL1.2 event layout and evdev parser.
 * Does not open /dev/input, use SDL, or access a framebuffer.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include "codex-sdl-touch-input.c"

static void feed(int type,int code,int value) {
    struct input_event ev={0};
    ev.type=(unsigned short)type;
    ev.code=(unsigned short)code;
    ev.value=value;
    handle_event(&ev);
}
int main(void) {
    /* Linux EVIOCGNAME success returns bytes copied (positive), not 0.
     * This exact ABI mistake prevented touch attachment on physical PW3. */
    assert(evdev_ioctl_failed(-1));
    assert(!evdev_ioctl_failed(0));
    assert(!evdev_ioctl_failed(10));
    ax_min=ay_min=0;
    feed(EV_ABS,ABS_MT_TRACKING_ID,2);
    feed(EV_ABS,ABS_MT_POSITION_X,234);
    feed(EV_ABS,ABS_MT_POSITION_Y,729);
    feed(EV_SYN,SYN_REPORT,0);
    feed(EV_ABS,ABS_MT_TRACKING_ID,-1);
    feed(EV_SYN,SYN_REPORT,0);
    assert((back+EVENT_CAP-front)%EVENT_CAP==4);
    unsigned char data[12]={0};
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEMOTION);
    uint16_t x=0,y=0;
    memcpy(&x,data+4,2);memcpy(&y,data+6,2);
    assert(x==130 && y==403);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEMOTION);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEBUTTONDOWN && data[2]==SDL_BUTTON_LEFT);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEBUTTONUP && data[2]==SDL_BUTTON_LEFT);
    assert(pop_event(data)==0);
    feed(EV_ABS,ABS_MT_TRACKING_ID,3);
    feed(EV_ABS,ABS_MT_POSITION_X,500);
    feed(EV_ABS,ABS_MT_POSITION_Y,1000);
    feed(EV_SYN,SYN_REPORT,0);
    feed(EV_ABS,ABS_MT_POSITION_Y,920);
    feed(EV_SYN,SYN_REPORT,0);
    feed(EV_ABS,ABS_MT_TRACKING_ID,-1);
    feed(EV_SYN,SYN_REPORT,0);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEMOTION);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEMOTION);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEBUTTONDOWN && data[2]==SDL_BUTTON_WHEELDOWN);
    assert(pop_event(data)==1 && data[0]==SDL_MOUSEBUTTONUP && data[2]==SDL_BUTTON_WHEELDOWN);
    assert(pop_event(data)==0); /* swipe must not become a click */
    reset_gesture();
    assert(active==0);
    puts("CODEX_BROWSER_SDL_TOUCH_BRIDGE_TEST_PASS");
    return 0;
}
