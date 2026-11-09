"""Synthetic unit tests; no physical ports or Kindle contacted."""
import contextlib
import io
import json
import unittest
from unittest.mock import patch
import pw3_r3877_74_macos_uart_inventory as m


class Tests(unittest.TestCase):
    def test_no_optin_no_list(self):
        with patch.object(m.os, 'listdir', side_effect=AssertionError('must not scan')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main([]), 2)
        j = json.loads(out.getvalue())
        self.assertEqual(j['hold_category'], 'MAC_SERIAL_NAME_INVENTORY_NOT_AUTHORIZED')
        self.assertFalse(j['mac_device_name_inventory_performed'])

    def test_mac_no_adapter(self):
        with patch.object(m.platform, 'system', return_value='Darwin'), \
             patch.object(m.os, 'listdir', return_value=['cu.Bluetooth-Incoming-Port', 'tty.null']):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--acknowledge-local-device-name-inventory']), 2)
        j = json.loads(out.getvalue())
        self.assertEqual(j['review']['candidate_port_count'], 0)
        self.assertEqual(j['immutable_hold'], 'NOT_BOOTABLE')

    def test_mac_candidate(self):
        with patch.object(m.platform, 'system', return_value='Darwin'), \
             patch.object(m.os, 'listdir', return_value=['cu.usbserial-0001', 'cu.usbmodemA', 'cu.wchusbserial-11']):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--acknowledge-local-device-name-inventory']), 2)
        j = json.loads(out.getvalue())
        self.assertEqual(j['review']['candidate_port_count'], 3)
        self.assertFalse(j['review']['actual_logic_voltage_verified'])
        self.assertNotIn('0001', out.getvalue())

    def test_duplicate_name_deduped(self):
        self.assertEqual(m.inspect_names(['cu.usbserialA', 'cu.usbserialA'])['candidate_port_count'], 1)

    def test_unknown_filtered(self):
        self.assertEqual(m.inspect_names(['cu.Bluetooth-Incoming-Port', 'cu.debug', 'tty.usbserial1'])['candidate_port_count'], 0)

    def test_linux_never_enumerates(self):
        with patch.object(m.platform, 'system', return_value='Linux'), \
             patch.object(m.os, 'listdir', side_effect=AssertionError('must not list')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--acknowledge-local-device-name-inventory']), 2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'], 'NOT_MACOS')

    def test_oserror_failclosed(self):
        with patch.object(m.platform, 'system', return_value='Darwin'), \
             patch.object(m.os, 'listdir', side_effect=OSError('denied')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                m.main(['--acknowledge-local-device-name-inventory'])
        self.assertNotIn('review', json.loads(out.getvalue()))

    def test_other_naming(self):
        self.assertEqual(m.classify('cu.SLAB_USBtoUART111'), 'SILABS_NAMING')
        self.assertEqual(m.classify('cu.UC-232A'), 'USB_SERIAL_NAMING')

    def test_no_pii_in_report(self):
        x = json.dumps(m.inspect_names(['cu.usbserial-PERSONAL-SERIAL-123']))
        self.assertNotIn('PERSONAL', x)
        self.assertNotIn('/dev', x)

    def test_no_hardware_authorization(self):
        r = m.inspect_names(['cu.usbmodem999'])
        self.assertFalse(r['adapter_connected_to_kindle_verified'])
        self.assertFalse(r['serial_data_sent'])
        self.assertFalse(r['serial_data_received'])


if __name__ == '__main__':
    unittest.main()
