/* Experimental PW3 fast e-ink browser presenter, not a boot service.
 * Runs only as an actual descendant of Codex Home, with an exact opt-in
 * environment gate and CLI argument. The existing GC16-only presenter
 * remains unchanged. Bounded 30 seconds, RAM-only input, guaranteed best-
 * effort GC16 restoration on normal exit and catchable signals.
 *
 * Hardware ABI copied from the already tested PW3 GC16 presenter:
 * 1072x1448 8-bit grayscale, Amazon kernel 3.0.35, 72-byte update struct.
 * All browser updates use grayscale-capable GC16: the DU waveform tested
 * on the PW3 made large regions of the actual grayscale page appear blank.
 * Partial GC16 is used only for small dirty regions, full GC16 for large
 * changes and periodic resynchronisation. No boot-time changes.
 */
#define _GNU_SOURCE
#include "codex-browser-home-origin.h"
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#define PW 1072u
#define PH 1448u
#define PIXELS ((size_t)PW*PH)
#define MAX_FB_MAP (16u*1024u*1024u)
#define MXCFB_SEND_UPDATE_PW3 0x4048462eu
#define MXCFB_WAIT_FOR_UPDATE_COMPLETE_PW3 0xc008462fu
#define WF_GC16 2u
#define WF_DU 1u
#define UPDATE_PARTIAL 0u
#define UPDATE_FULL 1u
#define TEMP_AMBIENT 0x1000
#define SESSION_MS 30000
#define MIN_UPDATE_MS 600
#define MAX_PARTIAL_BURST 6
#define FULL_AREA_PERCENT 45u
#define HDR "P5\n1072 1448\n255\n"

struct pw3_rect { uint32_t top,left,width,height; };
struct pw3_update {
    struct pw3_rect region;
    uint32_t waveform,mode,marker,hist_bw,hist_gray;
    int32_t temp;
    uint32_t flags;
    uint32_t alt[7];
};
_Static_assert(sizeof(struct pw3_update)==72,"Unsupported PW3 EPDC ABI");
static volatile sig_atomic_t stop_requested;
static void request_stop(int unused) { (void)unused; stop_requested=1; }

static int64_t millis(void) {
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)) return -1;
    return (int64_t)t.tv_sec*1000 + t.tv_nsec/1000000;
}
static void pause_ms(long ms) {
    struct timespec ts={ms/1000,(ms%1000)*1000000L};
    while(nanosleep(&ts,&ts)<0 && errno==EINTR && !stop_requested){}
}
static int read_exact(int fd,unsigned char *p,size_t n) {
    while(n) {
        ssize_t got=read(fd,p,n);
        if(got<0 && errno==EINTR)continue;
        if(got<=0)return -1;
        p+=(size_t)got;n-=(size_t)got;
    }
    return 0;
}
static int load_pgm(const char *path,unsigned char *dest,struct stat *identity) {
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);
    if(fd<0)return -1;
    struct stat st;
    char header[sizeof(HDR)-1u];
    int ok=0;
    if(fstat(fd,&st)<0 || !S_ISREG(st.st_mode) ||
       st.st_size!=(off_t)(sizeof(header)+PIXELS) ||
       read_exact(fd,(unsigned char*)header,sizeof(header)) ||
       memcmp(header,HDR,sizeof(header)) ||
       read_exact(fd,dest,PIXELS))ok=-1;
    if(close(fd)<0)ok=-1;
    if(ok==0 && identity)*identity=st;
    return ok;
}
static int supported_fb(const struct fb_var_screeninfo *v,
                        const struct fb_fix_screeninfo *f) {
    return v->xres==PW && v->yres==PH &&
        v->bits_per_pixel==8 && v->grayscale==1 &&
        v->rotate==FB_ROTATE_CCW && !v->xoffset && !v->yoffset &&
        v->xres_virtual>=PW && v->yres_virtual>=PH &&
        f->type==FB_TYPE_PACKED_PIXELS &&
        f->visual==FB_VISUAL_STATIC_PSEUDOCOLOR &&
        f->line_length>=PW && f->smem_len &&
        f->smem_len<=MAX_FB_MAP &&
        (uint64_t)f->line_length*PH<=f->smem_len;
}
static void copy_to_fb(unsigned char *fb,size_t pitch,const unsigned char *gray) {
    for(unsigned y=0;y<PH;y++)memcpy(fb+y*pitch,gray+(size_t)y*PW,PW);
}
static void copy_from_fb(unsigned char *dst,const unsigned char *fb,size_t pitch) {
    for(unsigned y=0;y<PH;y++)memcpy(dst+(size_t)y*PW,fb+y*pitch,PW);
}
/* Align changes outward to an 8px boundary. Bounding rectangles that
 * cover most of the page are promoted to a full GC16 refresh, avoiding
 * the missing-gray / blank-region behavior observed in fast DU trials.
 */
