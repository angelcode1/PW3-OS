/* Codex browser PW3 one-shot e-ink screenshot preview.
 * NOT a live browser backend. Default paths are read-only or RAM-only.
 * The only hardware-writing path requires a tty, an exact CLI confirmation
 * and a separate environment gate. It restores the previous framebuffer
 * after a bounded five-second preview. Do not run under stock firmware.
 *
 * EPDC ioctl ABI is pinned to the existing PW3 Home eink.h used by Codex.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define PW3_W 1072u
#define PW3_H 1448u
#define SCREEN_BYTES ((size_t)PW3_W * PW3_H)
#define MAX_FB_MAP (16u * 1024u * 1024u)
#define MXCFB_SEND_UPDATE_PW3 0x4048462eu
#define MXCFB_WAIT_FOR_UPDATE_COMPLETE_PW3 0xc008462fu
#define WF_GC16 2u
#define WF_DU 1u
#define TEMP_AMBIENT 0x1000
#define REFRESH_FULL 1u
#define PREVIEW_SECONDS 5

/* 72-byte ABI. Other Kindle EPDC layouts must not be substituted here. */
struct pw3_rect { uint32_t top, left, width, height; };
struct pw3_update {
    struct pw3_rect region;
    uint32_t waveform, mode, marker, hist_bw, hist_gray;
    int32_t temp;
    uint32_t flags;
    uint32_t alt[7];
};
_Static_assert(sizeof(struct pw3_update) == 72, "Wrong PW3 EPDC ABI");
static const char pgm_header[] = "P5\n1072 1448\n255\n";
static volatile sig_atomic_t stopped;

static void stop_handler(int signum) { (void)signum; stopped = 1; }

static int read_all(int fd, unsigned char *dst, size_t length) {
    while (length) {
        ssize_t got = read(fd, dst, length);
        if (got < 0 && errno == EINTR) continue;
        if (got <= 0) return -1;
        dst += (size_t)got;
        length -= (size_t)got;
    }
    return 0;
}

static int load_pgm(const char *path, unsigned char **out) {
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) { perror("open grayscale preview"); return -1; }
    struct stat st;
    const size_t hdr = sizeof(pgm_header) - 1u;
    if (fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) ||
        st.st_size != (off_t)(hdr + SCREEN_BYTES)) {
        fputs("Invalid PGM size or file type (must be 1072x1448 P5)\n", stderr);
        close(fd);
        return -1;
    }
    char header[sizeof(pgm_header)-1u];
    if (read_all(fd, (unsigned char *)header, hdr) || memcmp(header, pgm_header, hdr)) {
        fputs("Invalid P5 header, resolution or maxval\n", stderr);
        close(fd);
        return -1;
    }
    unsigned char *p = malloc(SCREEN_BYTES);
    if (!p) { close(fd); return -1; }
    int ok = read_all(fd, p, SCREEN_BYTES);
    close(fd);
    if (ok) { free(p); return -1; }
    *out = p;
    return 0;
}

static uint32_t pixel_checksum(const unsigned char *p) {
    uint32_t h = 2166136261u;
    for (size_t i = 0; i < SCREEN_BYTES; i++)
        h = (h ^ p[i]) * 16777619u;
    return h;
}

static void copy_rows(unsigned char *dst, size_t stride,
                      const unsigned char *src, size_t rowlen) {
    for (size_t y = 0; y < PW3_H; ++y)
        memcpy(dst + y * stride, src + y * rowlen, rowlen);
}
static void save_rows(unsigned char *dst, const unsigned char *src, size_t stride) {
    for (size_t y = 0; y < PW3_H; ++y)
        memcpy(dst + y * PW3_W, src + y * stride, PW3_W);
}

/*
 * On the physical PW3, FBIOGET_VSCREENINFO reports rotate=3
 * (FB_ROTATE_CCW) *while xres=1072 and yres=1448 are already portrait*.
 * KOReader's Kindle framebuffer backend treats this as canonical portrait.
 * The EPDC consumes visible rows in its own framebuffer orientation;
 * do NOT software-rotate the 1072x1448 PGM or set FBIOPUT_VSCREENINFO.
 *
 * Match the observed framebuffer ABI exactly; this is NOT a generic
 * rotation override for other Kindle models or arbitrary modes.
 */
