# CamStudio Pro — use an Android phone as a Windows webcam

## Built with AI assistance

**CamStudio Pro was developed primarily with the help of ChatGPT
(OpenAI), guided by a human creator who proposed features, tested
the software and iterated on it.**
This is an independent project, not affiliated with OpenAI.
[Read the AI development disclosure](AI_DISCLOSURE.md).


**V1.0.0 Release Candidate 1 · Windows + Android · Video only · No cloud**

[Français](README.md) · [Development](docs/DEVELOPMENT.md) · [Security](SECURITY.md) · [Release checklist](docs/RELEASE_CHECKLIST.md)

A local-first Android webcam companion for Windows. Stream over authorized USB debugging (ADB) or trusted private Wi-Fi. Features include live preview, video adjustments, scenes with text and image overlays, OBS-compatible virtual webcam output, photos, and silent MP4 recordings. No account is required.

**Naming notice:** another unrelated application already uses the name CamStudio. A distinct final product name is strongly recommended before public release.

## Features

- Automatic authorized USB device detection and reconnect after initial pairing.
- Manual local Wi-Fi connection, pairing key shown on demand.
- One Windows V1 instance: launching again restores the existing tray-hidden window.
- Autosaved settings and atomic configuration writes, Windows DPAPI key protection.
- Zoom, crop, rotate, image filters, color settings, scene backgrounds, text and images.
- Virtual webcam output for supported Discord/OBS setups (OBS Virtual Camera driver required).
- Photo capture, silent MP4 recordings, pause/resume, recording gallery, video-only playback.
- Simple and advanced user interface modes, live phone battery and frame rate diagnostics.

## USB connection

1. Install and open the Android companion. Grant camera permission and tap **Start streaming**. Windows never secretly enables Android camera capture.
2. Enable Android **Developer options → USB debugging**.
3. Install official Android Platform Tools: https://developer.android.com/tools/releases/platform-tools. ADB must be installed or discoverable from the Android SDK folder.
4. Connect a data-capable USB cable, unlock the phone, and accept the **USB debugging authorization** prompt for your trusted PC.
5. In Windows **Connections**, enter the Android pairing key once and select USB. The PC will look for an authorized phone and attempt to connect whenever its stream is active.

The Android key persists across camera service restarts; it can be manually regenerated. After rotation, update the Windows key. USB auto-connect does **not** bypass Android permissions.

## Wi-Fi connection

Use a **trusted private LAN only**. Read the IPv4 address and pairing key from the Android app, then select Wi-Fi and connect in Windows. The current MJPEG stream runs over unencrypted HTTP; never expose port 8765 to the public Internet.

## Build

Windows: Python 3.12, x64 Windows, PySide6, OpenCV and the dependencies from windows/requirements.txt. Run the app from the windows folder:

    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe app.py

Build using PyInstaller in onedir mode; see [development](docs/DEVELOPMENT.md). Distribute the **entire output directory**, not the EXE alone.

Android: open android in Android Studio with Android SDK 35 and JDK 17/21. Debug APKs are for local testing; sign a proper release APK with your private signing key before public distribution.

## Data, security and limitations

Data stays under the Windows user profile: %APPDATA%\CamStudioPro for settings and scenes, %USERPROFILE%\Videos\CamStudioPro for recordings. Windows DPAPI protects the pairing key against casual file disclosure but cannot make an untrusted device trustworthy.

A task-manager forced termination can lose edits made within the most recent ~350 ms; other changes are autosaved and written atomically. FPS/resolution depend on phone hardware, and 1440p/60 as an output option does not imply true native 1440p/60 capture. No audio. Real USB, new-PC installation, signed Android release builds, and Discord/OBS compatibility are still pending validation before stable V1.0.

See [SECURITY.md](SECURITY.md) and [release checklist](docs/RELEASE_CHECKLIST.md). MIT license proposed, pending confirmation before public publication.

## Interface languages

**English is the default.** In Windows **Settings → Language**, select French, Simplified Chinese, Hindi, Spanish, Arabic, Portuguese, Bengali, Russian, Urdu, Indonesian or Japanese. The choice persists across launches. The Android companion also offers the same 12 languages for primary controls; some technical instructions fall back to English.

## Community contribution

Anyone can propose bug fixes, translations and features using Issues and Pull Requests. Maintainer **@trigameyt** remains responsible for the official branch and releases. This project is independent, AI-assisted and video-only.

[Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md) · [Governance](GOVERNANCE.md) · [Code of Conduct](CODE_OF_CONDUCT.md) · [GitHub setup checklist](docs/COMMUNITY_SETUP.md)
