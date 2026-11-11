FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git python3 gcc libc6-dev make e2fsprogs file unzip zip \
    tar xz-utils binutils && rm -rf /var/lib/apt/lists/*
ARG ZIG_SHA=24aeeec8af16c381934a6cd7d95c807a8cb2cf7df9fa40d359aa884195c4716c
RUN curl -fL --retry 3 https://ziglang.org/download/0.14.1/zig-x86_64-linux-0.14.1.tar.xz -o /tmp/zig.tar.xz \
 && echo "$ZIG_SHA  /tmp/zig.tar.xz" | sha256sum -c - \
 && mkdir /opt/zig && tar -xJf /tmp/zig.tar.xz -C /opt/zig --strip-components=1 \
 && ln -s /opt/zig/zig /usr/local/bin/zig && rm /tmp/zig.tar.xz
WORKDIR /work
ENTRYPOINT ["python3", "/repo/build/pw3os/build_image.py"]