static int pw3_supported_fb(const struct fb_var_screeninfo *v,
                            const struct fb_fix_screeninfo *f) {
    return v && f &&
        v->xres == PW3_W && v->yres == PW3_H &&
        v->bits_per_pixel == 8u && v->grayscale == 1u &&
        v->rotate == FB_ROTATE_CCW &&
        v->xoffset == 0u && v->yoffset == 0u &&
        v->xres_virtual >= PW3_W && v->yres_virtual >= PW3_H &&
        f->type == FB_TYPE_PACKED_PIXELS &&
        f->visual == FB_VISUAL_STATIC_PSEUDOCOLOR &&
        f->line_length >= PW3_W &&
        f->smem_len != 0u && f->smem_len <= MAX_FB_MAP &&
        (uint64_t)f->line_length * PW3_H <= f->smem_len;
}

/* For dry tests only: no device fd, mmap, ioctl or touchscreen input. */
static int selftest(void) {
    if (sizeof(struct pw3_update) != 72u ||
        MXCFB_SEND_UPDATE_PW3 != 0x4048462eu) return 1;
    size_t stride = PW3_W + 23u;
    unsigned char *mapped = malloc(stride * PW3_H);
    unsigned char *before = malloc(SCREEN_BYTES);
    unsigned char *after = malloc(SCREEN_BYTES);
    if (!mapped || !before || !after) {
        free(mapped); free(before); free(after); return 1;
    }
    memset(mapped, 0x55, stride * PW3_H);
    for (size_t i = 0; i < SCREEN_BYTES; i++) before[i] = (unsigned char)(i & 255u);
    copy_rows(mapped, stride, before, PW3_W);
    save_rows(after, mapped, stride);
    int ok = memcmp(before, after, SCREEN_BYTES) == 0;
    memset(mapped, 0xff, stride * PW3_H);
    copy_rows(mapped, stride, after, PW3_W);
    for (size_t y = 0; y < PW3_H; y++)
        for (size_t x = PW3_W; x < stride; x++)
            if (mapped[y * stride + x] != 0xff) ok = 0;
    free(mapped); free(before); free(after);
    struct fb_var_screeninfo v = {0};
    struct fb_fix_screeninfo f = {0};
    v.xres=PW3_W; v.yres=PW3_H;
    v.xres_virtual=1088; v.yres_virtual=6144;
    v.bits_per_pixel=8; v.grayscale=1;
    v.rotate=FB_ROTATE_CCW;
    f.type=FB_TYPE_PACKED_PIXELS;
    f.visual=FB_VISUAL_STATIC_PSEUDOCOLOR;
    f.line_length=1088; f.smem_len=6782976;
    if (!pw3_supported_fb(&v, &f)) ok=0;
    v.rotate=FB_ROTATE_UR;
    if (pw3_supported_fb(&v, &f)) ok=0;
    v.rotate=FB_ROTATE_CCW;
    v.yoffset=1448;
    if (pw3_supported_fb(&v, &f)) ok=0;
    v.yoffset=0;
    f.line_length=1071;
    if (pw3_supported_fb(&v, &f)) ok=0;
    f.line_length=1088;
    f.smem_len=1088*1447;
    if (pw3_supported_fb(&v, &f)) ok=0;
    if (ok) puts("CODEX_PW3_BROWSER_PANEL_PREVIEW_RAM_SELFTEST_PASS");
    return ok ? 0 : 1;
}

static int pw3_refresh(int fd, uint32_t marker) {
    struct pw3_update u;
    memset(&u, 0, sizeof(u));
    u.region = (struct pw3_rect){0, 0, PW3_W, PW3_H};
    u.waveform = WF_GC16;
    u.mode = REFRESH_FULL;
    u.marker = marker;
    u.hist_bw = WF_DU;
    u.hist_gray = WF_GC16;
    u.temp = TEMP_AMBIENT;
    if (ioctl(fd, MXCFB_SEND_UPDATE_PW3, &u) != 0) {
        perror("PW3 EPDC SEND_UPDATE"); return -1;
    }
    uint32_t wait_marker[2] = {marker, 0};
    if (ioctl(fd, MXCFB_WAIT_FOR_UPDATE_COMPLETE_PW3, wait_marker) != 0) {
        perror("PW3 EPDC WAIT_FOR_UPDATE_COMPLETE"); return -1;
    }
    return 0;
}

