/* Codex real NetSurf SDL framebuffer capture, ARMv7 test only.
 * Alpine 3.24 netsurf-framebuffer has its libnsfb built into the binary,
 * so a separate libnsfb-dev package and nsfb_update interposition cannot
 * be used. Its SDL surface DOES call the public SDL_UpdateRect symbol.
 *
 * Capture the SDL_Surface supplied by the browser itself, before any X11
 * screenshot. All exports are resolved at runtime; no SDL development
 * headers, libnsfb or modified NetSurf binaries are needed.
 *
 * No /dev/fb0, EPDC ioctl, evdev, URL fetching, or input injection.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define OUTPUT "/reports/codex-live-sdl.bmp"
#define ENABLE "CI_ONLY"
#define MAX_FRAMES 100u
#define MIN_NS 220000000L

typedef void (*update_fn)(void *, int32_t, int32_t, uint32_t, uint32_t);
typedef void *(*rwfile_fn)(const char *, const char *);
typedef int (*save_fn)(void *, void *, int);
static update_fn next_update;
static rwfile_fn rw_file;
static save_fn save_bmp;
static unsigned captured;
static int active;
static struct timespec last;

static void *symbol(const char *name) {
    return dlsym(RTLD_NEXT,name);
}
static int resolve(void) {
    if (!next_update) {
        void *p=symbol("SDL_UpdateRect");
        if (!p) return -1;
        memcpy(&next_update,&p,sizeof(next_update));
    }
    if (!rw_file) {
        void *p=symbol("SDL_RWFromFile");
        if (!p) return -1;
        memcpy(&rw_file,&p,sizeof(rw_file));
    }
    if (!save_bmp) {
        void *p=symbol("SDL_SaveBMP_RW");
        if (!p) return -1;
        memcpy(&save_bmp,&p,sizeof(save_bmp));
    }
    return 0;
}
static int capture(void *surface) {
    /* /reports is the CI bind mount; no caller-controllable path is used. */
    char temp[]="/reports/.codex-live-sdl-XXXXXX";
    int fd=mkstemp(temp);
    if (fd<0) return -1;
    close(fd);
    void *rw=rw_file(temp,"wb");
    if (!rw) { unlink(temp); return -1; }
    /* freedst=1 delegates RWops close to SDL. */
    int ok=save_bmp(surface,rw,1);
    if (ok || rename(temp,OUTPUT)) {
        unlink(temp);
        return -1;
    }
    ++captured;
    printf("CODEX_NETSURF_DIRECT_SDL_FRAME frame=%u\n",captured);
    fflush(stdout);
    return 0;
}

/* Exact SDL 1.2 public ABI; argument types chosen to match SDL12-compat. */
void SDL_UpdateRect(void *surface, int32_t x, int32_t y,
                    uint32_t w, uint32_t h) {
    if (resolve()) return; /* no valid real driver, never invent display */
    next_update(surface,x,y,w,h);
    if (active || !surface || captured>=MAX_FRAMES) return;
    const char *gate=getenv("CODEX_SDL_CAPTURE_ENABLE");
    if (!gate || strcmp(gate,ENABLE)) return;
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC,&now)) return;
    if (captured) {
        long delta=(now.tv_sec-last.tv_sec)*1000000000L+
                   now.tv_nsec-last.tv_nsec;
        if (delta>=0 && delta<MIN_NS) return;
    }
    active=1;
    if (!capture(surface)) last=now;
    active=0;
}
