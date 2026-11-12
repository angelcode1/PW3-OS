# Codex browser integration

The pre-existing NetSurf proposal is in [NETSURF-EINK-BROWSER-PLAN.md](NETSURF-EINK-BROWSER-PLAN.md). The Alpine ARMv7 APKINDEX is now checked for a NetSurf framebuffer build and the result is recorded in BUILD-MANIFEST.json. The browser is **not yet installed**, and there is no validated PW3 EPDC screen/input adapter.

The standalone `build/pw3os/codex-browser.sh` launcher refuses to access a physical framebuffer unless explicitly enabled and a local backend-verification marker exists. Merely creating that marker is **not** proof of hardware compatibility.

Remaining work: pin a buildable NetSurf version and complete musl ARMv7 dependency closure, run an offscreen rendering test in ARM QEMU, implement/test the Cypress touch and Kindle EPDC interfaces, then integrate a browser entry after hardware validation. No browser runtime success or deployable implementation is claimed.

The existing six footer quotes remain local compiled strings in the upstream home UI, cycling by Unix day. Their replacement is pending the user's phrase list.
