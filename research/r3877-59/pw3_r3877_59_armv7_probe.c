/* R3877.59 host-only ARMv7 musl interpreter experiment.
 * Freestanding compile, imported libc/pthread functions resolved by the
 * pinned Alpine musl runtime loader. This is NOT a Kindle executable release.
 */
typedef unsigned int size_t;
typedef int ssize_t;
typedef struct __pthread *pthread_t;
extern int __libc_start_main(int (*)(int,char **,char **), int, char **,
                             void (*)(), void (*)(), void (*)());
extern int puts(const char *);
extern ssize_t getrandom(void *, size_t, unsigned);
extern int getentropy(void *, size_t);
extern int pthread_create(pthread_t *, const void *, void *(*)(void *), void *);
extern int pthread_join(pthread_t, void **);
extern int *__errno_location(void);
extern void exit(int) __attribute__((noreturn));

static __thread int tls_counter = 100;
static volatile int child_entered;
static void *child(void *arg)
{
    (void)arg;
    if (tls_counter != 100) return (void *)1;
    tls_counter += 7;
    if (tls_counter != 107) return (void *)2;
    child_entered=1;
    return (void *)0;
}

int main(int argc, char **argv, char **env)
{
    (void)argc; (void)argv; (void)env;
    if (tls_counter != 100) { puts("R59_FAIL_MAIN_TLS_INIT"); return 11; }
    pthread_t thread=0;
    if (pthread_create(&thread, 0, child, 0)) {
        puts("R59_FAIL_PTHREAD_CREATE"); return 12;
    }
    void *result=(void *)99;
    if (pthread_join(thread, &result) || result || !child_entered || tls_counter != 100) {
        puts("R59_FAIL_PTHREAD_TLS_OR_JOIN"); return 13;
    }
    puts("R59_PASS_ARMV7_PTHREAD_TLS");
    unsigned char random_bytes[16];
    ssize_t nr = getrandom(random_bytes, sizeof random_bytes, 0);
    if (nr == (ssize_t)sizeof random_bytes) puts("R59_OBS_GETRANDOM_SUPPORTED_BY_HOST");
    else if (nr == -1 && *__errno_location()==38) puts("R59_OBS_GETRANDOM_ENOSYS");
    else { puts("R59_FAIL_GETRANDOM_UNEXPECTED"); return 14; }
    if (nr == (ssize_t)sizeof random_bytes) {
        if (!getentropy(random_bytes, sizeof random_bytes)) puts("R59_OBS_GETENTROPY_SUPPORTED_BY_HOST");
        else {puts("R59_FAIL_GETENTROPY"); return 15;}
    }
    puts("R59_PASS_QEMU_ARMV7_MUSL_PROBE_ONLY");
    return 0;
}

void _start_c(long *p)
{
    int argc=p[0];
    char **argv=(void *)(p+1);
    __libc_start_main(main,argc,argv,0,0,0);
    exit(127);
}
__asm__(
".text\n"
".global _start\n"
".type _start,%function\n"
"_start:\n"
"  mov fp,#0\n"
"  mov lr,#0\n"
"  mov a1,sp\n"
"2: and ip,a1,#-16\n"
"  mov sp,ip\n"
"  bl _start_c\n"
);
