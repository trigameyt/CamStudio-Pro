"""Regression tests for Android clipboard and the Windows pairing-key Save action.

No user configuration, phone key or credentials are accessed. Test key is fake.
"""
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pairing_input import parse_pairing_text


class PairingInputTests(unittest.TestCase):
    def test_single_key_and_android_clipboard(self):
        token = "A1B2C3D4" * 4
        self.assertEqual(parse_pairing_text(token.lower()), (token, None))
        self.assertEqual(parse_pairing_text("192.168.10.12:8765\n" + token), (token, "192.168.10.12:8765"))
        self.assertEqual(parse_pairing_text("  http://10.0.0.8:8765\r\n" + token.lower()), (token, "10.0.0.8:8765"))

    def test_rejects_address_in_key_field_and_trailing_garbage(self):
        token = "ABCDEF12" * 4
        for text in ["192.168.0.8:8765", "X" + token, token + "0", "", "1.2.3.4:bad\n" + token]:
            with self.subTest(case=len(text)), self.assertRaises(ValueError):
                parse_pairing_text(text)

    @unittest.skipUnless(os.name == "nt", "DPAPI only available on Windows")
    def test_ui_save_clipboard_and_restart(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        import app as module
        from app import Studio
        from secure_store import reveal_key
        token = "ABCDEF0123456789" * 2
        qt = QApplication.instance() or QApplication([])
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(module, "APP_DIR", Path(directory)), patch.object(module, "CONFIG", Path(directory)/"config.json"):
                s = Studio()
                s.usb_monitor.stop()
                s._tray_enabled = False
                s._really_quit = True
                s._usb_autoconnect_enabled = False
                s._modern_ui.key_edit.setText(token.lower())
                self.assertEqual(s.key.text(), token.lower())
                self.assertTrue(s.save_pairing_key())
                self.assertEqual(s.key.text(), token)
                saved = json.loads(module.CONFIG.read_text(encoding="utf-8"))
                self.assertNotIn("key", saved)
                self.assertNotIn(token, module.CONFIG.read_text(encoding="utf-8"))
                self.assertEqual(reveal_key(saved["key_protected"]), token)

                qt.clipboard().setText("192.168.1.60:8765\n" + token)
                self.assertTrue(s.paste_android_pairing())
                self.assertEqual(s.host.text(), "192.168.1.60:8765")
                self.assertEqual(s._modern_ui.key_edit.text(), token)

                # Entering an IP alone must not silently replace the valid key.
                s._modern_ui.key_edit.setText("192.168.1.60:8765")
                self.assertFalse(s.save_pairing_key())
                s._modern_ui.key_edit.setText(token)
                self.assertTrue(s.save_pairing_key())

                # Mimic an abrupt process stop and fresh restart from encrypted config.
                s._autosave_timer.stop()
                s._fully_ready = False
                restored = Studio()
                restored.usb_monitor.stop()
                restored._tray_enabled = False
                restored._really_quit = True
                restored._usb_autoconnect_enabled = False
                self.assertEqual(restored.key.text(), token)
                self.assertEqual(restored._modern_ui.key_edit.text(), token)
                self.assertEqual(restored.host.text(), "192.168.1.60:8765")
                restored._autosave_timer.stop()
                restored._fully_ready = False
                s.close()
                restored.close()
                qt.clipboard().clear()


if __name__ == "__main__":
    unittest.main()
