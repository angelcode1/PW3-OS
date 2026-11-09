#!/usr/bin/env python3
"""Fail-closed parser for *metadata-only* Kindle storage inventory.

It cannot validate recovery, safety of partition writes, bootloader or data backup.
"""
import argparse, json, re, sys

BEGIN='R3877_19_READ_ONLY_STORAGE_BEGIN'
END='R3877_19_READ_ONLY_STORAGE_COMPLETE'
EXPECTED='3.0.35-lab126'

def block_device_kind(name):
    """Informational classification only: never infer bootloader or root location."""
    if re.fullmatch(r'mmcblk\d+boot[01]', name):
        return 'EMMC_BOOT_AREA'
    if re.fullmatch(r'mmcblk\d+p\d+', name):
        return 'EMMC_USER_AREA_PARTITION'
    if re.fullmatch(r'mmcblk\d+', name):
        return 'EMMC_USER_AREA_DEVICE'
    if re.fullmatch(r'mtdblock\d+', name):
        return 'MTD_BLOCK_DEVICE'
    return 'OTHER_BLOCK_DEVICE'


def analyze(s):
    result={'milestone':'R3877.19.1','result':'HOLD','hold_category':'INVENTORY_INCOMPLETE',
            'immutable_hold':'NOT_BOOTABLE','recovery_verified':False,
            'bootloader_verified':False,'rootfs_backup_verified':False,
            'kernel_syscall_compatibility_verified':False,'alpine_runtime_verified':False,
            'device_files_written':False,'firmware_write_performed':False,
            'raw_block_or_mtd_data_read':False,
            'root_backing_partition_verified':False,
            'bootloader_location_verified':False,
            'emmc_boot_area_contents_read':False}
    lines=[x.strip() for x in s.splitlines()]
    if lines.count(BEGIN)!=1 or lines.count(END)!=1 or lines.index(BEGIN)>=lines.index(END):
        result['hold_category']='MISSING_OR_DUPLICATE_SENTINELS';return result
    payload=lines[lines.index(BEGIN)+1:lines.index(END)]
    metadata={}; partitions=[];mtd=[];read_only=[]
    for line in payload:
        if not line or '=' not in line: continue
        k,v=line.split('=',1)
        if k=='partition':
            m=re.fullmatch(r'(mmcblk\d+(?:p\d+|boot[01])?|mtdblock\d+|sd[a-z]\d*),(\d+),(\d+),(\d+)',v)
            if not m:return {**result,'hold_category':'INVALID_PARTITION_RECORD'}
            partitions.append({'name':m.group(1),'major':int(m.group(2)),
                               'minor':int(m.group(3)),'size_1k_blocks':int(m.group(4)),
                               'kind':block_device_kind(m.group(1))})
        elif k=='mtd':
            m=re.fullmatch(r'mtd\d+,([0-9a-fA-F]+),([0-9a-fA-F]+)',v)
            if not m:return {**result,'hold_category':'INVALID_MTD_RECORD'}
            mtd.append({'name':v.split(',')[0],'size_bytes':int(m.group(1),16),
                        'erase_bytes':int(m.group(2),16)})
        elif k=='block_readonly':
            m=re.fullmatch(r'(mmcblk[01]),([01])',v)
            if not m:return {**result,'hold_category':'INVALID_READONLY_RECORD'}
            read_only.append({'name':m.group(1),'read_only':m.group(2)=='1'})
        elif k in ('kernel_release','machine','root_device','root_fstype','root_mount_read_only',
                   'root_mount_status','partitions_status','mtd_status'):
            if k in metadata:return {**result,'hold_category':'DUPLICATE_METADATA_KEY'}
            metadata[k]=v
    if metadata.get('kernel_release')!=EXPECTED or metadata.get('machine')!='armv7l':
        result['hold_category']='TARGET_KERNEL_OR_MACHINE_MISMATCH';return result
    if not metadata.get('root_fstype') or metadata.get('root_mount_read_only') not in ('true','false'):
        result['hold_category']='ROOT_MOUNT_METADATA_ABSENT';return result
    if not partitions and not mtd:
        result['hold_category']='NO_PARTITION_TOPOLOGY';return result
    if len(partitions)!=len(set(x['name'] for x in partitions)) or len(mtd)!=len(set(x['name'] for x in mtd)):
        result['hold_category']='DUPLICATE_PARTITION_NAME';return result
    result['inventory']={'kernel_release':metadata['kernel_release'],'machine':metadata['machine'],
                         'root_device':metadata.get('root_device','UNVERIFIED'),
                         'root_fstype':metadata['root_fstype'],
                         'root_mount_read_only':metadata['root_mount_read_only']=='true',
                         'partitions_status':metadata.get('partitions_status','NOT_REPORTED'),
                         'mtd_status':metadata.get('mtd_status','NOT_REPORTED'),
                         'partitions':sorted(partitions,key=lambda v:v['name']),
                         'mtd':sorted(mtd,key=lambda v:v['name']),
                         'block_readonly':sorted(read_only,key=lambda v:v['name']),
                         'emmc_boot_area_names':sorted(p['name'] for p in partitions if p['kind']=='EMMC_BOOT_AREA'),
                         'root_block_device_not_identified_from_rootfs': metadata.get('root_device')=='rootfs' and metadata['root_fstype']=='rootfs'}
    result.update(result='PASS_STORAGE_METADATA_ONLY',hold_category='NOT_BOOTABLE')
    return result

def main(argv=None):
    p=argparse.ArgumentParser(description='Read-only PW3 storage inventory parser')
    p.add_argument('inventory_file')
    args=p.parse_args(argv)
    try:
        with open(args.inventory_file,encoding='utf-8') as f: data=f.read()
        out=analyze(data)
    except (OSError,UnicodeError):
        out={'milestone':'R3877.19.1','result':'HOLD','hold_category':'INPUT_UNREADABLE',
             'immutable_hold':'NOT_BOOTABLE','recovery_verified':False}
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out['result'].startswith('PASS_') else 2
if __name__=='__main__':sys.exit(main())
