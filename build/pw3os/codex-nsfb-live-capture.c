/* Codex NetSurf libnsfb RAM-canvas capture shim (test only).
 *
 * Interposes the public nsfb_update() API, then reads NetSurf's ACTUAL
 * libnsfb pixel buffer using the published nsfb_get_* functions.
 *
 * Never opens any framebuffer or input device. Strict /reports-only output.
 * Not a PW3 display driver; no ioctl and no per-frame on-device writes.
 *
 * Compile with the matching Alpine libnsfb-dev headers on ARMv7:
 *   cc -shared -fPIC -std=c11 -O2 -Wall -Wextra -Werror ... -ldl -lnsfb
 */
#define _POSIX_C_SOURCE 200809L
#define _GNU_SOURCE
#include <libnsfb.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define CODEX_CAPTURE_FILE "/reports/codex-live-nsfb.pgm"
#define CODEX_CAPTURE_ENABLE "CI_ONLY"
#define CODEX_MAX_W 1072
#define CODEX_MAX_H 1448
#define CODEX_LIMIT_FRAMES 180
#define CODEX_MIN_INTERVAL_NS 200000000L

static int active;
static unsigned captured;
static struct timespec previous;

typedef int (*nsfb_update_fn)(nsfb_t *, nsfb_bbox_t *);

static int secure_write(int fd, const void *src, size_t n) {
    const unsigned char *p=src;
    while (n) {
        ssize_t rv=write(fd,p,n);
        if (rv<0 && errno==EINTR) continue;
        if (rv<=0) return -1;
        p+=(size_t)rv;
        n-=(size_t)rv;
    }
    return 0;
}

static int screenshot(nsfb_t *nsfb) {
    int w=0,h=0,stride=0;
    enum nsfb_format_e fmt=NSFB_FMT_ANY;
    uint8_t *ptr=NULL;
    if (nsfb_get_geometry(nsfb,&w,&h,&fmt) ||
        nsfb_get_buffer(nsfb,&ptr,&stride) || !ptr ||
        w<100 || h<100 || w>CODEX_MAX_W || h>CODEX_MAX_H ||
        stride<w*4 || stride>CODEX_MAX_W*8)
        return -1;
    /* libnsfb 32bpp little-endian byte order, verified against its public
     * NSFB_FMT_[A/X][B/R]GR8888 formats. Reject all others.
     */
    int rgb=(fmt==NSFB_FMT_ABGR8888 || fmt==NSFB_FMT_XBGR8888);
    int bgr=(fmt==NSFB_FMT_ARGB8888 || fmt==NSFB_FMT_XRGB8888);
    if (!rgb && !bgr) return -1;

    const size_t len=(size_t)w*(size_t)h;
    uint8_t *gray=malloc(len);
    if (!gray) return -1;
    for (int y=0;y<h;y++) {
        const uint8_t *line=ptr+(size_t)y*(size_t)stride;
        for (int x=0;x<w;x++) {
            const uint8_t *p=line+4*(size_t)x;
            unsigned red=rgb?p[0]:p[2];
            unsigned blue=rgb?p[2]:p[0];
            gray[(size_t)y*(size_t)w+(size_t)x]=(uint8_t)(
                (2126u*red+7152u*p[1]+722u*blue+5000u)/10000u);
        }
    }

    /* Use a fixed destination inside the CI-only report mount. Never
     * follow user-supplied paths or symlinks; write atomically.
     */
    char temporary[]="/reports/.codex-nsfb-XXXXXX";
    int fd=mkstemp(temporary);
    if (fd<0) { free(gray); return -1; }
    char header[64];
    int n=snprintf(header,sizeof(header),"P5\n%d %d\n255\n",w,h);
    int ok=n>0 && (size_t)n<sizeof(header) &&
           secure_write(fd,header,(size_t)n)==0 &&
           secure_write(fd,gray,len)==0 &&
           fsync(fd)==0;
    int close_rc=close(fd);
    free(gray);
    if (!ok || close_rc!=0 || rename(temporary,CODEX_CAPTURE_FILE)!=0) {
        unlink(temporary);
        return -1;
    }
    ++captured;
    printf("CODEX_NSFB_ACTUAL_FRAME_CAPTURED frame=%u width=%d height=%d format=%d\n",
           captured,w,h,(int)fmt);
    fflush(stdout);
    return 0;
}

int nsfb_update(nsfb_t *nsfb, nsfb_bbox_t *box) {
    static nsfb_update_fn next;
    if (!next) {
        /* POSIX dlsym() addresses may be function pointers. memcpy avoids
         * nonportable function-pointer casts under strict C compilers.
         */
        void *addr=dlsym(RTLD_NEXT,"nsfb_update");
        if (addr) memcpy(&next,&addr,sizeof(next));
        if (!next) {
            fputs("CODEX_NSFB_REAL_UPDATE_NOT_FOUND\n",stderr);
            return -1;
        }
    }
    int rv=next(nsfb,box);
    if (rv!=0 || active || captured>=CODEX_LIMIT_FRAMES) return rv;
    const char *gate=getenv("CODEX_NSFB_CAPTURE_ENABLE");
    if (!gate || strcmp(gate,CODEX_CAPTURE_ENABLE)!=0) return rv;
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC,&now)!=0) return rv;
    if (captured) {
        long elapsed=(now.tv_sec-previous.tv_sec)*1000000000L +
                     (now.tv_nsec-previous.tv_nsec);
        if (elapsed>=0 && elapsed<CODEX_MIN_INTERVAL_NS) return rv;
    }
    active=1;
    if (screenshot(nsfb)==0) previous=now;
    active=0;
    return rv;
}
