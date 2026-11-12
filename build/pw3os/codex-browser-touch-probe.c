/* Codex PW3 touchscreen discovery for future NetSurf input integration.
 * Read-only ioctl capability probe and optional bounded read-only sampling.
 * No EVIOCGRAB, sysfs writes, framebuffer writes or device reconfiguration.
 */
#define _GNU_SOURCE
#include "codex-touch-bridge.h"
#include <errno.h>
#include <fcntl.h>
#include <linux/input.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define PANEL_W 1072
#define PANEL_H 1448
#define MAX_EVENTS 16
static volatile sig_atomic_t stop_flag;
static void stop_now(int sig) { (void)sig; stop_flag=1; }

typedef struct {
    int fd, ax_min, ax_max, ay_min, ay_max, slot;
    int rx, ry, moved, pending_down, pending_up, dropped;
    unsigned transitions;
    codex_touch_state state;
    codex_touch_transform transform;
} device;

static int emit_phase(device *dev, codex_touch_phase phase) {
    codex_pointer_event events[2];
    int n=codex_touch_translate(&dev->state, &dev->transform,
                                 phase, dev->rx-dev->ax_min, dev->ry-dev->ay_min,
                                 events);
    if (n < 0) return -1;
    for (int i=0;i<n;i++) {
        const char *p=events[i].type == CODEX_PTR_MOVE ? "MOVE" :
                      events[i].type == CODEX_PTR_DOWN ? "DOWN" : "UP";
        printf("CODEX_TOUCH_%s x=%d y=%d\n",p,events[i].x,events[i].y);
        if (events[i].type != CODEX_PTR_MOVE) dev->transitions++;
    }
    fflush(stdout);
    return n;
}

static int process(device *d, const struct input_event *event) {
    if (event->type == EV_SYN && event->code == SYN_DROPPED) {
        /* Kernel overrun: discard gesture, never invent pointer coordinates. */
        emit_phase(d,CODEX_TOUCH_CANCEL);
        d->pending_down=d->pending_up=d->moved=0;
        d->dropped=1;
        return 0;
    }
    if (d->dropped) {
        if (event->type == EV_SYN && event->code == SYN_REPORT)
            d->dropped=0;
        return 0;
    }
    if (event->type == EV_ABS) {
        if (event->code == ABS_MT_SLOT) { d->slot=event->value; return 0; }
        if (d->slot != 0) return 0;  /* Ignore additional fingers. */
        if (event->code == ABS_MT_POSITION_X) {
            d->rx=event->value;d->moved=1;
        } else if (event->code == ABS_MT_POSITION_Y) {
            d->ry=event->value;d->moved=1;
        } else if (event->code == ABS_MT_TRACKING_ID) {
            if (event->value >= 0) {
                d->pending_down=1;d->pending_up=0;
            } else {
                d->pending_up=1;d->pending_down=0;
            }
        }
        return 0;
    }
    if (event->type == EV_SYN && event->code == SYN_REPORT) {
        if (d->pending_up) {
            emit_phase(d,CODEX_TOUCH_UP);
        } else if (d->pending_down) {
            emit_phase(d,CODEX_TOUCH_DOWN);
        } else if (d->moved && d->state.active) {
            emit_phase(d,CODEX_TOUCH_MOVE);
        }
        d->pending_down=d->pending_up=d->moved=0;
    }
    return 0;
}

static int selftest(void) {
    device d={0};
    d.ax_min=10;d.ax_max=109;d.ay_min=20;d.ay_max=219;
    d.rx=10;d.ry=20;
    d.transform=(codex_touch_transform){100,200,PANEL_W,PANEL_H,0,0,0};
    const struct input_event sequence[]={
        {.type=EV_ABS,.code=ABS_MT_TRACKING_ID,.value=7},
        {.type=EV_ABS,.code=ABS_MT_POSITION_X,.value=10},
        {.type=EV_ABS,.code=ABS_MT_POSITION_Y,.value=20},
        {.type=EV_SYN,.code=SYN_REPORT},
        {.type=EV_ABS,.code=ABS_MT_POSITION_X,.value=109},
        {.type=EV_ABS,.code=ABS_MT_POSITION_Y,.value=219},
        {.type=EV_SYN,.code=SYN_REPORT},
        {.type=EV_ABS,.code=ABS_MT_TRACKING_ID,.value=-1},
        {.type=EV_SYN,.code=SYN_REPORT}
    };
    for (size_t i=0;i<sizeof(sequence)/sizeof(sequence[0]);i++)
        process(&d,&sequence[i]);
    int ok = d.transitions==2 && !d.state.active;
    if (ok) puts("CODEX_PW3_TOUCH_PROBE_SYNTHETIC_PASS");
    return ok ? 0 : 1;
}

