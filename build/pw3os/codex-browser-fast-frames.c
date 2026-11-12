/* PW3 NetSurf SDL BMP -> 1072x1448 P5 grayscale in native ARMv7 code.
 * Replaces the slow Python pixel loops in the optional Home Browser Test only.
 * Does not open /dev/fb0 or an input device. Fixed RAM-only paths; never a
 * service or network program. One 33-second bounded process per trial.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#define SRC "/run/codex-browser/codex-live-sdl.bmp"
#define DST "/run/codex-browser/codex-browser-live-stream.pgm"
#define PGM "P5\n1072 1448\n255\n"
#define PW 1072u
#define PH 1448u
#define BW 600u
#define BH 800u
#define FRAME_BYTES (PW*PH)
#define MAX_BMP (3u*1024u*1024u)
static uint32_t u32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static uint16_t u16(const unsigned char *p) {
    return (uint16_t)p[0] | ((uint16_t)p[1]<<8);
}
static int64_t ticks_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) return -1;
    return (int64_t)t.tv_sec*1000 + t.tv_nsec/1000000;
}
static int read_exact(int fd, unsigned char *buf, size_t n) {
    while (n) {
        ssize_t k=read(fd,buf,n);
        if (k<0 && errno==EINTR) continue;
        if (k<=0) return -1;
        buf+=(size_t)k;n-=(size_t)k;
    }
    return 0;
}
static int write_exact(int fd, const unsigned char *buf, size_t n) {
    while (n) {
        ssize_t k=write(fd,buf,n);
        if (k<0 && errno==EINTR) continue;
        if (k<=0) return -1;
        buf+=(size_t)k;n-=(size_t)k;
    }
    return 0;
}
static int convert(const unsigned char *bmp, size_t len,
                   unsigned char *out) {
    if (len<54 || memcmp(bmp,"BM",2) || u32(bmp+2)!=len ||
        u32(bmp+14)<40 || u32(bmp+14)>124) return -1;
    uint32_t off=u32(bmp+10);
    int32_t w=(int32_t)u32(bmp+18), signed_h=(int32_t)u32(bmp+22);
    uint16_t planes=u16(bmp+26), bpp=u16(bmp+28);
    if (w!=(int32_t)BW || (signed_h!=(int32_t)BH && signed_h!=-(int32_t)BH) ||
        planes!=1 || (bpp!=24 && bpp!=32) || u32(bmp+30)!=0) return -1;
    uint32_t channels=bpp/8u, stride=(BW*channels+3u)&~3u;
    if (off<54 || off>(uint32_t)len ||
        (size_t)off + BH*stride != len) return -1;
    const unsigned char *pix=bmp+off;
    const unsigned dh=BW*PH >= BH*PW ? BH*PW/BW : PH;
    const unsigned dw=BW*PH >= BH*PW ? PW : BW*PH/BH;
    const unsigned left=(PW-dw)/2u, top=(PH-dh)/2u;
    memset(out,255,FRAME_BYTES);
    /* Fixed-point grayscale formula and nearest-neighbor mapping match
     * verify_direct_sdl.py exactly; no floating point or palette changes. */
    unsigned xoffset[PW];
    for(unsigned x=0;x<dw;x++) xoffset[x]=(x*BW/dw)*channels;
    for(unsigned y=0;y<dh;y++) {
        unsigned sy=y*BH/dh;
        const unsigned char *row=pix+
            (signed_h>0 ? BH-1u-sy : sy)*stride;
        unsigned char *dst=out+(y+top)*PW+left;
        for(unsigned x=0;x<dw;x++) {
            const unsigned char *p=row+xoffset[x];
            unsigned b=p[0],g=p[1],r=p[2];
            dst[x]=(unsigned char)((2126u*r+7152u*g+722u*b+5000u)/10000u);
        }
    }
    return 0;
}
static int publish(const unsigned char *frame) {
    char tmp[]="/run/codex-browser/.codex-browser-fast-pgm-XXXXXX";
    int fd=mkstemp(tmp);
    if(fd<0) return -1;
    int rc=write_exact(fd,(const unsigned char*)PGM,sizeof(PGM)-1u);
    if(rc==0) rc=write_exact(fd,frame,FRAME_BYTES);
    if(close(fd)<0) rc=-1;
    if(rc==0 && rename(tmp,DST)<0) rc=-1;
    if(rc!=0) unlink(tmp);
    return rc;
}
static int follow(int min_publish_ms) {
    unsigned char *bmp=malloc(MAX_BMP), *gray=malloc(FRAME_BYTES),
                  *previous=malloc(FRAME_BYTES);
    if(!bmp || !gray || !previous) {
        fputs("CODEX_BROWSER_FAST_CONVERTER_OOM\n",stderr);
        free(bmp);free(gray);free(previous);return 1;
    }
    struct stat prior={0};
    int has_prior=0, has_published=0, count=0;
    int64_t start=ticks_ms(), last_publish=start-2000;
    if(start<0) return 1;
    unlink(DST);
    while(ticks_ms()-start < 33000) {
        int64_t now=ticks_ms();
        if(now-last_publish>=min_publish_ms) {
            struct stat st;
            if(stat(SRC,&st)==0 && S_ISREG(st.st_mode) &&
               st.st_size>=54 && st.st_size<=(off_t)MAX_BMP &&
               (!has_prior || st.st_dev!=prior.st_dev ||
                st.st_ino!=prior.st_ino ||
                st.st_mtim.tv_sec!=prior.st_mtim.tv_sec ||
                st.st_mtim.tv_nsec!=prior.st_mtim.tv_nsec ||
                st.st_size!=prior.st_size)) {
                /* Capture uses atomic rename; open a single immutable inode
                 * and validate the same inode's actual size. */
                int fd=open(SRC,O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
                if(fd>=0) {
                    struct stat actual;
                    if(!fstat(fd,&actual) && S_ISREG(actual.st_mode) &&
                       actual.st_size>=54 && actual.st_size<=(off_t)MAX_BMP &&
                       !read_exact(fd,bmp,(size_t)actual.st_size)) {
                        int64_t t0=ticks_ms();
                        if(convert(bmp,(size_t)actual.st_size,gray)==0) {
                            if(!has_published ||
                               memcmp(gray,previous,FRAME_BYTES)!=0) {
                                if(publish(gray)==0) {
                                    memcpy(previous,gray,FRAME_BYTES);
                                    has_published=1;
                                    ++count;
                                    last_publish=now;
                                    printf("CODEX_BROWSER_FAST_PGM_PUBLISHED frame=%d conversion_ms=%lld\n",
                                           count,(long long)(ticks_ms()-t0));
                                    fflush(stdout);
                                } else perror("CODEX_BROWSER_FAST_PUBLISH");
                            }
                            /* Avoid wasting cycles on unchanged content. */
                            prior=actual;
                            has_prior=1;
                        } else {
                            fputs("CODEX_BROWSER_FAST_INVALID_BMP\n",stderr);
                        }
                    }
                    close(fd);
                }
            }
        }
        struct timespec pause={0,120000000};
        while(nanosleep(&pause,&pause)<0 && errno==EINTR){}
    }
    printf("CODEX_BROWSER_FAST_CONVERTER_END frames=%d\n",count);
    free(bmp);free(gray);free(previous);
    return count>0?0:4;
}
static int test(void) {
    size_t row=BW*3u, n=54u+row*BH;
    unsigned char *bmp=calloc(1,n), *gray=malloc(FRAME_BYTES);
    if(!bmp||!gray) return 1;
    bmp[0]='B';bmp[1]='M';
    bmp[2]=n&255;bmp[3]=(n>>8)&255;bmp[4]=(n>>16)&255;
    bmp[10]=54;bmp[14]=40;
    bmp[18]=BW&255;bmp[19]=BW>>8;
    bmp[22]=BH&255;bmp[23]=BH>>8;
    bmp[26]=1;bmp[28]=24;
    for(size_t i=54;i<n;i+=3){bmp[i]=0x77;bmp[i+1]=0x2a;bmp[i+2]=0xcc;}
    int good=convert(bmp,n,gray)==0;
    unsigned expected=(2126u*0xcc+7152u*0x2a+722u*0x77+5000u)/10000u;
    if(gray[0]!=255 || gray[9u*PW]!=(unsigned char)expected ||
       gray[(PH-1u)*PW]!=255)good=0;
    bmp[28]=16;
    if(convert(bmp,n,gray)==0)good=0;
    free(bmp);free(gray);
    if(good) puts("CODEX_BROWSER_FAST_CONVERTER_SELFTEST_PASS");
    return good?0:1;
}
int main(int argc,char **argv) {
    if(argc==2 && strcmp(argv[1],"--selftest")==0) return test();
    if(argc==3 && strcmp(argv[2],"33")==0 &&
       getenv("CODEX_BROWSER_LIVE_TRIAL") &&
       strcmp(getenv("CODEX_BROWSER_LIVE_TRIAL"),"EXPLICIT")==0) {
        if(strcmp(argv[1],"--follow-seconds")==0)return follow(1900);
        if(strcmp(argv[1],"--fast-follow-seconds")==0 &&
           getenv("CODEX_BROWSER_FAST_REFRESH") &&
           strcmp(getenv("CODEX_BROWSER_FAST_REFRESH"),"PW3_ONESHOT")==0)
            return follow(650);
    }
    fputs("Usage: --selftest | --follow-seconds 33 | gated --fast-follow-seconds 33\n",stderr);
    return 78;
}
