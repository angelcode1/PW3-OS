/* PW3 -> SDL 1.2 NetSurf input bridge.
 * Opt-in, one-process LD_PRELOAD under the 30-second attended trial.
 * Reads only /dev/input/event1 (cyttsp4_mt); no EVIOCGRAB, writes,
 * injections into kernel, or persistent services. Uses SDL1.2's public
 * PollEvent/WaitEvent API because libnsfb's SDL backend consumes both.
 *
 * SDL1.2 mouse event field layout is stable and tested here. No SDL
 * development package required; symbols resolve from the real library.
 */
#define _GNU_SOURCE
#include "codex-browser-viewport.h"
#include "codex-browser-home-origin.h"
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define TOUCH_NODE "/dev/input/event1"
#define EXPECTED_NAME "cyttsp4_mt"
#define PW3_WIDTH 1072
#define PW3_HEIGHT 1448
#define NETSURF_WIDTH 600
#define NETSURF_HEIGHT 800
#define SDL_MOUSEMOTION 4u
#define SDL_MOUSEBUTTONDOWN 5u
#define SDL_MOUSEBUTTONUP 6u
#define SDL_BUTTON_LEFT 1u
#define SDL_BUTTON_WHEELUP 4u
#define SDL_BUTTON_WHEELDOWN 5u
#define SDL_PRESSED 1u
#define SDL_RELEASED 0u

typedef struct {
    uint8_t type, which, state, padding;
    uint16_t x, y;
    int16_t xrel, yrel;
} sdl_motion;
typedef struct {
    uint8_t type, which, button, state;
    uint16_t x, y;
} sdl_button;
_Static_assert(sizeof(sdl_motion)==12, "SDL1.2 motion ABI differs");
_Static_assert(sizeof(sdl_button)==8, "SDL1.2 button ABI differs");

typedef struct {
    uint8_t content[12];
    unsigned size;
} pending_event;
#define EVENT_CAP 64
static pending_event queue[EVENT_CAP];
static unsigned front, back;
static int fd=-2; /* -2=not attempted, -1=unavailable */
static int slot;
static int raw_x,raw_y,ax_min,ay_min;
static int started,ended,moved,active,dragged,starting_y,last_wheel_y;
static int (*real_poll)(void *);
static int (*real_wait)(void *);
static int first_log;

static int active_gate(void) {
    const char *g=getenv("CODEX_SDL_INPUT_ENABLE");
    if (!g) return 0;
    /* Retain the already proven attended SSH trial unchanged. */
    if (strcmp(g,"PW3_ATTENDED")==0) return isatty(STDIN_FILENO);
    /* Home-launched apps are deliberately headless. Check their actual
     * /proc process ancestry, not only a spoofable environment variable. */
    if (strcmp(g,"PW3_HOME_PREVIEW")==0) return codex_browser_from_home();
    return 0;
}
static void queue_bytes(const void *event, unsigned len) {
    unsigned nxt=(back+1u)%EVENT_CAP;
    if (nxt==front || len>sizeof(queue[0].content)) return;
    memset(&queue[back],0,sizeof(queue[back]));
    memcpy(queue[back].content,event,len);
    queue[back].size=len;
    back=nxt;
}
static int pop_event(void *event) {
    if (!event || front==back) return 0;
    /* SDL1.2 event has a union of larger size; we write only the fields
     * that libnsfb reads for the chosen event type. No out-of-bounds writes. */
    memcpy(event,queue[front].content,queue[front].size);
    front=(front+1u)%EVENT_CAP;
    return 1;
}
static void enqueue_motion(int x,int y) {
    sdl_motion e={0};
    e.type=SDL_MOUSEMOTION;
    e.x=(uint16_t)x;
    e.y=(uint16_t)y;
    queue_bytes(&e,sizeof(e));
}
static void enqueue_button(int x,int y,unsigned button,int pressed) {
    sdl_button e={0};
    e.type=pressed?SDL_MOUSEBUTTONDOWN:SDL_MOUSEBUTTONUP;
    e.button=(uint8_t)button;
    e.state=(uint8_t)(pressed?SDL_PRESSED:SDL_RELEASED);
    e.x=(uint16_t)x;
    e.y=(uint16_t)y;
    queue_bytes(&e,sizeof(e));
}
static int coords(codex_browser_point *p) {
    return codex_browser_map_touch(raw_x-ax_min,raw_y-ay_min,
                                   PW3_WIDTH,PW3_HEIGHT,
                                   NETSURF_WIDTH,NETSURF_HEIGHT,p)==1;
}
static void reset_gesture(void) {
    started=ended=moved=active=dragged=0;
    last_wheel_y=0;
}
static void handle_event(const struct input_event *ev) {
    if (ev->type==EV_SYN && ev->code==SYN_DROPPED) {
        reset_gesture();
        return;
    }
    if (ev->type==EV_ABS) {
        if (ev->code==ABS_MT_SLOT) { slot=ev->value; return; }
        if (slot!=0) return;
        if (ev->code==ABS_MT_POSITION_X) { raw_x=ev->value; moved=1; }
        if (ev->code==ABS_MT_POSITION_Y) { raw_y=ev->value; moved=1; }
        if (ev->code==ABS_MT_TRACKING_ID) {
            if (ev->value>=0) { started=1;ended=0; }
            else { ended=1;started=0; }
        }
    }
    if (ev->type!=EV_SYN || ev->code!=SYN_REPORT) return;
    codex_browser_point p;
    int inside=coords(&p);
    if (started && inside) {
        active=1;
        dragged=0;
        starting_y=raw_y;
        last_wheel_y=raw_y;
        enqueue_motion(p.x,p.y);
        printf("CODEX_BROWSER_SDL_TOUCH_DOWN x=%d y=%d\n",p.x,p.y);
    } else if (ended && active) {
        if (!dragged && inside) {
            enqueue_motion(p.x,p.y);
            enqueue_button(p.x,p.y,SDL_BUTTON_LEFT,1);
            enqueue_button(p.x,p.y,SDL_BUTTON_LEFT,0);
            printf("CODEX_BROWSER_SDL_TAP x=%d y=%d\n",p.x,p.y);
        } else {
            printf("CODEX_BROWSER_SDL_SWIPE_END\n");
        }
        active=0;
    } else if (moved && active && inside) {
        int delta=raw_y-last_wheel_y;
        int travel=raw_y-starting_y;
        if (travel>30 || travel< -30) dragged=1;
        if (dragged && (delta>=65 || delta<=-65)) {
            unsigned button=delta>0?SDL_BUTTON_WHEELUP:SDL_BUTTON_WHEELDOWN;
            enqueue_motion(p.x,p.y);
            enqueue_button(p.x,p.y,button,1);
            enqueue_button(p.x,p.y,button,0);
            last_wheel_y=raw_y;
            printf("CODEX_BROWSER_SDL_SCROLL button=%u x=%d y=%d\n",
                   button,p.x,p.y);
        }
    }
    started=ended=moved=0;
    fflush(stdout);
}
/* EVIOCGNAME returns a positive length when a name was copied.
 * A previous version tested !=0 and rejected successful PW3 devices.
 * Other ioctl calls can also return nonnegative success values. */
