/* R3877.60.4 - AArch64 host-QEMU seccomp stacking launcher. NO KINDLE.
 * Tiny freestanding AArch64 executable. Adds a restrictive filter to the
 * Docker default seccomp filter (never substitutes an allow-all profile).
 * Force host getrandom(278) and statx(291) to errno 38 (ENOSYS) before execve.
 * This affects QEMU's HOST syscalls, not Kindle's Linux 3.0.35 kernel.
 * NOTE: no actual parent-image or physical-device modifications.
 */
typedef unsigned long ulong;
struct sock_filter { unsigned short code; unsigned char jt, jf; unsigned int k; };
struct sock_fprog { unsigned short len; struct sock_filter *filter; };
#define BPF_LD_W_ABS 0x20
#define BPF_JMP_JEQ_K 0x15
#define BPF_RET_K 0x06
#define AUDIT_ARCH_AARCH64 0xc00000b7U
#define SECCOMP_RET_KILL_PROCESS 0x80000000U
#define SECCOMP_RET_ERRNO 0x00050000U
#define SECCOMP_RET_ALLOW 0x7fff0000U
#define NR_PRCTL 167
#define NR_EXECVE 221
#define NR_WRITE 64
#define NR_EXIT_GROUP 94
#define PR_SET_NO_NEW_PRIVS 38
#define PR_SET_SECCOMP 22
#define SECCOMP_MODE_FILTER 2
#define GUEST_FILTERED_GETRANDOM_NR 278
#define GUEST_FILTERED_STATX_NR 291
#define ENOSYS 38
static struct sock_filter filter[] = {
  {BPF_LD_W_ABS, 0, 0, 4}, /* seccomp_data.arch */
  {BPF_JMP_JEQ_K, 1, 0, AUDIT_ARCH_AARCH64},
  {BPF_RET_K, 0, 0, SECCOMP_RET_KILL_PROCESS},
  {BPF_LD_W_ABS, 0, 0, 0}, /* seccomp_data.nr */
  {BPF_JMP_JEQ_K, 0, 1, GUEST_FILTERED_GETRANDOM_NR},
  {BPF_RET_K, 0, 0, SECCOMP_RET_ERRNO | ENOSYS},
  {BPF_JMP_JEQ_K, 0, 1, GUEST_FILTERED_STATX_NR},
  {BPF_RET_K, 0, 0, SECCOMP_RET_ERRNO | ENOSYS},
  {BPF_RET_K, 0, 0, SECCOMP_RET_ALLOW},
};
static struct sock_fprog program = {9, filter};
static long sys5(long nr, long a, long b, long c, long d, long e) {
  register long x8 __asm__("x8") = nr;
  register long x0 __asm__("x0") = a;
  register long x1 __asm__("x1") = b;
  register long x2 __asm__("x2") = c;
  register long x3 __asm__("x3") = d;
  register long x4 __asm__("x4") = e;
  __asm__ volatile ("svc #0" : "+r"(x0) : "r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4) : "memory");
  return x0;
}
static void die(long code) __attribute__((noreturn));
static void die(long code) {
  sys5(NR_EXIT_GROUP, code, 0, 0, 0, 0);
  for (;;) { }
}
void entry(ulong *initial_stack) __attribute__((noreturn));
void entry(ulong *initial_stack) {
  ulong argc=initial_stack[0];
  char **argv=(char **)(initial_stack+1);
  if (argc<2 || argc>40) die(125);
  char **envp=argv+argc+1;
  if (sys5(NR_PRCTL, PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)<0) die(125);
  if (sys5(NR_PRCTL, PR_SET_SECCOMP, SECCOMP_MODE_FILTER,(long)&program,0,0)<0) die(125);
  /* Selftest each filtered AArch64 host syscall BEFORE QEMU can run. */
  static unsigned char entropy_buffer[16];
  static unsigned char stat_buffer[256];
  static const char target_path[]="/bin/busybox";
  static const char marker[]="R604_HOST_FILTER_INSTALLED\n";
  static const char rmarker[]="R604_HOST_GETRANDOM_ENOSYS_VERIFIED\n";
  static const char smarker[]="R604_HOST_STATX_ENOSYS_VERIFIED\n";
  if (sys5(NR_WRITE, 2, (long)marker, sizeof(marker)-1, 0,0)!=(long)sizeof(marker)-1) die(125);
  /* On AArch64 Linux a blocked raw syscall must return -38 directly. */
  if (sys5(GUEST_FILTERED_GETRANDOM_NR,(long)entropy_buffer,sizeof(entropy_buffer),0,0,0) != -ENOSYS) die(124);
  if (sys5(NR_WRITE, 2, (long)rmarker, sizeof(rmarker)-1, 0,0)!=(long)sizeof(rmarker)-1) die(125);
  if (sys5(GUEST_FILTERED_STATX_NR,-100,(long)target_path,0,0x7ff,(long)stat_buffer) != -ENOSYS) die(124);
  if (sys5(NR_WRITE, 2, (long)smarker, sizeof(smarker)-1, 0,0)!=(long)sizeof(smarker)-1) die(125);
  sys5(NR_EXECVE,(long)argv[1], (long)(argv+1), (long)envp,0,0);
  die(126);
}
__asm__(".text\n.global _start\n.type _start,%function\n_start:\nmov x0, sp\nbl entry\n");