static int find_touch(device *dev) {
    for (int i=0;i<MAX_EVENTS;i++) {
        char path[64], name[128]={0};
        snprintf(path,sizeof(path),"/dev/input/event%d",i);
        int fd=open(path,O_RDONLY|O_CLOEXEC|O_NONBLOCK|O_NOFOLLOW);
        if (fd<0) continue;
        struct stat st;
        struct input_absinfo ax={0},ay={0},tracking={0};
        if (fstat(fd,&st) || !S_ISCHR(st.st_mode) ||
            ioctl(fd,EVIOCGABS(ABS_MT_POSITION_X),&ax) ||
            ioctl(fd,EVIOCGABS(ABS_MT_POSITION_Y),&ay) ||
            ioctl(fd,EVIOCGABS(ABS_MT_TRACKING_ID),&tracking) ||
            ax.maximum<=ax.minimum || ay.maximum<=ay.minimum) {
            close(fd); continue;
        }
        ioctl(fd,EVIOCGNAME(sizeof(name)),name);
        memset(dev,0,sizeof(*dev));
        dev->fd=fd;dev->ax_min=ax.minimum;dev->ax_max=ax.maximum;
        dev->ay_min=ay.minimum;dev->ay_max=ay.maximum;
        dev->rx=ax.minimum;dev->ry=ay.minimum;
        dev->transform=(codex_touch_transform){
            ax.maximum-ax.minimum+1,ay.maximum-ay.minimum+1,
            PANEL_W,PANEL_H,0,0,0};
        printf("CODEX_PW3_TOUCH_READ_ONLY device=%s name=%s\n",
               path,name[0]?name:"unknown");
        printf("abs_x_min=%d max=%d abs_y_min=%d max=%d "
               "tracking_min=%d tracking_max=%d\n",
               ax.minimum,ax.maximum,ay.minimum,ay.maximum,
               tracking.minimum,tracking.maximum);
        fflush(stdout);
        return 0;
    }
    fputs("No compatible ABS_MT touch device found in event0..15\n",stderr);
    return 1;
}

static int sample(device *d,int seconds) {
    struct sigaction sa={0};sa.sa_handler=stop_now;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT,&sa,NULL);
    sigaction(SIGTERM,&sa,NULL);
    struct timespec start,now;
    if (clock_gettime(CLOCK_MONOTONIC,&start)) return 1;
    while (!stop_flag) {
        if (clock_gettime(CLOCK_MONOTONIC,&now)) break;
        if (now.tv_sec-start.tv_sec >= seconds) break;
        struct pollfd p={d->fd,POLLIN,0};
        int rc=poll(&p,1,400);
        if (rc<0 && errno==EINTR) continue;
        if (rc<0) return 1;
        if (rc==0) continue;
        struct input_event events[32];
        ssize_t n=read(d->fd,events,sizeof(events));
        if (n<0 && (errno==EINTR || errno==EAGAIN)) continue;
        if (n<0) return 1;
        if (n % (ssize_t)sizeof(events[0]) != 0) return 1;
        for (size_t i=0;i<(size_t)n/sizeof(events[0]);i++)
            if (process(d,&events[i])) return 1;
    }
    if (d->state.active) emit_phase(d,CODEX_TOUCH_CANCEL);
    printf("CODEX_PW3_TOUCH_SAMPLE_END transitions=%u\n",d->transitions);
    return d->transitions >= 2 ? 0 : 4;
}

int main(int argc,char **argv) {
    if (argc==2 && strcmp(argv[1],"--selftest")==0) return selftest();
    int do_probe=argc==2 && strcmp(argv[1],"--read-only")==0;
    int do_sample=argc==3 && strcmp(argv[1],"--sample-seconds")==0 &&
                  strcmp(argv[2],"8")==0;
    if (!do_probe && !do_sample) {
        fputs("Usage: codex-browser-touch-probe --selftest | --read-only | "
              "--sample-seconds 8\n",stderr);
        return 64;
    }
    if (do_sample) {
        const char *gate=getenv("CODEX_BROWSER_TOUCH_TRIAL");
        if (!gate || strcmp(gate,"EXPLICIT") || !isatty(STDIN_FILENO)) {
            fputs("Touch sample requires interactive tty and explicit gate\n",stderr);
            return 78;
        }
    }
    device d;
    if (find_touch(&d)) return 1;
    int rc=do_probe ? 0 : sample(&d,8);
    close(d.fd);
    return rc;
}
