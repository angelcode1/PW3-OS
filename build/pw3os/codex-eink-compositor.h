/* Codex e-ink offscreen compositor (no Kindle device access).
 * Pure buffer operations; caller owns both frames and any EPDC integration.
 * Input pixels are explicitly RGBA byte order, NOT a libnsfb ABI assertion.
 */
#ifndef CODEX_EINK_COMPOSITOR_H
#define CODEX_EINK_COMPOSITOR_H
#include <stddef.h>
#include <stdint.h>

#define CODEX_TILE 64
#define CODEX_MAX_RECTS 512
#define CODEX_PARTIAL_LIMIT 12

typedef struct { unsigned x, y, w, h; } codex_rect;
typedef enum { CODEX_UPDATE_NONE=0, CODEX_UPDATE_PARTIAL=1, CODEX_UPDATE_FULL=2 } codex_update;
typedef struct {
    codex_update kind;
    unsigned dirty_tiles;
    unsigned rect_count;
    codex_rect rects[CODEX_MAX_RECTS];
} codex_plan;

/* Converts 4-byte/pixel RGBA into 8-bit luma. Ignores alpha (opaque output). */
int codex_rgba_to_gray(const uint8_t *src, size_t src_stride,
                       uint8_t *gray, unsigned w, unsigned h);
/* Computes changed 64x64 tiles. A frame is never submitted to EPDC here. */
int codex_eink_plan(const uint8_t *old_gray, const uint8_t *new_gray,
                    unsigned w, unsigned h, unsigned partials, codex_plan *out);
#endif
