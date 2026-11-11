"""Allow safe KOReader OTA *checks* in PW3-OS GNU-on-musl Alpine.

Original Kindle KOReader uses glibc's LuaSocket DNS. The relocated R13
glibc-2.20 runtime lacks its NSS DNS modules, whereas Alpine curl resolves
and downloads correctly. For PW3-OS only, fetch OTA metadata via Alpine
curl, and prohibit automatic OTA *installation* (which would overwrite
the custom launcher and Kindle network compatibility patches).
"""
from pathlib import Path

FETCH_OLD = '''    socketutil:set_timeout()
    local code, headers, status = socket.skip(1, http.request{
        url     = ota_update_file,
        sink    = ltn12.sink.file(io.open(local_update_file, "w")),
    })
    socketutil:reset_timeout()
    if code ~= 200 then
        logger.warn("cannot find update file:", status or code or "network unreachable")
        logger.dbg("Response headers:", headers)
        return
    end'''
FETCH_NEW = '''    -- PW3-OS Alpine: its musl curl has working DNS even without the R13
    -- glibc 2.20 NSS modules. Never invoke Kindle/Amazon network controls.
    local pw3os = false
    local marker = io.open("/etc/own/name", "r")
    if marker then
        pw3os = marker:read("*l") == "PW3-OS"
        marker:close()
    end
    if pw3os then
        local cmd = util.shell_escape({
            "curl", "--fail", "--silent", "--show-error", "--location",
            "--connect-timeout", "5", "--max-time", "30",
            "--output", local_update_file, ota_update_file
        })
        if os.execute(cmd) ~= 0 then
            logger.warn("PW3-OS: Alpine curl unable to fetch OTA metadata:", ota_update_file)
            return
        end
    else
        socketutil:set_timeout()
        local code, headers, status = socket.skip(1, http.request{
            url     = ota_update_file,
            sink    = ltn12.sink.file(io.open(local_update_file, "w")),
        })
        socketutil:reset_timeout()
        if code ~= 200 then
            logger.warn("cannot find update file:", status or code or "network unreachable")
            logger.dbg("Response headers:", headers)
            return
        end
    end'''
INSTALL_OLD = '''    elseif ota_version then
        local update_message = T(_("Do you want to update?\\nInstalled version: %1\\nAvailable version: %2"),'''
INSTALL_NEW = '''    elseif ota_version then
        -- The official OTA updater replaces the custom GNU loader, startup
        -- script synchronization and Alpine Wi-Fi patches. Show the update
        -- but do not allow automatic installation on PW3-OS.
        local marker = io.open("/etc/own/name", "r")
        if marker then
            local pw3os = marker:read("*l") == "PW3-OS"
            marker:close()
            if pw3os then
                UIManager:show(InfoMessage:new{
                    text = T(_("KOReader update available: %1\\n\\nAutomatic installation is disabled on PW3-OS Alpine to preserve the GNU compatibility runtime and custom patches."), ota_package or "unknown"),
                })
                return
            end
        end
        local update_message = T(_("Do you want to update?\\nInstalled version: %1\\nAvailable version: %2"),'''
def patch_koreader_ota(src: str) -> str:
    if "PW3-OS: Alpine curl unable to fetch OTA metadata" in src:
        return src
    if src.count(FETCH_OLD) != 1 or src.count(INSTALL_OLD) != 1:
        raise ValueError("HOLD: Unexpected KOReader OTA code; refusing automatic patch")
    return src.replace(FETCH_OLD, FETCH_NEW, 1).replace(INSTALL_OLD, INSTALL_NEW, 1)

def patch_file(path: Path) -> None:
    import shutil
    current = path.read_text()
    updated = patch_koreader_ota(current)
    if current == updated:
        print("RESULT: PW3OS_OTA_CHECK_PATCH_ALREADY_INSTALLED")
        return
    backup = path.with_name(path.name+".before-pw3os-curl")
    temp = path.with_name(path.name+".pw3os-curl.tmp")
    if backup.exists() or temp.exists():
        raise RuntimeError("HOLD: Backup or temp file exists; refusing overwrite")
    shutil.copy2(path, backup)
    try:
        temp.write_text(updated)
        temp.chmod(path.stat().st_mode & 0o777)
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    print("RESULT: PW3OS_OTA_CHECK_ALPINE_CURL_INSTALLED")
    print("RESULT: PW3OS_AUTOMATIC_OTA_INSTALL_GUARDED")
    print(f"BACKUP={backup}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 koreader_ota.py /opt/koreader/frontend/ui/otamanager.lua")
    patch_file(Path(sys.argv[1]))