static int evdev_ioctl_failed(int rc) { return rc < 0; }
static void touch_open_failure(const char *reason, int code) {
    fprintf(stderr, "CODEX_BROWSER_SDL_TOUCH_UNAVAILABLE reason=%s errno=%d\n",
            reason, code);
    fflush(stderr);
    if (fd>=0) close(fd);
    fd=-1;  /* fail closed for this attended session */
}
static void open_touch(void) {
    if (fd!=-2 || !active_gate()) return;
    fd=open(TOUCH_NODE,O_RDONLY|O_CLOEXEC|O_NONBLOCK|O_NOFOLLOW);
    if (fd<0) {
        touch_open_failure("OPEN",errno);
        return;
    }
    struct stat st;
    struct input_absinfo ax={0},ay={0};
    char name[64]={0};
    if (fstat(fd,&st)<0 || !S_ISCHR(st.st_mode)) {
        touch_open_failure("NOT_CHAR_DEVICE",errno);return;
    }
    errno=0;
    int name_rc=ioctl(fd,EVIOCGNAME(sizeof(name)),name);
    if (evdev_ioctl_failed(name_rc) || name_rc==0 || !name[0]) {
        touch_open_failure("NAME_IOCTL",errno);return;
    }
    if (strcmp(name,EXPECTED_NAME)!=0) {
        touch_open_failure("UNEXPECTED_DEVICE_NAME",0);return;
    }
    if (evdev_ioctl_failed(ioctl(fd,EVIOCGABS(ABS_MT_POSITION_X),&ax)) ||
        evdev_ioctl_failed(ioctl(fd,EVIOCGABS(ABS_MT_POSITION_Y),&ay))) {
        touch_open_failure("ABS_IOCTL",errno);return;
    }
    if (ax.minimum!=0 || ax.maximum!=PW3_WIDTH-1 ||
        ay.minimum!=0 || ay.maximum!=PW3_HEIGHT-1) {
        touch_open_failure("UNEXPECTED_AXIS_RANGE",0);return;
    }
    ax_min=ax.minimum; ay_min=ay.minimum;
    printf("CODEX_BROWSER_SDL_TOUCH_CONNECTED %s name=%s name_rc=%d\n",
           TOUCH_NODE,name,name_rc);
    fflush(stdout);
}
static void pump_touch(void) {
    open_touch();
    if (fd<0) return;
    struct input_event buf[64];
    for (int loops=0;loops<4;loops++) {
        ssize_t n=read(fd,buf,sizeof(buf));
        if (n<=0) break;
        if (n%(ssize_t)sizeof(buf[0])) { reset_gesture();break; }
        for (size_t i=0;i<(size_t)n/sizeof(buf[0]);i++)
            handle_event(&buf[i]);
    }
}

int SDL_PollEvent(void *event) {
    if (!real_poll) {
        void *ptr=dlsym(RTLD_NEXT,"SDL_PollEvent");
        if (!ptr) return 0;
        memcpy(&real_poll,&ptr,sizeof(real_poll));
    }
    /* Preserve NetSurf's SDL events (including its timer wake events). */
    int result=real_poll(event);
    if (result || !active_gate() || !event) return result;
    if (!first_log++) {
        puts("CODEX_BROWSER_SDL_POLL_HOOK_ACTIVE");
        fflush(stdout);
    }
    if (pop_event(event)) return 1;
    pump_touch();
    return pop_event(event);
}

int SDL_WaitEvent(void *event) {
    if (!real_wait) {
        void *ptr=dlsym(RTLD_NEXT,"SDL_WaitEvent");
        if (!ptr) return 0;
        memcpy(&real_wait,&ptr,sizeof(real_wait));
    }
    if (!active_gate()) return real_wait(event);
    /* NetSurf uses SDL_WaitEvent for its timed sleeps; poll it at 40 Hz
     * so the evdev input can be serviced without an SDL worker thread. */
    for (;;) {
        int n=SDL_PollEvent(event);
        if (n) return n;
        struct timespec pause={0,25000000};
        nanosleep(&pause,NULL);
    }
}
