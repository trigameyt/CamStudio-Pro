# CamStudio Pro — Community roadmap

**Status:** V1.0 Release Candidate. This roadmap is a proposal, not a release promise. Project scope: local-first Windows and Android webcam, **video only**, no audio.

## P0 — Before declaring V1.0 stable

- [ ] Test physical USB end-to-end: initial ADB permission, phone camera consent, disconnect/reconnect, persisted key and key rotation.
- [ ] Test a clean Windows installation and the OBS virtual camera backend.
- [ ] Test Discord/OBS with real source FPS, latency and reliability on multiple phones.
- [ ] Produce a properly signed Android release APK (never release the debug APK as stable).
- [ ] Review security and local Wi-Fi HTTP/MJPEG limitations; do not expose the video port to the Internet.
- [ ] Review project name (another CamStudio exists), MIT license and dependencies.
- [ ] Human-review translations (including right-to-left languages).
- [ ] Verify Windows and Android GitHub Actions run successfully before stable release.

## P1 — Reliability and performance

- [ ] Reduce actual camera-to-output latency, dropped frames and CPU usage.
- [ ] Improve USB recovery after unplug/replug and Android service restart.
- [ ] Provide diagnostics for ADB, virtual camera backend and frame rate.
- [ ] Improve low-light picture quality without significantly increasing latency.

## P2 — Future improvements

- [ ] Investigate hardware H.264/H.265 streaming with compatible device fallback.
- [ ] Refine visual scene composition and overlays.
- [ ] Add an easier Windows installer and update guidance.
- [ ] Expand and professionally review translations.

## Out of scope

No microphone/audio capture, paid cloud account, remote hidden camera activation, or unsupported native 60-FPS promises.

## Propose a change

Use [Issues](../../issues/new/choose) for bugs and feature requests. Discuss large changes in an issue first. The maintainer decides which PRs enter official releases.

CamStudio Pro was created primarily with ChatGPT assistance under human direction. See [AI_DISCLOSURE.md](AI_DISCLOSURE.md).

_En français : priorité à la stabilité USB réelle, aux performances et aux tests de publication avant d'ajouter beaucoup de nouveautés._