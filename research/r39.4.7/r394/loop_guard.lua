-- R39.3 HOME/FM RETURN AND DOCUMENT LIFECYCLE; preserves R39.2.4 scroll observer: follow genuine ReaderView scroll layout drawScrollPages.
-- Preserve R39.2.3 bounded diagnostic, original R25 control and strict navigation gate.
-- New bounded real UIManager GotoPage(2) event before genuine ReaderUI Close.
-- Adds only the missing lifecycle methods to the R17 in-memory Input instance.
-- ReaderUI and all staged sources remain genuine and unchanged.
-- Global migration execution remains skipped; ReaderUI init may run per-book migration on ephemeral PDF.
-- Every allowed write is confined to a fresh synthetic /tmp home.
local home='/tmp/r25-ko-home'
local function in_home(path)
    if type(path)~='string' or path:sub(1,#home+1)~=home..'/' then return false end
    if path:find('\\',1,true) or path:find('//',1,true) or path:find('/./',1,true)
       or path:find('/../',1,true) or path:match('/%.%.$') or path:match('/%.$') then return false end
    return true
end
local R25_ENABLED=true
local r39_pdf=home..'/library/r39-original-two-pages.pdf'
local r39_reader_seen=false
local r39_page1_verified=false
local r39_page2_verified=false
local r39_home_sent=false
local r39_home_returned=false
local r39_saved_doc=nil
local r39_saved_reader=nil
local r39_saved_settings_file=nil
local r3931_home_snapshot_count=0
local r3933_home_sentinel_count=0
-- R39.4: a second, independent, same-process open/close cycle.
local r394_cycle=1
local r394_first_doc=nil
local r394_first_reader=nil
local r394_first_draws=nil
local r394_second_scroll_returned=false
local r394_second_home_sent=false
local r394_second_home_returned=false
local r394_input_lifecycles=0
local r394_second_initial_page=nil

-- Read-only verification; does not release refs or mutate the PDF engine.
local function r3933_pdf_engine_released()
    local registry=package.loaded['document/documentregistry']
    return r39_saved_doc~=nil and r39_saved_doc.is_open==false and
           rawget(r39_saved_doc,'_document')==nil and
           r39_saved_doc._document==false and
           registry~=nil and type(registry.getReferenceCount)=='function' and
           registry:getReferenceCount(r39_pdf)==nil
end
-- R39.4.6: first-cycle document is archived in r394_first_doc before
-- the second real FileManager:openFile, not retained in r39_saved_doc.
local function r394_first_pdf_released()
    local registry=package.loaded['document/documentregistry']
    return r394_first_doc~=nil and r394_first_doc.is_open==false and
           rawget(r394_first_doc,'_document')==nil and
           r394_first_doc._document==false and r394_first_reader~=nil and
           r394_first_reader.document==nil and
           registry~=nil and type(registry.getReferenceCount)=='function' and
           registry:getReferenceCount(r39_pdf)==nil
end
-- The genuine PDF may use ReaderView:drawSinglePage (page mode) or
-- ReaderView:drawScrollPages (scroll mode). Record only after original returns.
-- ReaderView.state.drawn is only set for non-paging/CRE documents.
local r39_real_pdf_draws={[1]=0,[2]=0}
local r39_draw_marker_emitted={[1]=false,[2]=false}
-- An empty first paint poll is permitted once per page. Trigger only the
-- real UIManager dirty/repaint machinery, never call any renderer directly.
local r39_bounded_repaint_requests={[1]=0,[2]=0}
local r39_input_poll_count=0
-- Observational counters only. These never authorize page-change success.
local r39_diag={repaints=0,reader_dirty_entries=0,container_paints=0,view_paints=0}
local function diag_reader()
    local klass=package.loaded['apps/reader/readerui']
    return klass and klass.instance or nil
end
local r39_input_inhibit=0
local r39_input_until=0
local stats={setup=0,defaults=0,settings=0,collection_reads=0,device=0,canvas=0,patches=0,version=0,migrations=0,bidi=0,input_ready=0,uimanager=0,discovery=0,plugin_main=0,plugin_meta=0,owner=0,filemanager=0,loop=0,events=0,device_exit=0,os_exit=0,screen_scale=0,meminfo_reads=0,meminfo_closes=0,denied=0}
local native_require=require
local native_dofile=dofile
local native_open=io.open
-- R39.4.5: witness a single original KOReader-generated sidecar write in
-- the first document's Home close, before any second-open evaluation.
local r3945_sidecar=home..'/library/r39-original-two-pages.sdr/metadata.pdf.lua'
local r3945_sidecar_writes=0
local r3945_sidecar_loads=0
-- R39.4.6 first-reader archive remains authoritative. R39.4.7 observes
-- two different source-bound consumers of the same disposable sidecar.
local native_lines=io.lines
local native_rename=os.rename
local native_remove=os.remove
local native_execute=os.execute
local native_popen=io.popen
local real_ui,real_fm,real_loader
local ink_root='plugins/ink-away.koplugin'
local forbidden={liblipclua=true,libopenlipclua=true,
 ['device/kindle/device']=true,['device/kindle/powerd']=true,
 ['device/sdl/device']=true}
-- R39.4.3: observe the FIRST blocked operation only; never change any
-- permission, increment, exception, or original strict shutdown predicate.
-- Report a bounded reason class and staged call site, never the raw path.
local function denial_site()
    -- Stack: denial_site -> deny -> blocked wrapper -> genuine consumer.
    local caller=debug.getinfo(4,'Sl')
    local source=caller and caller.source or ''
    local loc='other'
    if type(source)=='string' then
        local rel=source:match('^@?(frontend/[%w_./-]+%.lua)$')
        if rel and #rel<=110 then loc=rel
        elseif source:match('^@?plugins/ink%-away%.koplugin/') then loc='ink-away-plugin'
        elseif source:match('^@?reader%.lua$') then loc='reader.lua'
        elseif source:match('^@?/r394/') then loc='experimental-guard' end
    end
    local line=caller and caller.currentline or -1
    if type(line)~='number' or line<0 or line>100000 then line=0 end
    return loc,math.floor(line)
end
local function deny(reason)
    stats.denied=stats.denied+1
    if stats.denied==1 then
        local kind=type(reason)=='string' and reason:match('^([A-Z_]+)') or nil
        local kinds={FILE_READ=true,FILE_WRITE=true,FILE_LINES=true,
                     MEMINFO_WRITE_MODE=true,MEMINFO_UNEXPECTED_CALLER=true,
                     SHELL=true,POPEN=true,RENAME=true,REMOVE=true,
                     MODULE=true,DOFILE=true}
        if not kinds[kind] then kind='OTHER' end
        local site,line=denial_site()
        print('R39_4_3_FIRST_DENIAL kind='..kind..' caller='..site..
              ' line='..line..' cycle='..r394_cycle..
              ' events='..stats.events..' filemanagers='..stats.filemanager)
    end
    error('R23_DENIED_'..reason,2)
end
local function protected(path)
    return type(path)=='string' and (path:match('^/dev/') or path:match('^/sys/')
       or path:match('^/proc/') or path:match('^/results/') or path:match('^/stage/'))
end
-- Only KOReader's own util.calcFreeMem may read a synthetic memory report.
-- No kernel proc file is opened: the file-like object is built in Lua memory.
-- Everything else in /proc, /sys, /dev and the staged root stays denied.
local function synthetic_meminfo()
    local lines={
       'MemTotal:       262144 kB',
       'MemFree:        131072 kB',
       'Buffers:         16384 kB',
       'Cached:          32768 kB',
    }
    local f={_closed=false}
    function f:lines()
        assert(self==f and not self._closed, 'synthetic meminfo read after close')
        local index=0
        return function()
            assert(not f._closed, 'synthetic meminfo iterator used after close')
            index=index+1
            return lines[index]
        end
    end
    function f:close()
        assert(self==f and not self._closed, 'synthetic meminfo double close')
        self._closed=true
        stats.meminfo_closes=stats.meminfo_closes+1
        return true
    end
    return f
end
io.open=function(path,mode)
    mode=mode or 'r'
    if path=='/proc/meminfo' then
        if mode~='r' then deny('MEMINFO_WRITE_MODE') end
        local origin=debug.getinfo(2,'Sl')
        if not (origin and type(origin.source)=='string' and
                origin.source:find('frontend/util%.lua') and
                origin.currentline==722) then
            deny('MEMINFO_UNEXPECTED_CALLER')
        end
        assert(stats.uimanager==1 and stats.screen_scale>0 and stats.migrations==1,
               'synthetic memory query outside expected R24 boundary')
        if stats.meminfo_reads==0 then
            print('R24_GENUINE_UTIL_MEMINFO_VIRTUALIZED')
        end
        stats.meminfo_reads=stats.meminfo_reads+1
        return synthetic_meminfo()
    end
    if protected(path) then deny('FILE_READ:'..tostring(path)) end
    if mode:find('[wax+]') and not in_home(path) then deny('FILE_WRITE:'..tostring(path)) end
    if path==r3945_sidecar and mode:find('[wax+]') then
        local caller=debug.getinfo(2,'Slf')
        local util=package.loaded['util']
        local original_writer=caller and util and type(util.writeToFile)=='function'
            and caller.func==util.writeToFile
            and caller.currentline==1147
            and type(caller.source)=='string'
            and caller.source:match('^@?frontend/util%.lua$')~=nil
        -- R39.4.6: exactly one genuine write-open in each Home close.
        -- The second is legal only AFTER one source-bound sidecar read and
        -- a genuine second PDF draw; no new target, caller or write mode.
        local first_write=(stats.events==2 and r394_cycle==1 and
                           stats.filemanager==1 and r3945_sidecar_writes==0 and
                           r39_home_sent and not r39_home_returned)
        local second_write=(stats.events==3 and r394_cycle==2 and
                            stats.filemanager==2 and r3945_sidecar_writes==1 and
                            r3945_sidecar_loads==2 and r394_second_home_sent and
                            not r394_second_home_returned and
                            r394_second_scroll_returned and r394_input_lifecycles==2 and
                            r394_first_doc~=nil and r394_first_doc.is_open==false and
                            rawget(r394_first_doc,'_document')==nil and
                            r394_first_doc._document==false and
                            r394_first_reader~=nil and r394_first_reader.document==nil)
        if not (original_writer and mode=='wb' and
                (first_write or second_write)) then
            deny('SIDECAR_WRITE_PROVENANCE')
        end
        local handle=native_open(path,mode)
        if handle then
            r3945_sidecar_writes=r3945_sidecar_writes+1
            if first_write then
                print('R39_4_6_FIRST_GENUINE_SIDECAR_WRITE_OPEN')
            elseif second_write then
                print('R39_4_6_SECOND_GENUINE_SIDECAR_WRITE_OPEN')
            end
        end
        return handle
    end
    return native_open(path,mode)
end
io.lines=function(path,...)
    if protected(path) then deny('FILE_LINES:'..tostring(path)) end
    return native_lines(path,...)
end
os.execute=function() deny('SHELL') end
io.popen=function() deny('POPEN') end
os.rename=function(a,b)
    if not in_home(a) or not in_home(b) then deny('RENAME') end
    return native_rename(a,b)
end
os.remove=function(path)
    if not in_home(path) then deny('REMOVE') end
    return native_remove(path)
end
-- Avoid real filesystem and exec access even via accidental package imports.
require=function(name)
    if forbidden[name] then deny('MODULE:'..name) end
    local module=native_require(name)
    if name=='setupkoenv' and stats.setup==0 then
        stats.setup=1
        print('R23_REAL_SETUPKOENV_IMPORTED')
    elseif name=='userpatch' and not stats.userpatch_installed then
        stats.userpatch_installed=true
        local original=module.applyPatches
        assert(type(original)=='function')
        module.applyPatches=function(priority)
            stats.patches=stats.patches+1
            assert(priority==module.early_once or priority==module.early
                   or priority==module.late or priority==module.before_exit
                   or priority==module.on_exit)
            return nil -- explicit no-user-script policy; real module still imported
        end
    elseif name=='version' and not stats.version_installed then
        stats.version_installed=true
        assert(type(module.updateVersionLog)=='function')
        module.updateVersionLog=function(_,model)
            assert(model=='R17StandalonePW3Synthetic')
            stats.version=stats.version+1
            print('R23_VERSION_DISK_LOG_HELD')
        end
    elseif name=='luasettings' and not stats.settings_installed then
        stats.settings_installed=true
        local genuine=module.open
        assert(type(genuine)=='function' and debug.getinfo(genuine,'S').source:find('frontend/luasettings%.lua'))
        module.open=function(self,path,...)
            -- Only the real top-level reader settings and the genuine
            -- ReadCollection's favorite-list settings may be opened.
            -- No arbitrary LuaSettings path is implicitly trusted.
            if path==home..'/settings.reader.lua' then
                assert(stats.settings==0, 'duplicate top-level reader settings open')
                stats.settings=1
                return genuine(self,path,...)
            end
            if path==home..'/settings/collection.lua' then
                local caller=debug.getinfo(2,'Sl')
                assert(caller and type(caller.source)=='string'
                       and caller.source:find('frontend/readcollection%.lua')
                       and (caller.currentline==43 or caller.currentline==74),
                       'collection settings caller not genuine pinned ReadCollection')
                assert(stats.settings==1 and stats.uimanager==1
                       and stats.screen_scale>0 and stats.meminfo_reads>0,
                       'collection settings attempted before genuine startup sequence')
                stats.collection_reads=stats.collection_reads+1
                local result=genuine(self,path,...)
                if stats.collection_reads==1 then
                    print('R24_GENUINE_READCOLLECTION_SETTINGS_OPENED')
                end
                return result
            end
            error('R24_UNEXPECTED_LUASETTINGS_PATH:'..tostring(path)
                  ..':caller='..tostring(debug.getinfo(2,'S').source),2)
        end
    elseif name=='device' then
        assert(module.model=='R17StandalonePW3Synthetic' and module.input.is_synthetic)
    elseif name=='ui/bidi' and not stats.bidi_installed then
        stats.bidi_installed=true
        local real_setup=module.setup
        assert(type(real_setup)=='function'
               and debug.getinfo(real_setup,'S').source:find('frontend/ui/bidi%.lua'))
        module.setup=function(...)
            assert(stats.migrations==1 and stats.canvas==1 and stats.bidi==0,
                   'Bidi attempted before the explicitly skipped migration position')
            local result=real_setup(...)
            stats.bidi=1
            print('R23_REAL_BIDI_SETUP_AFTER_SKIP')
            return result
        end
    elseif name=='ui/uimanager' and not stats.uimanager_installed then
        assert(stats.migrations==1 and stats.bidi==1 and stats.input_ready==1
               and stats.uimanager==0,
               'UIManager import must follow the genuine synthetic input handshake')
        assert(type(module.run)=='function' and type(module._window_stack)=='table'
               and debug.getinfo(module.run,'S').source:find('frontend/ui/uimanager%.lua'),
               'genuine KOReader UIManager source required')
        stats.uimanager_installed=true
        stats.uimanager=1
        real_ui=module
        -- Genuine repaint is always called unchanged. Log only a bounded sample
        -- AFTER an actual ReaderUI instance exists, so prior startup stays quiet.
        local original_repaint=assert(module._repaint)
        local oi=debug.getinfo(original_repaint,'S')
        assert(oi and oi.source:find('frontend/ui/uimanager%.lua'),
               'R39.2.3 original genuine UIManager:_repaint required')
        module._repaint=function(self,...)
            assert(self==module,'R39.2.3 unexpected UIManager repaint owner')
            local reader=diag_reader()
            local capture=reader~=nil and r39_diag.repaints<5
            if capture then
                r39_diag.repaints=r39_diag.repaints+1
                local dirty=self._dirty[reader]~=nil
                if dirty then r39_diag.reader_dirty_entries=r39_diag.reader_dirty_entries+1 end
                local top=self._window_stack[#self._window_stack]
                print('R39_2_3_REPAINT_ENTER n='..r39_diag.repaints..
                    ' dirty='..tostring(dirty)..' top_reader='..tostring(top~=nil and top.widget==reader)..
                    ' child_view='..tostring(reader[1]~=nil and reader[1]==reader.view)..
                    ' skip='..tostring(reader.skip_paint==true))
            end
            local result=original_repaint(self,...)
            if capture then
                print('R39_2_3_REPAINT_RETURN n='..r39_diag.repaints..
                    ' container='..r39_diag.container_paints..' view='..r39_diag.view_paints..
                    ' draws1='..r39_real_pdf_draws[1]..' draws2='..r39_real_pdf_draws[2])
            end
            return result
        end
        print('R23_REAL_UIMANAGER_MODULE_IMPORTED')
        -- R24 may stop at run entry, but its FileManager must initialize first.
        -- R25 leaves UIManager.run untouched and verifies real loop via synthetic input.
        if not R25_ENABLED then
            local stock_run=module.run
            module.run=function(self,...)
                assert(self==module and stats.filemanager==1,
                       'event loop reached before genuine FileManager startup')
                assert(type(stock_run)=='function' and
                       debug.getinfo(stock_run,'S').source:find('frontend/ui/uimanager%.lua'))
                print('R24_REAL_EVENT_LOOP_ENTRY_HELD')
                error('R24_INTENTIONAL_PRE_LOOP_HOLD',2)
            end
        end
    elseif name=='pluginloader' and not stats.plugin_installed then
        assert(stats.uimanager==1 and G_reader_settings,
               'plugin loader was reached before UIManager/settings')
        local stock_load=module.loadPlugins
        local stock_create=module.createPluginInstance
        assert(type(stock_load)=='function' and type(stock_create)=='function')
        assert(debug.getinfo(stock_load,'S').source:find('frontend/pluginloader%.lua'))
        assert(debug.getinfo(stock_create,'S').source:find('frontend/pluginloader%.lua'))
        assert(module.enabled_plugins==nil and module.loaded_plugins==nil,
               'preexisting plugin loading forbidden')
        stats.plugin_installed=true
        real_loader=module
        G_reader_settings:saveSetting('inkaway_update_auto',false)
        G_reader_settings:saveSetting('inkaway_welcome_seen',true)
        G_reader_settings:saveSetting('inkaway_gestures_setup',2)
        G_reader_settings:saveSetting('extra_plugin_paths',{})
        module._discover=function(self)
            assert(self==module and stats.discovery<=2 and module.loadPlugins==stock_load
                   and module.createPluginInstance==stock_create,
                   'only R39 bounded original-reader plugin discovery is permitted')
            if stats.discovery>=1 then
                assert(real_fm and real_fm.instance==nil,
                       'ReaderUI rediscovery must follow genuine FileManager close')
                print('R39_READER_PLUGIN_REDISCOVERY_AFTER_FILEMANAGER_CLOSE')
            end
            stats.discovery=stats.discovery+1
            if stats.discovery==1 then print('R24_ONLY_INKAWAY_DISCOVERED') end
            return {{main=ink_root..'/main.lua',meta=ink_root..'/_meta.lua',
                     name='ink-away',path=ink_root,disabled=false}}
        end
    elseif name=='ui/widget/container/inputcontainer' and not stats.r39_inputcontainer_observed then
        stats.r39_inputcontainer_observed=true
        local original_paint=assert(module.paintTo)
        local oi=debug.getinfo(original_paint,'S')
        assert(oi and oi.source:find('frontend/ui/widget/container/inputcontainer%.lua'),
               'R39.2.3 genuine InputContainer:paintTo required')
        module.paintTo=function(self,bb,x,y)
            local reader=diag_reader()
            local capture=reader~=nil and self==reader and r39_diag.container_paints<6
            if capture then
                r39_diag.container_paints=r39_diag.container_paints+1
                print('R39_2_3_READER_CONTAINER_PAINT n='..r39_diag.container_paints..
                      ' child_view='..tostring(self[1]~=nil and self[1]==self.view)..
                      ' skip='..tostring(self.skip_paint==true)..
                      ' bb='..tostring(bb~=nil))
            end
            return original_paint(self,bb,x,y)
        end
    elseif name=='apps/filemanager/filemanager' and not stats.fm_installed then
        assert(stats.uimanager==1 and stats.plugin_installed and stats.discovery==0,
               'FileManager module imported in unexpected state')
        local stock_show=module.showFiles
        assert(type(stock_show)=='function' and
               debug.getinfo(stock_show,'S').source:find('frontend/apps/filemanager/filemanager%.lua'),
               'genuine FileManager:showFiles required')
        stats.fm_installed=true
        real_fm=module
        module.showFiles=function(self,path,...)
            if stats.filemanager==1 or (stats.filemanager==2 and r394_cycle==2) then
                local returning_second=(stats.filemanager==2)
                local focused=select(1,...)
                assert(self==module and path==home..'/library/' and
                       focused==r39_pdf and stats.events==(returning_second and 3 or 2) and
                       (returning_second and r394_second_home_sent or r39_home_sent) and
                       (returning_second and not r394_second_home_returned or not r39_home_returned) and
                       module.instance==nil,
                       'R39.3 unexpected or duplicated FileManager return')
                local caller=debug.getinfo(3,'Sl')
                assert(caller and type(caller.source)=='string' and
                       caller.source:find('frontend/apps/reader/readerui%.lua') and
                       caller.currentline==594,
                       'R39.3 FileManager return must come from genuine ReaderUI:showFileManager')
                if returning_second then
                    -- R39.4: a second bounded read-only pre-FM-construction snapshot.
                    -- Do not change the document or registry to influence the result.
                    local registry=package.loaded['document/documentregistry']
                    local n=registry and registry:getReferenceCount(r39_pdf)
                    assert(n==nil,'R39.4 second Home retains PDF registry ownership')
                    print('R39_4_SECOND_HOME_ENGINE_STATE raw_engine_nil='..
                          tostring(r39_saved_doc~=nil and rawget(r39_saved_doc,'_document')==nil)..
                          ' inherited_engine_false='..tostring(r39_saved_doc~=nil and r39_saved_doc._document==false)..
                          ' registry_refs=none reader_instance_nil='..
                          tostring(native_require('apps/reader/readerui').instance==nil)..
                          ' reader_document_nil='..tostring(r39_saved_reader~=nil and r39_saved_reader.document==nil)..
                          ' distinct_document='..tostring(r39_saved_doc~=r394_first_doc)..
                          ' filemanager_instance_nil='..tostring(module.instance==nil))
                    assert(r394_first_doc and r394_first_reader and r394_first_draws and
                           r394_second_scroll_returned and r39_saved_doc~=r394_first_doc and
                           r39_saved_reader~=r394_first_reader and
                           r3933_pdf_engine_released() and
                           native_require('apps/reader/readerui').instance==nil and
                           r39_saved_reader and r39_saved_reader.document==nil,
                           'R39.4 second genuine document engine/ReaderUI not released')
                    local result=stock_show(self,path,...)
                    -- R39.4.2: ONE bounded, read-only snapshot after genuine
                    -- stock_show, BEFORE the same fail-closed R39.4 assertion.
                    -- Do not modify FM, stack, selected path or registry.
                    local fm=module.instance
                    local stack=real_ui._window_stack
                    local depth=#stack
                    local top=stack[depth] and stack[depth].widget or nil
                    local idx=0
                    for i=1,depth do
                        if stack[i].widget==fm and fm~=nil then idx=i end
                    end
                    local chooser=fm and fm.file_chooser or nil
                    local pathkind='unavailable'
                    if chooser then
                        if chooser.path==home..'/library' then pathkind='expected'
                        elseif chooser.path==home..'/library/' then pathkind='trailing_slash'
                        elseif type(chooser.path)=='string' and in_home(chooser.path) then
                            pathkind='other_home'
                        else pathkind='outside_or_unset' end
                    end
                    print('R39_4_2_SECOND_FILEMANAGER_STATE fm_present='..tostring(fm~=nil)..
                          ' chooser_present='..tostring(chooser~=nil)..
                          ' chooser_path_kind='..pathkind..
                          ' stack_depth='..tostring(depth)..
                          ' fm_stack_index='..tostring(idx)..
                          ' top_widget_present='..tostring(top~=nil)..
                          ' top_is_fm='..tostring(fm~=nil and top==fm)..
                          ' top_is_second_reader='..tostring(top~=nil and top==r39_saved_reader)..
                          ' top_is_first_reader='..tostring(top~=nil and top==r394_first_reader)..
                          ' denied_zero='..tostring(stats.denied==0))
                    -- R39.4.3 read-only count, after the existing R39.4.2 state.
                    -- The original strict assertion below is STILL unchanged.
                    print('R39_4_3_DENIAL_SUMMARY count='..tostring(stats.denied))
                    -- Preserve the original R39.4 strict assertion unmodified.
                    fm=assert(module.instance,'R39.4 second returned FM missing')
                    assert(fm.file_chooser and fm.file_chooser.path==home..'/library' and
                           real_ui._window_stack[#real_ui._window_stack].widget==fm and
                           stats.denied==0,'R39.4 second FileManager not active')
                    r394_second_home_returned=true
                    stats.filemanager=3
                    stats.owner=3
                    print('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY')
                    print('R39_4_SECOND_GENUINE_FILEMANAGER_RETURNED_AFTER_HOME')
                    return result
                end
                -- R39.3.1: observe the genuine Home->FM handoff BEFORE the
                -- unchanged strict closure assertion. No object is changed.
                -- Original R39.3 failed this compound predicate; the log could
                -- not reveal whether ReaderUI, document, engine or registry
                -- refcount was responsible. This snapshot does not waive it.
                assert(r3931_home_snapshot_count==0,
                       'R39.3.1 duplicate Home close snapshot')
                r3931_home_snapshot_count=1
                local registry=package.loaded['document/documentregistry']
                local refcount='unavailable'
                if registry and type(registry.getReferenceCount)=='function' then
                    local n=registry:getReferenceCount(r39_pdf)
                    if n==nil then refcount='none'
                    elseif type(n)=='number' and n>=0 and n==math.floor(n) and n<100000 then
                        refcount=tostring(n)
                    else refcount='invalid' end
                end
                local reader_instance_nil=(native_require('apps/reader/readerui').instance==nil)
                local reader_document_nil=(r39_saved_reader~=nil and r39_saved_reader.document==nil)
                local document_present=(r39_saved_doc~=nil)
                local doc_is_open=document_present and tostring(r39_saved_doc.is_open) or 'absent'
                local engine_nil=document_present and r39_saved_doc._document==nil
                local raw_engine_nil=document_present and rawget(r39_saved_doc,'_document')==nil
                local inherited_engine_false=document_present and r39_saved_doc._document==false
                print('R39_3_1_HOME_CLOSE_STATE reader_instance_nil='..tostring(reader_instance_nil)..
                      ' reader_document_nil='..tostring(reader_document_nil)..
                      ' document_present='..tostring(document_present)..
                      ' doc_is_open='..doc_is_open..
                      ' engine_nil='..tostring(engine_nil)..
                      ' registry_refs='..refcount..
                      ' filemanager_instance_nil='..tostring(module.instance==nil))
                -- R39.3.3: the old R39.3.1 engine_nil value uses inherited lookup.
                -- Record the *raw instance slot* and the inherited false sentinel.
                -- Emit BEFORE any success assertion; the real FileManager is still absent.
                assert(r3933_home_sentinel_count==0,'R39.3.3 duplicate sentinel')
                r3933_home_sentinel_count=1
                print('R39_3_3_HOME_ENGINE_SENTINEL raw_engine_nil='..tostring(raw_engine_nil)..
                      ' inherited_engine_false='..tostring(inherited_engine_false)..
                      ' registry_refs='..refcount..
                      ' doc_is_open='..doc_is_open..
                      ' reader_instance_nil='..tostring(reader_instance_nil)..
                      ' reader_document_nil='..tostring(reader_document_nil)..
                      ' filemanager_instance_nil='..tostring(module.instance==nil))
                -- Retain all original reader/UI checks; independently require
                -- a genuinely closed raw engine and zero registry ownership.
                assert(raw_engine_nil and inherited_engine_false and refcount=='none' and
                       r3933_pdf_engine_released() and
                       reader_instance_nil and reader_document_nil and
                       module.instance==nil,
                       'R39.3.3 raw engine or registry or reader handoff not released')
                -- Keep the original R39.3 strict fail-closed lifecycle gate,
                -- correcting only inherited `_document` lookup semantics.
                assert(native_require('apps/reader/readerui').instance==nil and
                       r39_saved_reader and r39_saved_reader.document==nil and
                       r3933_pdf_engine_released(),
                       'R39.3 ReaderUI document not genuinely closed before FM return')
                local result=stock_show(self,path,...)
                local fm=assert(module.instance,'R39.3 genuine FileManager absent on Home')
                assert(fm.file_chooser and fm.file_chooser.path==home..'/library' and
                       real_ui._window_stack[#real_ui._window_stack].widget==fm,
                       'R39.3 returned FileManager not active/temporary')
                assert(stats.denied==0,'R39.3 forbidden operation during onHome')
                r39_home_returned=true
                stats.filemanager=2
                stats.owner=2
                print('R39_3_GENUINE_FILEMANAGER_RETURNED_AFTER_HOME')
                return result
            end
            assert(self==module and path==home..'/library' and stats.filemanager==0,
                   'unexpected startup path or duplicated FileManager')
            local result=stock_show(self,path,...)
            local fm=assert(module.instance,'genuine FileManager instance absent')
            assert(fm.file_chooser and fm.file_chooser.path==path,
                   'real FileChooser not on temporary directory')
            assert(real_ui._window_stack[1] and real_ui._window_stack[1].widget==fm,
                   'FileManager not owned by real UIManager')
            assert(stats.discovery==1 and stats.plugin_main==1 and stats.plugin_meta==1 and stats.screen_scale>0,
                   'unexpected plugin execution scope')
            local plugin=assert(real_loader:getPluginInstance('ink-away'),
                                'Ink Away instance missing')
            assert(fm['ink-away']==plugin and plugin.ui==fm,
                   'Ink Away not owned by genuine FileManager')
            assert(type(plugin.openCanvas)=='function' and type(plugin.addToMainMenu)=='function')
            local enabled,disabled=real_loader:loadPlugins()
            assert(#enabled==1 and enabled[1].name=='ink-away' and #disabled==0,
                   'unexpected enabled/disabled plugins')
            stats.filemanager=stats.filemanager+1
            stats.owner=stats.owner+1
            print('R24_REAL_FILEMANAGER_SHOWFILES')
            print('R24_INKAWAY_INSTANCE_OWNED_BY_FILEMANAGER')
            return result
        end
    elseif name=='document/canvascontext' and not stats.canvas_installed then
        stats.canvas_installed=true
        local genuine=module.init
        assert(type(genuine)=='function')
        module.init=function(self,dev,...)
            assert(dev.model=='R17StandalonePW3Synthetic')
            stats.canvas=stats.canvas+1
            local result=genuine(self,dev,...)
            return result
        end
    end
    -- Observe, never substitute, the real PDF paint path. For a PDF, genuine
    -- ReaderView:paintTo() -> drawSinglePage() does not set state.drawn.
    -- Only a successful return from the original staged renderer counts.
    if name=='apps/reader/modules/readerview' and not stats.r39_readerview_observed then
        local original=assert(module.drawSinglePage)
        local original_info=debug.getinfo(original,'S')
        assert(original_info and type(original_info.source)=='string' and
               original_info.source:find('frontend/apps/reader/modules/readerview%.lua'),
               'R39.2.1 original genuine ReaderView:drawSinglePage required')
        stats.r39_readerview_observed=true
        local original_paint=assert(module.paintTo)
        local paint_info=debug.getinfo(original_paint,'S')
        assert(paint_info and paint_info.source:find('frontend/apps/reader/modules/readerview%.lua'),
               'R39.2.3 genuine ReaderView:paintTo required')
        module.paintTo=function(self,bb,x,y)
            local reader=diag_reader()
            local capture=reader~=nil and self==reader.view and r39_diag.view_paints<6
            if capture then
                r39_diag.view_paints=r39_diag.view_paints+1
                print('R39_2_3_READERVIEW_PAINT n='..r39_diag.view_paints..
                      ' paging='..tostring(self.ui.paging~=nil)..
                      ' scroll='..tostring(self.page_scroll==true)..
                      ' page='..tostring(self.state and self.state.page)..
                      ' bb='..tostring(bb~=nil))
            end
            return original_paint(self,bb,x,y)
        end
        -- R39.2.4: actual user diagnostic proved paging=true, page_scroll=true.
        -- In this mode ReaderView:paintTo invokes drawScrollPages (source line
        -- 196), never drawSinglePage. Exact pinned source loops through each
        -- page_state and calls the genuine document:drawPage with state.page.
        -- Count only after that genuine whole scroll-paint call returns.
        local original_scroll=assert(module.drawScrollPages)
        local scroll_info=debug.getinfo(original_scroll,'S')
        assert(scroll_info and type(scroll_info.source)=='string' and
               scroll_info.source:find('frontend/apps/reader/modules/readerview%.lua'),
               'R39.2.4 pinned genuine ReaderView:drawScrollPages required')
        module.drawScrollPages=function(self,bb,x,y)
            local caller=debug.getinfo(2,'Sl')
            assert(caller and type(caller.source)=='string' and
                   caller.source:find('frontend/apps/reader/modules/readerview%.lua') and
                   caller.currentline==196,
                   'R39.2.4 scroll draw only from genuine ReaderView:paintTo')
            local reader=assert(diag_reader(),'R39.2.4 no real ReaderUI during scroll draw')
            assert(reader.view==self and self.ui==reader and self.ui.paging and
                   self.page_scroll==true and reader.document and
                   reader.document.file==r39_pdf and reader.document.is_pdf and
                   reader.document.is_open and reader.document:getPageCount()==2 and bb~=nil,
                   'R39.2.4 PDF scroll paint owner/fixture/buffer mismatch')
            local selected=reader.paging.current_page
            assert(self.state and self.state.page==selected and
                   ((r394_cycle==2 and (selected==1 or selected==2) and
                     (stats.events==2 or stats.events==3)) or
                    (r394_cycle==1 and selected==(stats.events==0 and 1 or 2))),
                   'R39.2.4 scroll paint selected page/phase mismatch')
            local states=assert(self.page_states,'R39.2.4 page_states missing')
            assert(#states>=1 and #states<=4,'R39.2.4 unbounded/empty scroll page states')
            local snapshot={}
            local visible=false
            for i, st in ipairs(states) do
                assert(type(st)=='table' and (st.page==1 or st.page==2) and
                       st.visible_area and st.offset and st.zoom,
                       'R39.2.4 invalid scroll-page state')
                snapshot[i]=st.page
                if st.page==selected then visible=true end
            end
            assert(visible,'R39.2.4 selected page not in real scroll page states')
            -- Original upstream code calls document:drawPage for each state.
            -- A normal return proves it traversed all those genuine calls.
            local result=original_scroll(self,bb,x,y)
            assert(self.page_states==states and #states==#snapshot,
                   'R39.2.4 scroll page states replaced during paint')
            for i, page in ipairs(snapshot) do
                assert(states[i].page==page,'R39.2.4 scroll page state changed during paint')
            end
            r39_real_pdf_draws[selected]=r39_real_pdf_draws[selected]+1
            assert(r39_real_pdf_draws[selected]<=24,'R39.2.4 unbounded scroll PDF paints')
            if not r39_draw_marker_emitted[selected] then
                r39_draw_marker_emitted[selected]=true
                if r394_cycle==2 then
                    r394_second_scroll_returned=true
                    r394_second_initial_page=selected
                    print('R39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED page='..selected)
                elseif selected==1 then
                    assert(stats.events==0,'R39.2.4 first-page scroll draw after GotoPage')
                    print('R39_2_1_GENUINE_MUPDF_PAGE1_DRAW_COMPLETED')
                    print('R39_2_4_GENUINE_SCROLL_PAGE1_DRAW_RETURNED')
                else
                    assert(stats.events==1 and r39_page1_verified,
                           'R39.2.4 page2 scroll draw before genuine input event')
                    print('R39_2_1_GENUINE_MUPDF_PAGE2_DRAW_COMPLETED')
                    print('R39_2_4_GENUINE_SCROLL_PAGE2_DRAW_RETURNED')
                end
            end
            return result
        end
        module.drawSinglePage=function(self,bb,x,y)
            local caller=debug.getinfo(2,'Sl')
            assert(caller and type(caller.source)=='string' and
                   caller.source:find('frontend/apps/reader/modules/readerview%.lua') and
                   caller.currentline==198,
                   'R39.2.1 draw only from genuine ReaderView:paintTo')
            local ReaderUI=native_require('apps/reader/readerui')
            local reader=assert(ReaderUI.instance,'no genuine ReaderUI during PDF draw')
            assert(reader.view==self and self.ui==reader and self.ui.paging and
                   reader.document and reader.document.file==r39_pdf and
                   reader.document.is_pdf and reader.document.is_open and
                   reader.document:getPageCount()==2 and bb~=nil,
                   'R39.2.2 PDF paint instance or original memory buffer mismatch')
            local page=self.state.page
            assert(page==1 or page==2,'R39.2.1 unexpected PDF page draw')
            assert(reader.paging.current_page==page,
                   'R39.2.1 ReaderPaging and rendered page mismatch')
            -- DO NOT use self.state.drawn for PDFs; true is assigned only in
            -- the non-paging/CRE branch of genuine ReaderView:paintTo.
            local result=original(self,bb,x,y)
            r39_real_pdf_draws[page]=r39_real_pdf_draws[page]+1
            assert(r39_real_pdf_draws[page]<=24,'R39.2.1 unbounded PDF repaints')
            if not r39_draw_marker_emitted[page] then
                r39_draw_marker_emitted[page]=true
                if r394_cycle==2 then
                    print('R39_4_SECOND_GENUINE_PDF_SINGLE_DRAW_RETURNED page='..page)
                elseif page==1 then
                    print('R39_2_1_GENUINE_MUPDF_PAGE1_DRAW_COMPLETED')
                else
                    assert(stats.events==1 and r39_page1_verified,
                           'R39.2.1 page2 drawn before genuine GotoPage input')
                    print('R39_2_1_GENUINE_MUPDF_PAGE2_DRAW_COMPLETED')
                end
            end
            return result
        end
    end
    return module
end
-- Import the synthetic class only when reader.lua itself reaches require('device').
-- The stock device selector would probe physical hardware, so it is never called.
package.preload['device']=function()
    assert(stats.settings==1,'reader.lua must open real temporary LuaSettings first')
    local Device=native_require('standalone_pw3_r17').new_synthetic()
    local Generic=native_require('device/generic/device')
    assert(Device.init==Generic.init and Device._UIManagerReady==Generic._UIManagerReady,
           'genuine generic device lifecycle required')
    assert(Device.input and Device.input.is_synthetic and Device.input.UIManagerReady==nil,
           'expected R17 synthetic input with no native UIManager callback')
    assert(Device.powerd and type(Device.powerd.UIManagerReady)=='function',
           'genuine synthetic power manager UIManager callback required')
    -- KOReader's genuine Generic:_UIManagerReady() invokes input:UIManagerReady(uimgr).
    -- R18 provided this on its own fake input instance; R23.3 did not.
    -- Attach ONLY to this in-memory input instance, never to the device or stock code.
    local screen=Device.screen
    assert(screen and type(screen.getBB)=='function' and screen.dpi==300
           and screen.w==1072 and screen.h==1448 and screen.buffer,
           'only the established R17 in-memory 300-DPI screen is supported')
    -- This is the exact R19.2 synthetic geometry API used by the previous
    -- CanvasContext probe.  It never loads a real framebuffer or /dev node.
    function screen:getDPI() assert(self==screen); return self.dpi end
    function screen:getSize() assert(self==screen); return {x=0,y=0,w=self.w,h=self.h} end
    function screen:isColorEnabled() assert(self==screen); return false end
    function screen:scaleBySize(n)
        assert(self==screen and type(n)=='number' and n==n and n>=0,
               'invalid synthetic screen scaling request')
        if stats.screen_scale==0 then
            local origin=debug.getinfo(2,'S')
            assert(origin and type(origin.source)=='string' and
                   origin.source:find('frontend/ui/size%.lua'),
                   'the first screen scaling call must come from genuine ui/size.lua')
            assert(stats.uimanager==1 and stats.migrations==1 and stats.bidi==1,
                   'UI size scaling reached outside the expected startup boundary')
            print('R24_GENUINE_UI_SIZE_CALLED_SYNTHETIC_SCALING')
        end
        stats.screen_scale=stats.screen_scale+1
        return math.max(1,math.floor(n*self.dpi/167+0.5))
    end
    screen.scaleByDPI=screen.scaleBySize
    screen.fb_bpp=8
    screen.bb=screen:getBB()
    function screen:beforePaint() end
    function screen:afterPaint() end
    function screen:refreshWaitForLast() return true end
    local function memory_refresh(self,...) return self:refreshFull(...) end
    for _,key in ipairs({'refreshA2','refreshFast','refreshUI','refreshPartial',
        'refreshNoMergeUI','refreshNoMergePartial','refreshFlashUI','refreshFlashPartial'}) do
        screen[key]=memory_refresh
    end
    local expected_input=Device.input
    function expected_input:UIManagerReady(uimgr)
        assert(self==expected_input and self.is_synthetic,
               'unexpected non-synthetic input callback owner')
        assert(stats.bidi==1 and stats.migrations==1 and stats.input_ready==0,
               'unexpected or repeated synthetic input handshake')
        assert(type(uimgr)=='table' and type(uimgr.run)=='function'
               and debug.getinfo(uimgr.run,'S').source:find('frontend/ui/uimanager%.lua'),
               'real KOReader UIManager must notify synthetic input')
        self.ui_ready=true
        stats.input_ready=1
        print('R23_SYNTHETIC_INPUT_UIMANAGER_READY')
    end
    -- R39.0 user ARM failure: genuine ReaderUI:init (line 120) calls
    -- Input:inhibitInput(true); the R17 synthetic input did not supply it.
    -- ReaderUI:init success (line 533) and exception recovery (730, 922)
    -- also call Input:inhibitInputUntil(0.2). These are NOT hardware APIs.
    -- No native evdev device is opened; the bounded synthetic event provider
    -- stays inert until ReaderUI's genuine coroutine reaches completion.
    assert(expected_input.inhibitInput==nil and expected_input.inhibitInputUntil==nil,
           'unexpected preexisting synthetic Input inhibition overrides')
    local function genuine_readerui_call(allowed)
        local caller=debug.getinfo(3,'Sl')
        assert(caller and type(caller.source)=='string' and
               caller.source:find('frontend/apps/reader/readerui%.lua') and
               allowed[caller.currentline],
               'R39 synthetic Input lifecycle call outside genuine pinned ReaderUI source')
        return caller.currentline
    end
    function expected_input:inhibitInput(enabled)
        assert(self==expected_input and self.is_synthetic and enabled==true,
               'R39 only genuine ReaderUI:init Input:inhibitInput(true) allowed')
        genuine_readerui_call({[120]=true})
        -- R39.4.1: R39.4 previously reused a first-open-only guard. After
        -- genuine Home restores FileManager, that singleton is the *second*
        -- genuine FileManager and the second ReaderUI invokes this same API.
        -- Allow ONLY these two exact, ordered synthetic ReaderUI lifecycle
        -- phases; do not replace ReaderUI or loosen hardware/input denials.
        local first_reader_init=(r394_cycle==1 and stats.filemanager==1 and
                                 stats.events==0 and r394_input_lifecycles==0 and
                                 not r39_home_sent)
        local second_reader_init=(r394_cycle==2 and stats.filemanager==2 and
                                  stats.events==2 and r394_input_lifecycles==1 and
                                  r39_home_returned and r394_first_reader~=nil and
                                  r394_first_doc~=nil and
                                  r394_first_doc.is_open==false and
                                  rawget(r394_first_doc,'_document')==nil and
                                  r394_first_doc._document==false and
                                  real_fm~=nil and real_fm.instance==nil)
        assert((first_reader_init or second_reader_init) and
               r39_input_inhibit==0 and r39_input_until==0 and
               self._r39_readerui_inhibited~=true,
               'R39.4.1 genuine ReaderUI Input lifecycle out of phase')
        r39_input_inhibit=1
        r394_input_lifecycles=r394_input_lifecycles+1
        assert(r394_input_lifecycles==r394_cycle,'R39.4 duplicate ReaderUI input lifecycle')
        self._r39_readerui_inhibited=true
        print('R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY')
        return true
    end
    function expected_input:inhibitInputUntil(seconds)
        assert(self==expected_input and self.is_synthetic and seconds==0.2,
               'R39 only genuine ReaderUI Input:inhibitInputUntil(0.2) allowed')
        local line=genuine_readerui_call({[533]=true,[730]=true,[922]=true})
        -- The matching release must belong to the currently active, audited
        -- genuine ReaderUI:init; an extra/late release cannot consume phase 2.
        assert(r394_input_lifecycles==r394_cycle and
               r39_input_inhibit==1 and r39_input_until==0 and
               self._r39_readerui_inhibited==true,
               'R39.4.1 timed Input release outside active ReaderUI construction')
        r39_input_until=1
        self._r39_readerui_inhibited=false
        self._r39_inhibit_release_from=line
        if line==533 then
            print('R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY')
        else
            -- Original genuine coroutine exception path remains a strict FAIL.
            print('R39_1_READERUI_COROUTINE_RECOVERY_INPUT_RELEASE_ONLY')
        end
        return true
    end
    -- R39.2: exactly two genuine UIManager input polls: GotoPage(2), then Close.
    -- Do not replace ReaderPaging handlers or assign its page state directly.
    function expected_input:waitEvent(now,deadline)
        r39_input_poll_count=r39_input_poll_count+1
        assert(self==expected_input and self.ui_ready and stats.filemanager>=1 and stats.filemanager<=3
               and stats.loop<=1 and stats.events<=4 and r39_input_poll_count<=8,
               'R39.2.2 unbounded/extra synthetic input poll')
        local origin=debug.getinfo(2,'Sl')
        assert(origin and type(origin.source)=='string' and
               origin.source:find('frontend/ui/uimanager%.lua'),
               'R39.2 synthetic event must be requested by genuine UIManager')
        local Event=native_require('ui/event')
        local ReaderUI=native_require('apps/reader/readerui')
        if stats.events==3 and r394_cycle==2 then
            assert(r394_second_home_sent and r394_second_home_returned and
                   stats.filemanager==3 and ReaderUI.instance==nil and
                   real_fm and real_fm.instance and r394_second_scroll_returned and
                   r39_saved_doc~=r394_first_doc and r3933_pdf_engine_released(),
                   'R39.4 second Home close and returned FM required')
            local fm=real_fm.instance
            assert(fm.file_chooser and fm.file_chooser.path==home..'/library' and
                   real_ui._window_stack[#real_ui._window_stack].widget==fm and
                   stats.denied==0,'R39.4 final FileManager not active')
            stats.events=4
            print('R39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER')
            return {Event:new('Close')}
        end
        if stats.events==2 and r394_cycle==2 then
            local reader=ReaderUI.instance
            assert(reader and reader~=r394_first_reader and reader.document and
                   reader.document~=r394_first_doc and reader.document.file==r39_pdf and
                   reader.document.is_pdf and reader.document.is_open and
                   reader.document:getPageCount()==2 and stats.filemanager==2 and
                   real_fm and real_fm.instance==nil and
                   real_ui._window_stack[#real_ui._window_stack].widget==reader and
                   r39_input_inhibit==1 and r39_input_until==1 and
                   expected_input._r39_inhibit_release_from==533,
                   'R39.4 genuinely reinitialized distinct ReaderUI/PDF')
            local selected=reader.paging.current_page
            assert((selected==1 or selected==2) and reader.view.state.page==selected,
                   'R39.4 second reader page state inconsistent')
            if not r394_second_scroll_returned then
                assert(r39_bounded_repaint_requests[selected]==0,
                       'R39.4 second PDF failed genuine repaint')
                r39_bounded_repaint_requests[selected]=1
                assert(debug.getinfo(real_ui.setDirty,'S').source:find('frontend/ui/uimanager%.lua'),
                       'R39.4 must use genuine UIManager:setDirty')
                real_ui:setDirty(reader,'full')
                print('R39_4_SECOND_BOUNDED_REAL_UIMANAGER_REPAINT_REQUESTED')
                return nil
            end
            assert(r394_second_initial_page==selected and r39_real_pdf_draws[selected]>=1,
                   'R39.4 second ReaderView scroll draw not observed')
            r39_saved_doc=reader.document
            r39_saved_reader=reader
            assert(reader.doc_settings and reader.doc_settings.doc_sidecar_dir and
                   reader.doc_settings.sidecar_filename and
                   in_home(reader.doc_settings.doc_sidecar_dir..'/'..reader.doc_settings.sidecar_filename),
                   'R39.4 second per-book settings escaped temporary home')
            print('R39_4_DISTINCT_READERUI_AND_PDF_DOCUMENT_REOPENED')
            stats.events=3
            r394_second_home_sent=true
            print('R39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT')
            return {Event:new('Home')}
        end
        if stats.events==2 then
            assert(r39_home_sent and r39_home_returned and stats.filemanager==2 and
                   ReaderUI.instance==nil and real_fm and real_fm.instance and
                   r39_saved_reader and r39_saved_reader.document==nil and
                   r3933_pdf_engine_released() and r39_page2_verified and
                   r3933_home_sentinel_count==1,
                   'R39.3 real ReaderUI close/document release/FM return missing')
            local fm=real_fm.instance
            assert(fm.file_chooser and fm.file_chooser.path==home..'/library' and
                   real_ui._window_stack[#real_ui._window_stack].widget==fm and
                   stats.denied==0,
                   'R39.3 FileManager is not active after Home')
            print('R39_3_GENUINE_DOCUMENT_CLOSED_AND_READERUI_INSTANCE_RELEASED')
            print('R39_3_FILEMANAGER_ACTIVE_AFTER_HOME')
            r394_first_doc=r39_saved_doc
            r394_first_reader=r39_saved_reader
            r394_first_draws={[1]=r39_real_pdf_draws[1],[2]=r39_real_pdf_draws[2]}
            assert(r394_first_draws[1]>=1 and r394_first_draws[2]>=1,
                   'R39.4 first cycle PDF paints missing')
            r394_cycle=2
            r39_saved_doc=nil
            r39_saved_reader=nil
            r39_real_pdf_draws={[1]=0,[2]=0}
            r39_draw_marker_emitted={[1]=false,[2]=false}
            r39_bounded_repaint_requests={[1]=0,[2]=0}
            r39_input_inhibit=0
            r39_input_until=0
            local original_open=assert(fm.openFile,'R39.4 authentic FM reopen required')
            assert(debug.getinfo(original_open,'S').source:find('frontend/apps/filemanager/filemanager%.lua'),
                   'R39.4 original FileManager:openFile provenance mismatch')
            print('R39_4_REOPEN_REQUESTED_FROM_RETURNED_FILEMANAGER')
            fm:openFile(r39_pdf)
            assert(real_fm.instance==nil and ReaderUI.instance==nil,
                   'R39.4 reopen must close FM and schedule async ReaderUI')
            print('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED')
            return nil
        end
        local reader=ReaderUI.instance
        assert(r39_input_inhibit==1 and r39_input_until==1 and
               expected_input._r39_readerui_inhibited==false and
               expected_input._r39_inhibit_release_from==533,
               'R39.2 genuine ReaderUI must complete audited Input lifecycle')
        assert(reader and reader.document and reader.document.file==r39_pdf and
               reader.document.is_pdf and reader.document.is_open and
               reader.document:getPageCount()==2,
               'R39.2 genuine ReaderUI/two-page PDF lost')
        assert(reader.paging and type(reader.paging.onGotoPage)=='function' and
               debug.getinfo(reader.paging.onGotoPage,'S').source:find(
                 'frontend/apps/reader/modules/readerpaging%.lua'),
               'R39.2 genuine ReaderPaging onGotoPage required')
        assert(real_fm and real_fm.instance==nil and
               real_ui._window_stack[#real_ui._window_stack] and
               real_ui._window_stack[#real_ui._window_stack].widget==reader,
               'R39.2 ReaderUI must own active UI stack')
        assert(reader.view and type(reader.view.state)=='table',
               'R39.2 genuine ReaderView state missing')
        print('R39_2_3_INPUT_POLL poll='..r39_input_poll_count..
              ' phase='..stats.events..' dirty='..tostring(real_ui._dirty[reader]~=nil)..
              ' repaints='..r39_diag.repaints..' dirty_entries='..r39_diag.reader_dirty_entries..
              ' container='..r39_diag.container_paints..' view='..r39_diag.view_paints..
              ' draws1='..r39_real_pdf_draws[1]..' draws2='..r39_real_pdf_draws[2])
        if stats.events==0 then
            assert(reader.paging.current_page==1 and reader.view.state.page==1,
                   'R39.2 document must start on page 1')
            -- A real ReaderUI instance may be visible at the input boundary
            -- before its first PDF paint has occurred. A single bounded
            -- real-UIManager repaint is permitted; never invent paint evidence.
            if r39_real_pdf_draws[1]==0 then
                assert(r39_bounded_repaint_requests[1]==0,
                       'R39.2.2 page1 genuine PDF paint still missing after real UIManager repaint')
                assert(real_ui and type(real_ui.setDirty)=='function' and
                       debug.getinfo(real_ui.setDirty,'S').source:find('frontend/ui/uimanager%.lua'),
                       'R39.2.2 real UIManager:setDirty required')
                r39_bounded_repaint_requests[1]=1
                real_ui:setDirty(reader,'full')
                print('R39_2_2_BOUNDED_REAL_UIMANAGER_REPAINT_REQUESTED_PAGE1')
                return nil -- no input event; genuine UIManager next repaint pass
            end
            assert(r39_real_pdf_draws[1]>=1 and r39_real_pdf_draws[2]==0,
                   'R39.2.2 first page must finish real MuPDF draw before event')
            r39_reader_seen=true
            r39_page1_verified=true
            print('R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED')
            print('R39_REAL_UIMANAGER_LOOP_AFTER_READERUI_NEXTTICK')
            print('R39_2_READER_PAGE1_DRAWN_AND_CURRENT_PAGE_VERIFIED')
            stats.events=1
            stats.loop=1
            print('R39_2_GOTOPAGE2_SENT_THROUGH_REAL_UIMANAGER_INPUT')
            return {Event:new('GotoPage',2)}
        end
        assert(stats.events==1 and r39_reader_seen and r39_page1_verified and
               reader.paging.current_page==2 and reader.view.state.page==2,
               'R39.2 real ReaderPaging/ReaderView page 2 state missing')
        if r39_real_pdf_draws[2]==0 then
            assert(r39_bounded_repaint_requests[2]==0,
                   'R39.2.2 page2 genuine PDF paint still missing after real UIManager repaint')
            assert(real_ui and type(real_ui.setDirty)=='function' and
                   debug.getinfo(real_ui.setDirty,'S').source:find('frontend/ui/uimanager%.lua'),
                   'R39.2.2 real UIManager:setDirty required')
            r39_bounded_repaint_requests[2]=1
            real_ui:setDirty(reader,'full')
            print('R39_2_2_BOUNDED_REAL_UIMANAGER_REPAINT_REQUESTED_PAGE2')
            return nil
        end
        assert(r39_real_pdf_draws[2]>=1,
               'R39.2.2 second page must finish real MuPDF draw before Close')
        stats.events=2
        r39_page2_verified=true
        print('R39_2_READER_PAGE2_DRAWN_AND_CURRENT_PAGE_VERIFIED')
        assert(not r39_home_sent and reader.document and reader.document.is_open and
               reader.doc_settings and reader.doc_settings.doc_sidecar_dir and
               reader.doc_settings.sidecar_filename and
               in_home(reader.doc_settings.doc_sidecar_dir..'/'..reader.doc_settings.sidecar_filename),
               'R39.3 ReaderUI per-book metadata must stay in disposable home')
        r39_saved_settings_file=reader.doc_settings.doc_sidecar_dir..'/'..reader.doc_settings.sidecar_filename
        r39_saved_doc=reader.document
        r39_saved_reader=reader
        r39_home_sent=true
        print('R39_3_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT')
        return {Event:new('Home')}
    end
    function expected_input:teardown()
        assert(self==expected_input and stats.events==4 and r39_page2_verified and
               r39_home_returned and r394_second_home_returned and
               r39_input_poll_count>=4 and r39_input_poll_count<=8 and
               r394_first_draws and r394_first_draws[1]>=1 and r394_first_draws[2]>=1 and
               r394_second_scroll_returned,
               'invalid R39.2 synthetic teardown')
        self.teardown_done=true
    end
    function screen:setHWNightmode(_) return true end
    function screen:close() self.closed=true; return true end
    -- Preserve genuine Generic:exit(): missing methods are added to *instances*.
    local stock_exit=Generic.exit
    assert(type(stock_exit)=='function' and
           debug.getinfo(stock_exit,'S').source:find('frontend/device/generic/device%.lua'))
    Device.exit=function(self,...)
        assert(self==Device and stats.events==4 and r39_page2_verified and r39_home_returned and
               r394_second_home_returned and stats.device_exit==0,
               'unexpected synthetic device shutdown')
        local value=stock_exit(self,...)
        assert(screen.closed and expected_input.teardown_done,
               'genuine Generic:exit() did not release synthetic screen/input')
        stats.device_exit=1
        print('R39_REAL_GENERIC_EXIT_SYNTHETIC_ONLY')
        return value
    end
    Device:init() -- real Generic:init, memory-backed screen and fake input
    stats.device=stats.device+1
    print('R23_REAL_GENERIC_INIT_SYNTHETIC_ONLY')
    return Device
end
-- LuaDefaults:open() and LuaSettings:open() use dofile even to try absent
-- optional settings files, via pcall. Only the official, staged defaults.lua
-- and four narrowly scoped temporary settings filenames may reach native_dofile.
-- The migration script, external user patches, and every other Lua source stay blocked.
local function is_optional_temp_settings_file(path)
    return path==home..'/defaults.custom.lua'
        or path==home..'/defaults.custom.lua.old'
        or path==home..'/settings.reader.lua'
        or path==home..'/settings.reader.lua.old'
end
-- Match the genuine reader.lua migration call but NEVER execute the script.
-- This is an explicit skip (not migration verification) for the post-migration
-- *source position*, to exercise genuine Bidi and UIManager imports next.
dofile=function(path)
    if path=='defaults.lua' then
        assert(stats.setup==1 and stats.defaults==0,
               'unexpected or repeated original defaults.lua load')
        local defaults=native_dofile(path) -- exact allowlisted staged application source
        assert(type(defaults)=='table' and defaults.DHINTCOUNT==1,
               'staged defaults.lua failed its read-only contents contract')
        stats.defaults=1
        print('R23_REAL_DEFAULTS_LOADED_READ_ONLY')
        return defaults
    end
    if is_optional_temp_settings_file(path) then
        -- A missing optional file should raise the native file-not-found error.
        -- LuaSettings and LuaDefaults catch it via pcall and use empty defaults.
        return native_dofile(path)
    end
    if path==home..'/settings/collection.lua'
        or path==home..'/settings/collection.lua.old' then
        assert(stats.collection_reads>0,
               'collection settings file may only be checked after trusted open')
        return native_dofile(path)
    end
    if path==ink_root..'/main.lua' or path==ink_root..'/_meta.lua' then
        assert(stats.plugin_installed and stats.discovery>=1 and stats.discovery<=3,
               'plugin source outside bounded FileManager/ReaderUI discovery')
        -- Allow at most one renewed Ink Away import, *after* the real FM closes.
        -- Keep the original first-load ordering, never load a third instance.
        if stats.discovery>=2 then
            assert(real_fm and real_fm.instance==nil,
                   'second plugin source load before FileManager closed')
        end
        if path==ink_root..'/main.lua' then
            assert(stats.plugin_main==stats.discovery-1 and
                   stats.plugin_meta==stats.discovery-1,
                   'plugin main repeated or loaded out of order')
            stats.plugin_main=stats.plugin_main+1
        else
            assert(stats.plugin_main==stats.discovery and
                   stats.plugin_meta==stats.discovery-1,
                   'plugin meta repeated or loaded before plugin main')
            stats.plugin_meta=stats.plugin_meta+1
        end
        return native_dofile(path)
    end
    if path=='frontend/ui/data/onetime_migration.lua' then
        stats.migrations=stats.migrations+1
        assert(stats.setup==1 and stats.defaults==1 and stats.settings==1 and stats.device==1
            and stats.canvas==1 and stats.version==1 and stats.patches==2,
            'reader.lua did not reach migration in expected startup order')
        print('R23_READER_REAL_PREMIGRATION_ORDER_CONFIRMED')
        print('R23_MIGRATIONS_SKIPPED_IN_SYNTHETIC_TEST')
        return nil -- Never call native_dofile(path) here. No migration effects.
    end
    -- R39.4.4: first DOFILE-denial target & genuine immediate caller,
    -- without revealing or reading a path, executing Lua, or changing deny().
    -- A path can ONLY be named as the expected sidecar by exact equality.
    if stats.denied==0 then
        local kind='outside_or_unknown'
        if type(path)=='string' then
            if path==home..'/library/r39-original-two-pages.sdr/metadata.pdf.lua' then
                kind='exact_pdf_sidecar'
            elseif path==home..'/library/r39-original-two-pages.sdr/metadata.pdf.lua.old' then
                kind='exact_pdf_sidecar_backup'
            elseif path==r39_pdf..'.kpdfview.lua' then
                kind='exact_pdf_legacy'
            elseif in_home(path) then
                kind='other_temp_home'
            elseif protected(path) then
                kind='protected_target'
            end
        end
        -- In a dofile global replacement, level 2 is the *genuine consumer*.
        -- Unlike the R39.4.3 denial_site() multi-frame probe, this does not
        -- walk through deny() and must not expose arbitrary source paths.
        local origin=debug.getinfo(2,'Sl')
        local caller='other'
        local source=origin and origin.source or ''
        if type(source)=='string' then
            if source:match('^@?frontend/docsettings%.lua$') or
               source:match('^@?/stage/rootfs/opt/koreader%-compat/app/frontend/docsettings%.lua$') then
                caller='docsettings'
            elseif source:match('^@?frontend/luasettings%.lua$') or
                   source:match('^@?/stage/rootfs/opt/koreader%-compat/app/frontend/luasettings%.lua$') then
                caller='luasettings'
            elseif source:match('^@?frontend/document/documentregistry%.lua$') then
                caller='documentregistry'
            end
        end
        local line=origin and origin.currentline or 0
        if caller=='other' or type(line)~='number' or line<0 or line>100000 then line=0 end
        print('R39_4_4_DOFILE_TARGET path_kind='..kind..
              ' caller_kind='..caller..' line='..math.floor(line)..
              ' cycle='..r394_cycle..' events='..stats.events..
              ' filemanagers='..stats.filemanager)
    end
    -- R39.4.5: only permit the exact *newly generated* synthetic sidecar,
    -- through the upstream DocSettings:open -> C pcall -> dofile call chain.
    -- Inspect function identity, not source-name text alone. Other requests
    -- retain the original DOFILE denial, counter and exception unchanged.
    if path==r3945_sidecar then
        local frame2=debug.getinfo(2,'Sf')
        local frame3=debug.getinfo(3,'Slf')
        local docsettings=package.loaded['docsettings']
        local from_c_pcall=frame2 and frame2.what=='C' and frame2.func==pcall
        local from_original_docsettings=frame3 and docsettings and
            type(docsettings.open)=='function' and frame3.func==docsettings.open and
            frame3.currentline==276 and type(frame3.source)=='string' and
            frame3.source:match('^@?frontend/docsettings%.lua$')~=nil
        local lfs=package.loaded['libs/libkoreader-lfs']
        local plain_file=lfs and type(lfs.symlinkattributes)=='function' and
            lfs.symlinkattributes(path,'mode')=='file' and
            lfs.symlinkattributes(home..'/library/r39-original-two-pages.sdr','mode')=='directory'
        -- R39.4.7: two distinct genuine DocSettings:open calls occur during
        -- the same second PDF opening: one from FileManager:openFile, then
        -- another at original ReaderUI:init line 131. The latter runs after
        -- the new PDF may have obtained a DocumentRegistry reference, so the
        -- first phase's zero-registry precondition cannot apply to it.
        -- The second phase instead validates original ReaderUI:init function
        -- identity and callsite, plus the already verified first doc release.
        local frame4=debug.getinfo(4,'Slf')
        local readerui=package.loaded['apps/reader/readerui']
        local original_readerui_init=frame4 and readerui and
            type(readerui.init)=='function' and frame4.func==readerui.init and
            frame4.currentline==131 and type(frame4.source)=='string' and
            frame4.source:match('^@?frontend/apps/reader/readerui%.lua$')~=nil
        local archived_first_engine_closed=r394_first_doc~=nil and
            r394_first_doc.is_open==false and
            rawget(r394_first_doc,'_document')==nil and
            r394_first_doc._document==false and
            r394_first_reader~=nil and r394_first_reader.document==nil
        local second_context=r394_cycle==2 and stats.events==2 and
            stats.filemanager==2 and r39_home_returned and stats.denied==0 and
            r3945_sidecar_writes==1 and not r394_second_home_sent and
            not r394_second_scroll_returned and real_fm~=nil and
            real_fm.instance==nil
        local from_returned_filemanager=second_context and
            r3945_sidecar_loads==0 and r394_input_lifecycles==1 and
            r394_first_pdf_released()
        local from_reopened_readerui=second_context and
            r3945_sidecar_loads==1 and r394_input_lifecycles==2 and
            r39_input_inhibit==1 and r39_input_until==0 and
            diag_reader()==nil and archived_first_engine_closed and
            original_readerui_init
        if r3945_sidecar_loads==0 then
            print('R39_4_5_SIDECAR_GATE exact=true c_pcall='..tostring(not not from_c_pcall)..
                  ' docsettings='..tostring(not not from_original_docsettings)..
                  ' fresh_write='..tostring(r3945_sidecar_writes==1)..
                  ' regular_file='..tostring(not not plain_file)..
                  ' cycle2='..tostring(not not from_returned_filemanager))
        elseif r3945_sidecar_loads==1 then
            print('R39_4_7_READERUI_SIDECAR_GATE exact=true c_pcall='..tostring(not not from_c_pcall)..
                  ' docsettings='..tostring(not not from_original_docsettings)..
                  ' readerui_init='..tostring(not not original_readerui_init)..
                  ' fresh_write='..tostring(r3945_sidecar_writes==1)..
                  ' regular_file='..tostring(not not plain_file)..
                  ' phase2='..tostring(not not from_reopened_readerui))
        end
        if from_c_pcall and from_original_docsettings and plain_file and
           (from_returned_filemanager or from_reopened_readerui) then
            local value=native_dofile(path)
            assert(type(value)=='table','R39.4.7 generated metadata not a table')
            r3945_sidecar_loads=r3945_sidecar_loads+1
            if from_returned_filemanager then
                print('R39_4_5_GENUINE_DOCSETTINGS_SIDECAR_LOADED_FROM_FIRST_CYCLE')
            else
                print('R39_4_7_GENUINE_READERUI_DOCSETTINGS_SIDECAR_RELOADED')
            end
            return value
        end
    end
    deny('DOFILE:'..tostring(path))
end
-- At the *last* real reader.lua statement, prevent calling libc exit
-- so the harness can verify normal Device:exit and cleanup invariants.
os.exit=function(code,close)
    assert(close==true and stats.events==4 and stats.loop==1 and r39_page2_verified and
           r39_home_returned and r394_second_home_returned and stats.device_exit==1
           and stats.os_exit==0,'reader.lua invoked os.exit before genuine shutdown')
    assert(real_fm and real_fm.instance==nil and real_loader
           and not real_loader:isPluginLoaded('ink-away'), 'plugin not finalized')
    stats.os_exit=1
    assert(r39_reader_seen and r39_page1_verified and r39_page2_verified and
           r394_first_draws and r394_first_draws[1]>=1 and r394_first_draws[2]>=1 and
           r394_second_scroll_returned,
           'ReaderUI repeated document lifecycle not completed')
    local reader=native_require('apps/reader/readerui')
    assert(reader.instance==nil and r39_saved_reader and
           r39_saved_reader.document==nil and r39_saved_doc and
           r3933_pdf_engine_released() and
           r3933_home_sentinel_count==1 and r39_home_returned and
           r394_second_home_returned and r394_input_lifecycles==2 and
           r394_first_doc and r394_first_reader and
           r394_first_doc~=r39_saved_doc and r394_first_reader~=r39_saved_reader and
           r394_first_doc.is_open==false and rawget(r394_first_doc,'_document')==nil and
           r394_first_doc._document==false and r39_saved_settings_file and
           in_home(r39_saved_settings_file),
           'R39.3 genuine reader/document/storage boundary incomplete')
    print('R39_REAL_READER_SHUTDOWN_COMPLETED')
    error('R25_INTENTIONAL_OS_EXIT_HOLD',2)
end
local function run()
    assert(os.getenv('KO_HOME')==home and os.getenv('HOME')==home)
    assert(#arg==1 and arg[1]==home..'/library')
    assert(package.loaded['device']==nil)
    -- Leave actual reader.lua untouched and use native dofile to enter it.
    -- Real entrypoint and modules; migration execution stays entirely blocked.
    print('R23_REAL_READER_LUA_ENTER')
    local ok,reason=pcall(native_dofile,'reader.lua')
    assert(not ok and tostring(reason):find('R25_INTENTIONAL_OS_EXIT_HOLD',1,true),
           'reader.lua did not reach verified synthetic application exit: '..tostring(reason))
    assert(r39_input_inhibit==1 and r39_input_until==1 and r394_input_lifecycles==2,
           'R39.4 second audited genuine ReaderUI Input lifecycle missing')
    assert(stats.filemanager==3 and stats.owner==3 and stats.collection_reads>=1 and
           stats.discovery>=1 and stats.discovery<=3 and
           stats.loop==1 and stats.events==4 and stats.device_exit==1 and
           stats.os_exit==1 and stats.meminfo_reads>0 and
           r3945_sidecar_writes==2 and r3945_sidecar_loads==2 and
           stats.meminfo_closes==stats.meminfo_reads and stats.denied==0,
           'incomplete R25 real loop/shutdown state')
    assert(real_fm.instance==nil and not real_loader:isPluginLoaded('ink-away'),
           'FileManager or plugin retained after full close')
    assert(#real_ui._window_stack==0,'UIManager window leak')
    assert(r39_reader_seen and r39_page1_verified and r39_page2_verified and
           r394_first_draws and r394_first_draws[1]>=1 and r394_first_draws[2]>=1 and
           r394_second_scroll_returned and r394_second_home_returned,
           'R39.4 first navigation and second genuine PDF scroll not both observed')
    assert(native_require('apps/reader/readerui').instance==nil,'ReaderUI still open after run')
    print('R39_REAL_READER_EXIT_BOUNDARY_PASS')
    print('R39_4_TWO_CYCLE_SYNTHETIC_PAGE_TURN_REOPEN_HOME_CLOSE; GLOBAL_MIGRATIONS_SKIPPED; NOT_BOOTABLE')
end
return {run=run}
