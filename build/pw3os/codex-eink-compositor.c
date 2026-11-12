#include "codex-eink-compositor.h"
#include <string.h>
#include <stdint.h>

#define MAX_PIXELS (1072u * 1448u)
static unsigned min_u(unsigned a, unsigned b) { return a < b ? a : b; }

int codex_nsfb32_to_gray(const uint8_t *src, size_t stride,
                         uint8_t *gray, unsigned w, unsigned h,
                         codex_pixfmt format)
{
    if (!src || !gray || !w || !h || (uint64_t)w*h > MAX_PIXELS ||
        (uint64_t)w*4u > (uint64_t)SIZE_MAX || stride < (size_t)w*4u ||
        (format != CODEX_FMT_ABGR8888_LE && format != CODEX_FMT_ARGB8888_LE))
        return -1;
    for (unsigned y=0; y<h; y++) {
        for (unsigned x=0; x<w; x++) {
            const uint8_t *p=src + (size_t)y*stride + (size_t)x*4u;
            uint32_t red=(format == CODEX_FMT_ABGR8888_LE) ? p[0] : p[2];
            uint32_t green=p[1];
            uint32_t blue=(format == CODEX_FMT_ABGR8888_LE) ? p[2] : p[0];
            /* Encoded RGB luma approximation, not linear-light gamma correction. */
            gray[(size_t)y*w+x]=(uint8_t)((2126u*red+7152u*green+
                                           722u*blue+5000u)/10000u);
        }
    }
    return 0;
}

int codex_rgba_to_gray(const uint8_t *src, size_t stride,
                       uint8_t *gray, unsigned w, unsigned h)
{
    return codex_nsfb32_to_gray(src,stride,gray,w,h,CODEX_FMT_ABGR8888_LE);
}

int codex_eink_plan(const uint8_t *old_gray, const uint8_t *new_gray,
                    unsigned w, unsigned h, unsigned partials, codex_plan *out)
{
    if (!old_gray || !new_gray || !out || !w || !h ||
        (uint64_t)w * h > MAX_PIXELS) return -1;
    memset(out, 0, sizeof(*out));
    unsigned nx = (w + CODEX_TILE - 1) / CODEX_TILE;
    unsigned ny = (h + CODEX_TILE - 1) / CODEX_TILE;
    for (unsigned ty = 0; ty < ny; ty++) {
        unsigned y0 = ty * CODEX_TILE, yh = min_u(CODEX_TILE, h - y0);
        for (unsigned tx = 0; tx < nx; ) {
            unsigned start = tx, run = 0;
            for (; tx < nx; tx++) {
                unsigned x0=tx * CODEX_TILE, xw=min_u(CODEX_TILE, w-x0);
                int dirty=0;
                for (unsigned y=y0; y<y0+yh && !dirty; y++)
                    for (unsigned x=x0; x<x0+xw; x++)
                        if (old_gray[(size_t)y*w+x] != new_gray[(size_t)y*w+x]) {
                            dirty=1; break;
                        }
                if (!dirty && run) break;
                if (dirty) { run++; out->dirty_tiles++; }
                else start=tx+1;
            }
            if (run) {
                if (out->rect_count == CODEX_MAX_RECTS) {
                    out->kind=CODEX_UPDATE_FULL;
                    out->rect_count=0;
                    return 0;
                }
                codex_rect *r=&out->rects[out->rect_count++];
                r->x=start*CODEX_TILE; r->y=y0;
                r->w=min_u(run*CODEX_TILE, w-r->x); r->h=yh;
            }
            if (!run && tx==nx) break;
        }
    }
    if (!out->dirty_tiles) out->kind=CODEX_UPDATE_NONE;
    else if (partials >= CODEX_PARTIAL_LIMIT ||
             (uint64_t)out->dirty_tiles*100 >= (uint64_t)nx*ny*45) {
        out->kind=CODEX_UPDATE_FULL;
        out->rect_count=0;
    } else out->kind=CODEX_UPDATE_PARTIAL;
    return 0;
}
