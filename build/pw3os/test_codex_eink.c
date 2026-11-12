#include "codex-eink-compositor.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

int main(void) {
    unsigned char pixel[8]={255,0,0,255,0,255,0,255};
    unsigned char gray[2]={0,0};
    assert(codex_rgba_to_gray(pixel,8,gray,2,1)==0);
    assert(gray[0]==54 && gray[1]==182);
    assert(codex_rgba_to_gray(NULL,8,gray,2,1)<0);
    assert(codex_rgba_to_gray(pixel,7,gray,2,1)<0);

    enum { W=1072, H=1448, N=W*H };
    unsigned char *old=malloc(N), *next=malloc(N);
    codex_plan *p=malloc(sizeof *p);
    assert(old && next && p);
    memset(old,255,N); memset(next,255,N);
    assert(codex_eink_plan(old,next,W,H,0,p)==0);
    assert(p->kind==CODEX_UPDATE_NONE && p->rect_count==0);

    next[0]=0;
    assert(codex_eink_plan(old,next,W,H,0,p)==0);
    assert(p->kind==CODEX_UPDATE_PARTIAL && p->rect_count==1);
    assert(p->rects[0].x==0 && p->rects[0].y==0);
    assert(p->rects[0].w==64 && p->rects[0].h==64);

    memset(next,255,N); next[N-1]=0;
    assert(codex_eink_plan(old,next,W,H,0,p)==0);
    assert(p->kind==CODEX_UPDATE_PARTIAL && p->rect_count==1);
    assert(p->rects[0].x==1024 && p->rects[0].y==1408);
    assert(p->rects[0].w==48 && p->rects[0].h==40);

    assert(codex_eink_plan(old,next,W,H,CODEX_PARTIAL_LIMIT,p)==0);
    assert(p->kind==CODEX_UPDATE_FULL && p->rect_count==0);

    memset(next,0,N);
    assert(codex_eink_plan(old,next,W,H,0,p)==0);
    assert(p->kind==CODEX_UPDATE_FULL && p->rect_count==0);
    assert(codex_eink_plan(NULL,next,W,H,0,p)<0);
    free(p); free(old); free(next);
    puts("CODEX_EINK_OFFSCREEN_COMPOSITOR_PASS");
    return 0;
}
