#!/usr/bin/env python3
"""R3877.74: Mac-only serial-device *name inventory*, no serial I/O.

Never opens ports, contacts Kindle, changes settings, or publishes raw device
paths/names. A candidate serial name is NOT proof of a 1.8 V UART adapter.
"""
import argparse
import json
import os
import platform
import sys

PREFIXES = (
    ('cu.usbserial', 'USB_SERIAL_NAMING'),
    ('cu.usbmodem', 'USB_MODEM_NAMING'),
    ('cu.SLAB_USBtoUART', 'SILABS_NAMING'),
    ('cu.wchusbserial', 'WCH_NAMING'),
    ('cu.UC-232A', 'USB_SERIAL_NAMING'),
    ('cu.serial', 'USB_SERIAL_NAMING'),
)


def classify(name):
    for prefix, category in PREFIXES:
        if name.startswith(prefix):
            return category
    return None


def inspect_names(names):
    counts = {}
    for name in sorted(set(names)):
        if not isinstance(name, str):
            continue
        category = classify(name)
        if category is not None:
            counts[category] = counts.get(category, 0) + 1
    return dict(candidate_port_count=sum(counts.values()), candidate_naming_counts=counts,
                adapter_model_verified=False, actual_logic_voltage_verified=False,
                adapter_connected_to_kindle_verified=False, raw_serial_paths_published=False,
                uart_port_opened=False, serial_data_sent=False, serial_data_received=False)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acknowledge-local-device-name-inventory', action='store_true')
    a = p.parse_args(argv)
    result = dict(milestone='R3877.74', result='HOLD', immutable_hold='NOT_BOOTABLE',
                  hold_category='MAC_SERIAL_NAME_INVENTORY_NOT_AUTHORIZED',
                  mac_device_name_inventory_performed=False, kindle_access_performed=False,
                  serial_port_opened=False, firmware_write_performed=False,
                  physical_uart_access_verified=False, recovery_verified=False)
    if a.acknowledge_local_device_name_inventory:
        if platform.system() != 'Darwin':
            result['hold_category'] = 'NOT_MACOS'
        else:
            try:
                names = os.listdir('/dev')
                review = inspect_names(names)
                result['review'] = review
                result['mac_device_name_inventory_performed'] = True
                result['hold_category'] = ('CANDIDATE_USB_SERIAL_NAMES_PRESENT_VOLTAGE_UNVERIFIED'
                                           if review['candidate_port_count'] else
                                           'NO_CANDIDATE_USB_SERIAL_NAME_DETECTED')
            except OSError:
                result['hold_category'] = 'MAC_DEVICE_NAME_LIST_UNAVAILABLE'
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 2


if __name__ == '__main__':
    sys.exit(main())
