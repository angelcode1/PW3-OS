/* PW3 R3877.61. Mac/Colima-only ARMv7 musl getentropy ENOSYS probe.
 * Deliberately no Kindle boot, install, firmware write or physical execution.
 * The pinned AArch64 launcher forces host getrandom and statx to ENOSYS.
 * Verify musl getentropy returns ENOSYS (not an unsafe random fallback).
 */
typedef unsigned int size_t;
typedef int ssize_t;
typedef struct __pthread *pthread_t;
extern int __libc_start_main(int (*)(int,char **,char **), int, char **, void (*)(), void (*)(), void (*)());
extern int puts(const char *);
extern ssize_t getrandom(void *,size_t,unsigned);
extern int getentropy(void *,size_t);
extern int pthread_create(pthread_t *,const void *,void *(*)(void *),void *);
extern int pthread_join(pthread_t,void **);
extern int *__errno_location(void);
extern void exit(int) __attribute__((noreturn));
static __thread int tls_counter=100;
static volatile int child_entered;
static void *child(void *arg) {
 (void)arg;
 if(tls_counter!=100)return (void *)1;
 tls_counter+=7;
 if(tls_counter!=107)return (void *)2;
 child_entered=1;
 return (void *)0;
}
int main(int argc,char **argv,char **env){
 (void)argc;(void)argv;(void)env;
 if(tls_counter!=100){puts("R61_FAIL_MAIN_TLS");return 11;}
 pthread_t th=0;
 if(pthread_create(&th,0,child,0)){puts("R61_FAIL_PTHREAD_CREATE");return 12;}
 void *val=(void *)99;
 if(pthread_join(th,&val)||val||!child_entered||tls_counter!=100){puts("R61_FAIL_PTHREAD_TLS_OR_JOIN");return 13;}
 puts("R61_PASS_ARMV7_PTHREAD_TLS");
 unsigned char bytes[16];
 ssize_t n=getrandom(bytes,sizeof(bytes),0);
 if(n!=-1||*__errno_location()!=38){puts("R61_FAIL_GETRANDOM_NOT_ENOSYS");return 14;}
 puts("R61_OBS_GETRANDOM_ENOSYS");
 /* Unlike R59, getentropy must be called even though getrandom failed. */
 *__errno_location()=0;
 int ret=getentropy(bytes,sizeof(bytes));
 if(ret!=-1||*__errno_location()!=38){puts("R61_FAIL_GETENTROPY_NOT_ENOSYS");return 15;}
 puts("R61_OBS_GETENTROPY_ENOSYS");
 puts("R61_PASS_QEMU_MUSL_ENTROPY_ENOSYS_ONLY");
 return 0;
}
void _start_c(long *p){
 int argc=p[0];char **argv=(void *)(p+1);
 __libc_start_main(main,argc,argv,0,0,0);
 exit(127);
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\nmov fp,#0\nmov lr,#0\nmov a1,sp\n2: and ip,a1,#-16\nmov sp,ip\nbl _start_c\n");
