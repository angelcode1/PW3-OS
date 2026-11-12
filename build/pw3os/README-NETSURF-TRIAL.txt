Codex NetSurf isolated ARMv7 RAM test bundle
===================================================

This is an attended test package for an existing Alpine v3.24 ARMv7
installation on PW3, NOT an installer, a web browser UI, or an EPDC driver.

The archive includes the NetSurf 3.11 framebuffer executable, local browser
assets, DejaVu fonts, staged shared libraries, and an isolated RAM launcher.
It does not alter /usr/bin, /usr/lib, the original Home app, or stock firmware.

Example after downloading the CI build artifact (run within Alpine SSH):
    mkdir -p /opt/codex-netsurf-trial
    tar -xzf /path/to/codex-netsurf-test-bundle.tar.gz -C /opt/codex-netsurf-trial
    cd /opt/codex-netsurf-trial
    sh ./codex-browser-trial.sh --diagnose
    sh ./codex-browser-trial.sh --offscreen-test

The RAM test is deliberately invisible on the Kindle screen. It starts
NetSurf against a local HTML fixture for eight seconds and stops it.
A PASS proves process liveness only; use the separately produced CI
Xvfb screenshot and pixel check to assess actual visual rendering.
No internet access is necessary for the fixture; no physical framebuffer
or Cypress touch device is opened by this launch path.

Clean up only this directory after testing:
    rm -rf /opt/codex-netsurf-trial

DO NOT add the test binary as a Home menu app. Its physical EPDC backend,
input mapping, old-kernel runtime and return-to-Home behaviour remain
unverified. If the trial fails, preserve the logs and do not change kernel,
boot scripts, or stock display drivers.

Copyright: NetSurf is GPL-2.0-or-later; retain upstream licences and
provide corresponding source under GPL when redistributing binary packages.
