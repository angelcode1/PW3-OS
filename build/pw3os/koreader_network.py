"""Patch KOReader's Kindle backend for PW3-OS Alpine networking.

On Amazon's rootfs KOReader uses LIPC to enable Wi-Fi and Microsoft's
DNS test to decide whether Internet access exists. In PW3-OS Alpine,
wlan0 and the default route are managed by wpa_supplicant and udhcpc.
The Kindle-specific online test must recognize that route without
invoking Amazon's Wi-Fi toggles.
"""
from pathlib import Path

ANCHOR = ("    NetworkMgr.isWifiOn = NetworkMgr.sysfsWifiOn\n"
          "    NetworkMgr.isConnected = NetworkMgr.ifHasAnAddress\n"
          "end\n")
MARKER = "-- PW3-OS Alpine network compatibility"

ADAPTER = """    NetworkMgr.isWifiOn = NetworkMgr.sysfsWifiOn
    NetworkMgr.isConnected = NetworkMgr.ifHasAnAddress

    -- PW3-OS Alpine network compatibility. No Amazon LIPC service is running.
    local marker = io.open("/etc/own/name", "r")
    local running_pw3os = false
    if marker then
        running_pw3os = marker:read("*l") == "PW3-OS"
        marker:close()
    end
    if running_pw3os then
        local function wlanHasDefaultRoute()
            local routes = io.open("/proc/net/route", "r")
            if not routes then return false end
            for line in routes:lines() do
                local iface, dest, _, flags = line:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)")
                if iface == "wlan0" and dest == "00000000" then
                    local f = tonumber(flags, 16)
                    if f and f % 2 == 1 then
                        routes:close()
                        return true
                    end
                end
            end
            routes:close()
            return false
        end
        -- A usable default route is enough to attempt an online operation.
        -- If DNS or HTTPS really fails, the operation will report its own
        -- network error rather than incorrectly asking to enable Wi-Fi.
        function NetworkMgr:isOnline()
            return self:sysfsWifiOn() and wlanHasDefaultRoute()
        end
        -- Protect Alpine's Wi-Fi session (including SSH) from Kindle LIPC calls.
        function NetworkMgr:turnOnWifi(complete_callback)
            if self:isOnline() then
                if complete_callback then complete_callback() end
                return true
            end
            logger.warn("PW3-OS: use the PW3-OS Wi-Fi app to connect")
            return false
        end
        function NetworkMgr:turnOffWifi()
            logger.warn("PW3-OS: KOReader cannot disable Alpine Wi-Fi; use the PW3-OS Wi-Fi app")
            return false
        end
    end
end
"""

def patch_koreader_network(content: str) -> str:
    if MARKER in content:
        return content
    if content.count(ANCHOR) != 1:
        raise ValueError("HOLD: KOReader Kindle backend unexpected or already modified")
    return content.replace(ANCHOR, ADAPTER, 1)

def patch_file(path: Path) -> None:
    import os
    import shutil
    import subprocess
    text = path.read_text()
    updated = patch_koreader_network(text)
    if updated == text:
        print("RESULT: PW3OS_KOREADER_NETWORK_ALREADY_PATCHED")
        return
    backup = path.with_name(path.name + ".before-pw3os-network")
    if backup.exists():
        raise RuntimeError("HOLD: BACKUP_ALREADY_EXISTS: " + str(backup))
    tmp = path.with_name(path.name + ".pw3os-network.tmp")
    if tmp.exists():
        raise RuntimeError("HOLD: TEMPORARY_FILE_ALREADY_EXISTS: " + str(tmp))
    shutil.copy2(path, backup)
    try:
        tmp.write_text(updated)
        tmp.chmod(path.stat().st_mode & 0o777)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    print("RESULT: PW3OS_KOREADER_NETWORK_PATCH_INSTALLED")
    print("BACKUP=" + str(backup))

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python3 koreader_network.py /opt/koreader/frontend/device/kindle/device.lua")
    patch_file(Path(sys.argv[1]))