static int changed_rect(const unsigned char *previous,const unsigned char *now,
                        struct pw3_rect *rect) {
    unsigned left=PW,top=PH,right=0,bottom=0;
    for(unsigned y=0;y<PH;y++) {
        size_t base=(size_t)y*PW;
        if(memcmp(previous+base,now+base,PW)==0)continue;
        for(unsigned x=0;x<PW;x++)if(previous[base+x]!=now[base+x]) {
            if(x<left)left=x;
            if(x>right)right=x;
            if(y<top)top=y;
            if(y>bottom)bottom=y;
        }
    }
    if(left==PW)return 0;
    left &= ~7u;top &= ~7u;
    right=(right+8u)&~7u;bottom=(bottom+8u)&~7u;
    if(right>PW)right=PW;
    if(bottom>PH)bottom=PH;
    *rect=(struct pw3_rect){top,left,right-left,bottom-top};
    return rect->width>0 && rect->height>0;
}
/* This policy preserves grayscale even when a small region changes. It
 * also resynchronises the panel after six smaller GC16 updates. A DU
 * waveform is never used for the browser's 8-bit grayscale content. */
static int should_full_refresh(int have_frame,int partial_burst,
                               struct pw3_rect changed) {
    return !have_frame || partial_burst>=MAX_PARTIAL_BURST ||
        (uint64_t)changed.width*changed.height*100u >=
        (uint64_t)PW*PH*FULL_AREA_PERCENT;
}
static int same_identity(const struct stat *a,const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino &&
        a->st_size==b->st_size &&
        a->st_mtim.tv_sec==b->st_mtim.tv_sec &&
        a->st_mtim.tv_nsec==b->st_mtim.tv_nsec;
}
static int epdc_update(int fd,uint32_t marker,struct pw3_rect region,
                       uint32_t waveform,uint32_t mode) {
    struct pw3_update u;
    memset(&u,0,sizeof(u));
    u.region=region;u.waveform=waveform;u.mode=mode;u.marker=marker;
    u.hist_bw=WF_DU;u.hist_gray=WF_GC16;u.temp=TEMP_AMBIENT;
    int64_t started=millis();
    int rc=ioctl(fd,MXCFB_SEND_UPDATE_PW3,&u);
    if(rc<0) {
        fprintf(stderr,"CODEX_BROWSER_FAST_EPDC_SEND_FAILED errno=%d\n",errno);
        return -1;
    }
    uint32_t wait_marker[2]={marker,0};
    rc=ioctl(fd,MXCFB_WAIT_FOR_UPDATE_COMPLETE_PW3,wait_marker);
    if(rc<0) {
        fprintf(stderr,"CODEX_BROWSER_FAST_EPDC_WAIT_FAILED errno=%d\n",errno);
        return -1;
    }
    printf("CODEX_BROWSER_FAST_EPDC waveform=%s mode=%s rect=%u,%u,%u,%u elapsed_ms=%lld\n",
           waveform==WF_DU?"DU":"GC16",
           mode==UPDATE_PARTIAL?"partial":"full",
           region.left,region.top,region.width,region.height,
           (long long)(millis()-started));
    fflush(stdout);
    return 0;
}
static int selftest(void) {
    if(sizeof(struct pw3_update)!=72 ||
       MXCFB_SEND_UPDATE_PW3!=0x4048462eu ||
       MXCFB_WAIT_FOR_UPDATE_COMPLETE_PW3!=0xc008462fu ||
       UPDATE_PARTIAL!=0 || UPDATE_FULL!=1 ||
       WF_DU!=1 || WF_GC16!=2)return 1;
    unsigned char *a=malloc(PIXELS),*b=malloc(PIXELS);
    if(!a||!b){free(a);free(b);return 1;}
    memset(a,255,PIXELS);memcpy(b,a,PIXELS);
    struct pw3_rect r={0};
    int ok=!changed_rect(a,b,&r);
    for(unsigned y=31;y<=37;y++)
        for(unsigned x=13;x<=21;x++)b[(size_t)y*PW+x]=0;
    if(!changed_rect(a,b,&r) || r.left!=8 || r.top!=24 ||
       r.width!=16 || r.height!=16)ok=0;
    memset(b,0,PIXELS);
    if(!changed_rect(a,b,&r) || r.left || r.top ||
       r.width!=PW || r.height!=PH)ok=0;
    memcpy(b,a,PIXELS);
    if(changed_rect(a,b,&r))ok=0;
    /* Grayscale pixels are real browser content, not binary DU input. */
    for(unsigned y=31;y<=37;y++)
        for(unsigned x=13;x<=21;x++)b[(size_t)y*PW+x]=160;
    if(!changed_rect(a,b,&r) || r.left!=8 || r.top!=24 ||
       r.width!=16 || r.height!=16)ok=0;
    struct pw3_rect small={24,8,16,16},large={0,0,PW,PH};
    if(!should_full_refresh(0,0,small) ||
       should_full_refresh(1,0,small) ||
       !should_full_refresh(1,MAX_PARTIAL_BURST,small) ||
       !should_full_refresh(1,0,large))ok=0;
    free(a);free(b);
    if(ok)puts("CODEX_BROWSER_FAST_PANEL_SELFTEST_PASS");
    return ok?0:1;
}
static int follow(const char *source) {
    int fd=open("/dev/fb0",O_RDWR|O_CLOEXEC|O_NOFOLLOW);
    if(fd<0){perror("fast framebuffer open");return 1;}
    struct fb_var_screeninfo v={0};
    struct fb_fix_screeninfo f={0};
    struct stat fst;
    if(fstat(fd,&fst) || !S_ISCHR(fst.st_mode) ||
       ioctl(fd,FBIOGET_VSCREENINFO,&v)<0 ||
       ioctl(fd,FBIOGET_FSCREENINFO,&f)<0 ||
       !supported_fb(&v,&f)) {
        fputs("CODEX_BROWSER_FAST_FB_UNSUPPORTED_NO_WRITE\n",stderr);
        close(fd);return 1;
    }
    unsigned char *mapped=mmap(NULL,f.smem_len,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
    if(mapped==MAP_FAILED){perror("fast mmap");close(fd);return 1;}
    unsigned char *snapshot=malloc(PIXELS), *last=malloc(PIXELS),
                  *candidate=malloc(PIXELS);
    if(!snapshot||!last||!candidate) {
        free(snapshot);free(last);free(candidate);
        munmap(mapped,f.smem_len);close(fd);return 1;
    }
    copy_from_fb(snapshot,mapped,f.line_length);
    struct sigaction sa={0};
    sa.sa_handler=request_stop;sigemptyset(&sa.sa_mask);
    sigaction(SIGINT,&sa,NULL);sigaction(SIGTERM,&sa,NULL);
    sigaction(SIGHUP,&sa,NULL);
    const struct pw3_rect full={0,0,PW,PH};
    struct stat previous={0};
    int have_previous=0,have_frame=0,partial_burst=0;
    unsigned count=0;
    int wrote=0,failed=0;
    int64_t started=millis(),last_draw=started-MIN_UPDATE_MS;
    if(started<0)failed=1;
    while(!failed && !stop_requested) {
        int64_t now=millis();
        if(now<0){failed=1;break;}
        if(now-started>=SESSION_MS)break;
        if(now-last_draw>=MIN_UPDATE_MS) {
            struct stat st;
            if(stat(source,&st)==0 && S_ISREG(st.st_mode) &&
               st.st_size==(off_t)(sizeof(HDR)-1u+PIXELS) &&
               (!have_previous || !same_identity(&st,&previous))) {
                struct stat opened;
                if(load_pgm(source,candidate,&opened)==0 &&
                   (!have_previous || !same_identity(&opened,&previous))) {
                    previous=opened;have_previous=1;
                    struct pw3_rect changed=full;
                    int differs=!have_frame || changed_rect(last,candidate,&changed);
                    if(differs) {
                        int do_full=should_full_refresh(have_frame,partial_burst,changed);
                        copy_to_fb(mapped,f.line_length,candidate);
                        wrote=1;
                        if(epdc_update(fd,0xc0df1000u+count,do_full?full:changed,
                                       WF_GC16,
                                       do_full?UPDATE_FULL:UPDATE_PARTIAL)<0){
                            failed=1;break;
                        }
                        memcpy(last,candidate,PIXELS);
                        have_frame=1;count++;last_draw=millis();
                        if(do_full)partial_burst=0;
                        else partial_burst++;
                        printf("CODEX_BROWSER_FAST_FRAME_DISPLAYED frame=%u mode=%s\n",
                               count,do_full?"GC16":"DU");
                        fflush(stdout);
                    }
                }
            }
        }
        pause_ms(70);
    }
    /* Best-effort restoration even if EPDC SEND or WAIT failed. */
    if(wrote) {
        copy_to_fb(mapped,f.line_length,snapshot);
        if(epdc_update(fd,0xc0df7fffu,full,WF_GC16,UPDATE_FULL)<0) {
            fputs("CODEX_BROWSER_FAST_RESTORE_FAILED\n",stderr);
            failed=1;
        } else puts("CODEX_BROWSER_FAST_SCREEN_RESTORED");
    }
    printf("CODEX_BROWSER_FAST_SESSION_END frames=%u\n",count);
    free(snapshot);free(last);free(candidate);
    munmap(mapped,f.smem_len);close(fd);
    return (!failed && count>0)?0:1;
}
int main(int argc,char **argv) {
    if(argc==2 && strcmp(argv[1],"--selftest")==0)return selftest();
    if(argc==4 && strcmp(argv[1],"--follow-pgm")==0 &&
       strcmp(argv[3],"--confirm-home-fast")==0 &&
       getenv("CODEX_BROWSER_PANEL_TRIAL") &&
       strcmp(getenv("CODEX_BROWSER_PANEL_TRIAL"),"HOME_FAST_PREVIEW")==0 &&
       codex_browser_from_home())
        return follow(argv[2]);
    fputs("Fast presenter requires real Home ancestry, explicit gate and --confirm-home-fast\n",
          stderr);
    return 78;
}