static int preview(const unsigned char *gray) {
    int fd = open("/dev/fb0", O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) { perror("PW3 fb0 open"); return 1; }
    struct stat st;
    struct fb_var_screeninfo v;
    struct fb_fix_screeninfo f;
    memset(&v, 0, sizeof(v));
    memset(&f, 0, sizeof(f));
    if (fstat(fd, &st) || !S_ISCHR(st.st_mode) ||
        ioctl(fd, FBIOGET_VSCREENINFO, &v) ||
        ioctl(fd, FBIOGET_FSCREENINFO, &f)) {
        fputs("PW3 framebuffer capability queries failed\n", stderr);
        close(fd); return 1;
    }
    if (!pw3_supported_fb(&v, &f)) {
        fputs("Unsupported PW3 framebuffer rotation/geometry/format; no write\n", stderr);
        close(fd); return 1;
    }
    unsigned char *mapped = mmap(NULL, f.smem_len, PROT_READ | PROT_WRITE,
                                 MAP_SHARED, fd, 0);
    if (mapped == MAP_FAILED) { perror("fb0 mmap"); close(fd); return 1; }
    unsigned char *snapshot = malloc(SCREEN_BYTES);
    if (!snapshot) { munmap(mapped, f.smem_len); close(fd); return 1; }
    save_rows(snapshot, mapped, f.line_length);
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = stop_handler;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGTERM, &sa, NULL);
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGHUP, &sa, NULL);
    /* If the preview refresh fails, still restore the original bytes. */
    copy_rows(mapped, f.line_length, gray, PW3_W);
    int shown = pw3_refresh(fd, 0xc0de0001u);
    if (shown == 0) {
        for (int i = 0; i < PREVIEW_SECONDS && !stopped; i++) {
            struct timespec one = {1, 0};
            while (nanosleep(&one, &one) && errno == EINTR && !stopped) { }
        }
    }
    copy_rows(mapped, f.line_length, snapshot, PW3_W);
    int restored = pw3_refresh(fd, 0xc0de0002u);
    free(snapshot);
    munmap(mapped, f.smem_len);
    close(fd);
    if (restored != 0) {
        fputs("WARNING: framebuffer bytes restored but refresh failed\n", stderr);
        return 1;
    }
    puts("CODEX_PW3_BROWSER_SCREEN_RESTORED");
    return shown == 0 ? 0 : 1;
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--selftest") == 0) return selftest();
    if (argc == 3 && strcmp(argv[1], "--inspect") == 0) {
        unsigned char *pgm = NULL;
        if (load_pgm(argv[2], &pgm)) return 1;
        printf("CODEX_PW3_PGM_VALID width=%u height=%u bytes=%zu fnv32=%08x\n",
               PW3_W, PW3_H, SCREEN_BYTES, pixel_checksum(pgm));
        free(pgm);
        return 0;
    }
    if (argc == 4 && strcmp(argv[1], "--display-once") == 0 &&
        strcmp(argv[3], "--confirm-pw3") == 0) {
        /* Interactively attended only: never automatically run from boot,
         * CI, Home or the default NetSurf launcher. */
        const char *gate = getenv("CODEX_BROWSER_PANEL_TRIAL");
        if (!gate || strcmp(gate, "EXPLICIT") != 0 || !isatty(STDIN_FILENO)) {
            fputs("Display preview needs interactive tty and explicit trial gate\n", stderr);
            return 78;
        }
        unsigned char *pgm = NULL;
        if (load_pgm(argv[2], &pgm)) return 1;
        int result = preview(pgm);
        free(pgm);
        return result;
    }
    fputs("Usage: codex-browser-panel-preview --selftest | --inspect image.pgm\n"
          "  --display-once image.pgm --confirm-pw3 (tty + trial env required)\n", stderr);
    return 64;
}
