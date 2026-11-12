/* Verify that a browser helper is a descendant of the real Codex Home.
 * A Home-launched app has no terminal. Do not permit noninteractive display
 * access merely because a shell set an environment variable. Linux /proc
 * must expose an actual /usr/local/bin/home ancestor to allow the preview.
 * Root can override this; this is an accident-prevention gate, not sandboxing.
 */
#ifndef CODEX_BROWSER_HOME_ORIGIN_H
#define CODEX_BROWSER_HOME_ORIGIN_H
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
static pid_t codex_browser_parent_of(pid_t pid) {
    char path[64], line[128];
    snprintf(path,sizeof(path),"/proc/%ld/status",(long)pid);
    FILE *f=fopen(path,"r");
    if (!f) return -1;
    pid_t parent=-1;
    while(fgets(line,sizeof(line),f)) {
        long p=0;
        if (sscanf(line,"PPid: %ld",&p)==1) {
            if (p>0) parent=(pid_t)p;
            break;
        }
    }
    fclose(f);
    return parent;
}
static int codex_browser_from_home(void) {
    pid_t pid=getppid();
    for (unsigned depth=0;depth<10 && pid>1;depth++) {
        char path[64], target[256];
        snprintf(path,sizeof(path),"/proc/%ld/exe",(long)pid);
        ssize_t len=readlink(path,target,sizeof(target)-1u);
        if (len>0 && (size_t)len<sizeof(target)) {
            target[len]=0;
            if (!strcmp(target,"/usr/local/bin/home"))
                return 1;
        }
        pid_t next=codex_browser_parent_of(pid);
        if (next<=1 || next==pid) break;
        pid=next;
    }
    return 0;
}
#endif
