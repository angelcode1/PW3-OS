-- KOReader supported userpatch, kept in KO_HOME outside the app release.
-- PW3-OS Alpine uses musl for networking and a separate GNU loader for UI.
local function is_pw3os()
    local f = io.open("/etc/own/name", "r")
    if not f then return false end
    local name = f:read("*l")
    f:close()
    return name == "PW3-OS"
end
if not is_pw3os() then return end

local NetworkMgr = require("ui/network/manager")
local OTAManager = require("ui/otamanager")
local Device = require("device")
local Version = require("version")
local UIManager = require("ui/uimanager")
local ConfirmBox = require("ui/widget/confirmbox")
local InfoMessage = require("ui/widget/infomessage")
local logger = require("logger")

local function wlan_has_route()
    local routes = io.open("/proc/net/route", "r")
    if not routes then return false end
    local available = false
    for line in routes:lines() do
        local iface, dest, _, flags = line:match("^(%S+)%s+(%S+)%s+(%S+)%s+(%S+)")
        local flagbits = flags and tonumber(flags, 16)
        if iface == "wlan0" and dest == "00000000" and
            flagbits and flagbits % 2 == 1 then
            available = true
            break
        end
    end
    routes:close()
    return available
end
function NetworkMgr:isOnline()
    return self:sysfsWifiOn() and wlan_has_route()
end
function NetworkMgr:turnOnWifi(callback)
    if not self:isOnline() then
        logger.warn("PW3-OS Alpine: connect via PW3-OS Wi-Fi app")
        return false
    end
    if callback then callback() end
    return true
end
function NetworkMgr:turnOffWifi()
    logger.warn("PW3-OS: refusing to disconnect Wi-Fi via Kindle LIPC")
    return false
end

local MANAGER = "/usr/local/lib/pw3os/koreader_update.py"
local function check_current()
    local f = io.popen("python3 " .. MANAGER .. " check 2>/dev/null", "r")
    if not f then return nil end
    local current, available
    for line in f:lines() do
        current = current or line:match("^CURRENT=(.+)$")
        available = available or line:match("^AVAILABLE=(.+)$")
    end
    local ok = f:close()
    if ok == false or not current or not available then return nil end
    return current, available
end
function OTAManager:fetchAndProcessUpdate()
    -- Own only the stable channel in PW3-OS. Preserve the upstream menu
    -- and prompt/confirmation UX; never patch a release's OTA source.
    if self:getOTAChannel() ~= "stable" then
        UIManager:show(InfoMessage:new{
            text = "PW3-OS automatic updates currently support the Stable channel. Select Stable under Update settings."
        })
        return
    end
    local current, available = check_current()
    if not available then
        UIManager:show(InfoMessage:new{
            text = "Unable to check KOReader updates. Check the PW3-OS Wi-Fi connection."
        })
        return
    end
    local current_num = Version:getNormalizedVersion(current)
    local available_num = Version:getNormalizedVersion(available)
    if current == available or (current_num and available_num and available_num <= current_num) then
        UIManager:show(InfoMessage:new{text = "KOReader is up to date (" .. current .. ")."})
        return
    end
    UIManager:show(ConfirmBox:new{
        text = "KOReader update available.\nInstalled: " .. current .. "\nAvailable: " .. available ..
            "\n\nPW3-OS will verify the release, retain a rollback copy, and install automatically.",
        ok_text = "Update",
        ok_callback = function()
            UIManager:show(InfoMessage:new{
                text = "Downloading and verifying KOReader for PW3-OS…",
                timeout = 3,
            })
            UIManager:scheduleIn(1, function()
                local command = "python3 " .. MANAGER ..
                    " stage >> /mnt/us/pw3os/koreader-updater/stage.log 2>&1"
                local result = os.execute(command)
                if result == 0 or result == true then
                    -- Use KOReader's normal Install confirmation and Exit(85).
                    -- The stable PW3-OS launcher catches 85 and switches a
                    -- verified release, then starts KOReader automatically.
                    Device:install()
                else
                    UIManager:show(InfoMessage:new{
                        text = "Update could not be safely staged. KOReader is unchanged. See /mnt/us/pw3os/koreader-updater/stage.log."
                    })
                end
            end)
        end,
    })
end
logger.info("PW3-OS persistent KOReader updater loaded")
