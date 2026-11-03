-- R40.4.1: bounded, independent synthetic FileManager-only entrypoint.
-- Do not open any PDF/document, do not execute global migrations, use R394 strict safety guard.
local home='/tmp/r25-ko-home'
local original_require=require
local baseline=original_require('loop_guard') -- resolves /r4041/loop_guard.lua first
local guarded_require=require -- must preserve source-pinned R39.4 safety instrumentation
local seen=false
require=function(name)
    local module=guarded_require(name)
    if name=='apps/filemanager/filemanager' and not seen then
        seen=true
        local genuine_guarded=assert(module.showFiles)
        assert(type(genuine_guarded)=='function','R4041 FileManager startup absent')
        module.showFiles=function(self,path,...)
            assert(self==module and path==home..'/library' and module.instance==nil,
                   'R4041 unexpected second FileManager or non-temporary startup')
            local result=genuine_guarded(self,path,...)
            assert(module.instance and module.instance.file_chooser and
                   module.instance.file_chooser.path==home..'/library',
                   'R4041 authentic FileManager startup did not return')
            print('R4041_GENUINE_FILEMANAGER_SHOWFILES_RETURNED')
            return result
        end
    end
    return module
end
local function run()
    assert(os.getenv('HOME')==home and os.getenv('KO_HOME')==home,
           'R4041 only isolated guest HOME permitted')
    assert(#arg==1 and arg[1]==home..'/library',
           'R4041 only synthetic FileManager directory permitted')
    baseline.run()
    assert(seen,'R4041 authentic FileManager module never imported')
    print('R4041_FILEMANAGER_ONLY_ENTRYPOINT_COMPLETED')
end
return {run=run}
