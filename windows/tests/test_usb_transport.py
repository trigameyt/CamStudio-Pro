import os
import unittest
from unittest.mock import patch
from pathlib import Path

import usb_transport

class UsbTests(unittest.TestCase):
    def test_tunnel_port_and_cleanup(self):
        with patch("usb_transport.find_adb",return_value="adb.exe"), patch("usb_transport.adb_run",side_effect=["device","18765", ""]) as call:
            tunnel=usb_transport.open_usb_tunnel()
            self.assertEqual(tunnel.url,"http://127.0.0.1:18765")
            tunnel.close()
            tunnel.close()
            self.assertEqual(call.call_count,3)
            self.assertEqual(call.call_args_list[1].args[1],["-d","forward","tcp:0","tcp:8765"])
            self.assertEqual(call.call_args_list[2].args[1],["-d","forward","--remove","tcp:18765"])

    def test_fails_if_no_usb(self):
        with patch("usb_transport.find_adb",return_value="adb.exe"), patch("usb_transport.adb_run",side_effect=usb_transport.UsbConnectionError("no usb")):
            with self.assertRaises(usb_transport.UsbConnectionError):
                usb_transport.open_usb_tunnel()

    def test_fails_when_adb_port_invalid(self):
        with patch("usb_transport.find_adb",return_value="adb.exe"), patch("usb_transport.adb_run",side_effect=["device", "notaport"]):
            with self.assertRaises(usb_transport.UsbConnectionError):
                usb_transport.open_usb_tunnel()

if __name__=="__main__":
    unittest.main()
