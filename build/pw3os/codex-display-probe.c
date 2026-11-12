/* Codex PW3 framebuffer capability probe.
 * No framebuffer mmap, no pixel writes and no EPDC/MXCFB refresh ioctls.
 * Run --selftest on a host; --read-only /dev/fb0 on an attended Kindle.
 */
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

static int report(const struct fb_var_screeninfo *v,
                  const struct fb_fix_screeninfo *f)
{
    if (!v || !f) return 2;
    int valid = v->xres > 0 && v->yres > 0 &&
                v->xres <= 2048 && v->yres <= 2048 &&
                v->xres_virtual >= v->xres &&
                v->yres_virtual >= v->yres &&
                (v->bits_per_pixel == 8 || v->bits_per_pixel == 16 ||
                 v->bits_per_pixel == 32) &&
                f->line_length >= (v->xres * v->bits_per_pixel+7)/8 &&
                f->smem_len >= f->line_length * v->yres;
    printf("CODEX_FB_PROBE=READ_ONLY\n");
    printf("xres=%u yres=%u xvirt=%u yvirt=%u bpp=%u "
           "grayscale=%u rotation=%u stride=%u fb_bytes=%u\n",
           v->xres,v->yres,v->xres_virtual,v->yres_virtual,
           v->bits_per_pixel,v->grayscale,v->rotate,
           f->line_length,f->smem_len);
    printf("format_type=%u visual=%u status=%s\n",
           f->type,f->visual,valid ? "CAPTURED_UNVERIFIED" : "UNSUPPORTED");
    return valid ? 0 : 4;
}

int main(int argc,char **argv)
{
    if (argc == 2 && strcmp(argv[1],"--selftest") == 0) {
        struct fb_var_screeninfo v={0};
        struct fb_fix_screeninfo f={0};
        v.xres=1072; v.yres=1448;
        v.xres_virtual=1072; v.yres_virtual=1448;
        v.bits_per_pixel=8; v.grayscale=1;
        f.line_length=1072; f.smem_len=1072u*1448u;
        return report(&v,&f);
    }
    if (argc != 3 || strcmp(argv[1],"--read-only") != 0 ||
        strcmp(argv[2],"/dev/fb0") != 0) {
        fprintf(stderr,"Usage: %s --selftest | --read-only /dev/fb0\n",argv[0]);
        return 64;
    }
    int fd=open("/dev/fb0",O_RDONLY|O_CLOEXEC|O_NOFOLLOW);
    if (fd < 0) {
        fprintf(stderr,"Open framebuffer for read-only probe failed: %s\n",
                strerror(errno));
        return 1;
    }
    struct stat st;
    struct fb_var_screeninfo v={0};
    struct fb_fix_screeninfo f={0};
    int ok=fstat(fd,&st)==0 && S_ISCHR(st.st_mode) &&
           ioctl(fd,FBIOGET_VSCREENINFO,&v)==0 &&
           ioctl(fd,FBIOGET_FSCREENINFO,&f)==0;
    close(fd);
    if (!ok) {
        fputs("Read-only framebuffer capability query failed\n",stderr);
        return 1;
    }
    return report(&v,&f);
}
