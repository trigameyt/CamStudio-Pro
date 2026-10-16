# Contributing / Contribuer

CamStudio Pro is a local-first Android webcam for Windows, created primarily with ChatGPT assistance under human direction. Contributions are welcome, including AI-assisted work that is **human reviewed**.

## Workflow

1. Search existing Issues. Open a **Bug report** or **Feature request** for new work. Discuss large changes before coding.
2. Fork the repository or create a feature branch, e.g. `fix/usb-reconnect`.
3. Implement a focused change, with tests and documentation where relevant.
4. Run the appropriate tests (see below).
5. Open a Pull Request to `main`, link the Issue, and describe your verification. Mention significant AI assistance.
6. Wait for the maintainer's review and approval. No contribution is merged automatically.

## Windows tests

Use Windows 10/11, Python 3.12:

```powershell
cd windows
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe test_v100_i18n.py
```

## Android check

Open `android/` in Android Studio (JDK 17, SDK 35). With Gradle installed:

```bash
cd android
gradle :app:assembleDebug --no-daemon
```

**Do not commit** debug APKs, release signing keys, private IPs, pairing keys, config.json, user screenshots/videos, personal logs or any other secret.

## Quality and scope

- This is a **video-only** application: no audio, cloud accounts or hidden Android camera activation.
- Keep translations accurate; fall back to English when a translation is unavailable.
- Do not claim 60 native FPS simply because the output format advertises 60.
- Explain impacts on privacy, phone permissions, virtual camera compatibility and USB trust.
- Test on actual devices when a change cannot be verified with unit tests.

See [ROADMAP](ROADMAP.md), [GOVERNANCE](GOVERNANCE.md), [SECURITY](SECURITY.md), [AI disclosure](AI_DISCLOSURE.md).