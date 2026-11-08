#!/bin/sh
# Optional provenance *experiment*, not needed for Mac runtime execution.
# May not reproduce exact bytes with a different clang/lld toolchain.
set -eu
: "${CC:=clang}"
: "${TARGET:=armv7-alpine-linux-musleabihf}"
: "${WORKDIR:=./r592-link-build}"
mkdir -p "$WORKDIR"
# Link-time-only SONAME marker: never copied to a QEMU guest / Kindle.
printf '%s\n' '/* Empty link-time-only SONAME anchor; no runtime file. */' > "$WORKDIR/empty.c"
"$CC" --target="$TARGET" -fuse-ld=lld -nostdlib -shared -fPIC \
  -Wl,-soname,libc.so -o "$WORKDIR/libc.so" "$WORKDIR/empty.c"
"$CC" --target="$TARGET" -fuse-ld=lld -nostdlib -fpie -pie \
  -Wl,-e,_start -Wl,--unresolved-symbols=ignore-all \
  -Wl,--dynamic-linker=/lib/ld-musl-armhf.so.1 -Wl,--no-as-needed \
  pw3_r3877_59_armv7_probe.c "$WORKDIR/libc.so" -o "$WORKDIR/probe.elf"
python3 - "$WORKDIR/probe.elf" <<'PY'
import hashlib,sys
p=sys.argv[1]
s=hashlib.sha256(open(p,'rb').read()).hexdigest()
print('REBUILT_SHA256='+s)
print('MATCHES_PINNED='+str(s=='b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4').lower())
PY
