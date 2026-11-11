/*
 * PW3-OS tiny ARM Linux EABI mount syscall bridge.
 * No libc, no loader; mounts ONLY the dedicated Alpine debug image.
 * Only mount(2) (rw ext3 at fixed root or exact scoped binds) and
 * umount2(2) (normal detach of only those targets) are exposed.
 * Does NOT remount root, reboot, alter Upstart, or configure loop devices.
 * Intended for an attended, one-shot Alpine runtime test only.
 */
__asm__(".text\n.global _start\n.type _start, %function\n_start:\nmov r0, sp\nbl pw3_main\nmov r7, #1\nsvc #0\n");

static int same(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *b) { if (*a++ != *b++) return 0; }
    return *a == *b;
}

static int valid_loop(const char *p) {
    /* /dev/loop/0 holds stock userstore: never touch it.
       Restrict to verified major/minor device node names exposed by preflight. */
    return same(p,"/dev/loop/1") || same(p,"/dev/loop/2") ||
           same(p,"/dev/loop/3") || same(p,"/dev/loop/4") ||
           same(p,"/dev/loop/5") || same(p,"/dev/loop/6") ||
           same(p,"/dev/loop/7") || same(p,"/dev/loop/8") ||
           same(p,"/dev/loop/9") || same(p,"/dev/loop/10") ||
           same(p,"/dev/loop/11") || same(p,"/dev/loop/12") ||
           same(p,"/dev/loop/13") || same(p,"/dev/loop/14") ||
           same(p,"/dev/loop/15") || same(p,"/dev/loop/16");
}
static int valid_target(const char *p) {
    return same(p, "/mnt/base-us/pw3os/.pw3os-alpine-live-root");
}
static int valid_bind(const char *source, const char *target) {
    return (same(source,"/mnt/base-us") &&
            same(target,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/mnt/us")) ||
           (same(source,"/dev") &&
            same(target,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/dev")) ||
           (same(source,"/dev/pts") &&
            same(target,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/dev/pts")) ||
           (same(source,"/proc") &&
            same(target,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/proc")) ||
           (same(source,"/sys") &&
            same(target,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/sys"));
}
static int valid_bind_target(const char *p) {
    return same(p,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/mnt/us") ||
           same(p,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/dev") ||
           same(p,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/dev/pts") ||
           same(p,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/proc") ||
           same(p,"/mnt/base-us/pw3os/.pw3os-alpine-live-root/sys");
}
static int sys_write(int fd, const void *buf, unsigned len) {
    register long r0 __asm__("r0") = fd;
    register long r1 __asm__("r1") = (long)buf;
    register long r2 __asm__("r2") = (long)len;
    register long r7 __asm__("r7") = 4;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r7) : "memory");
    return (int)r0;
}
static void say(const char *s) {
    unsigned n=0; while (s[n]) n++;
    sys_write(2,s,n);
}
static int sys_mount(const char *source, const char *target,
                     const char *fstype, unsigned long flags,
                     const void *data) {
    register long r0 __asm__("r0") = (long)source;
    register long r1 __asm__("r1") = (long)target;
    register long r2 __asm__("r2") = (long)fstype;
    register long r3 __asm__("r3") = flags;
    register long r4 __asm__("r4") = (long)data;
    register long r7 __asm__("r7") = 21;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r2), "r"(r3), "r"(r4), "r"(r7) : "memory");
    return (int)r0;
}
static int sys_umount2(const char *target, int flags) {
    register long r0 __asm__("r0") = (long)target;
    register long r1 __asm__("r1") = flags;
    register long r7 __asm__("r7") = 52;
    __asm__ volatile("svc #0" : "+r"(r0) : "r"(r1), "r"(r7) : "memory");
    return (int)r0;
}

/* argv from initial stack, no runtime entry objects needed */
int pw3_main(long *stack) {
    int argc=(int)stack[0];
    char **argv=(char **)(stack+1);
    int ret;
    if (argc == 4 && same(argv[1],"mount-rw") && valid_loop(argv[2]) && valid_target(argv[3])) {
        /* The backed-up original alpine.img remains untouched. For this distinct
         * alpine-debug.img, allow writes, noatime, nosuid and nodev. */
        ret=sys_mount(argv[2], argv[3], "ext3", 2u|4u|1024u, (void*)0);
        if (ret<0) { say("HOLD: mount(2) syscall failed\n"); return 3; }
        return 0;
    }
    if (argc == 4 && same(argv[1],"bind") && valid_bind(argv[2],argv[3])) {
        /* MS_BIND (0x1000). No remount of source or target, no persistence. */
        ret=sys_mount(argv[2], argv[3], (void*)0, 4096u, (void*)0);
        if (ret<0) { say("HOLD: bind mount(2) syscall failed\n"); return 5; }
        return 0;
    }
    if (argc == 3 && same(argv[1],"umount") &&
        (valid_target(argv[2]) || valid_bind_target(argv[2]))) {
        ret=sys_umount2(argv[2],0);
        if (ret<0) { say("HOLD: umount2(2) syscall failed\n"); return 4; }
        return 0;
    }
    say("Usage: pw3-debugmount mount-rw /dev/loop/{1..16} /mnt/base-us/pw3os/.pw3os-alpine-live-root\n");
    say("       pw3-debugmount bind /dev|/dev/pts|/proc|/sys|/mnt/base-us <exact corresponding Alpine path>\n");
    say("       pw3-debugmount umount <exact root or bound target>\n");
    return 2;
}
