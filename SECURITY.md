# Security Policy / Politique de sécurité

CamStudio Pro V1.0 RC1 is a release candidate. Do not submit secrets, camera keys, unredacted IP addresses, personal recordings, private logs, or signing keys in public issues.

## Trust boundaries

**Wi-Fi:** Android serves MJPEG video over **unencrypted HTTP** (TCP port 8765) authenticated by a pairing key. It is for trusted local networks only. Do not forward this port to the Internet.

**USB:** The app uses ADB local port forwarding and requires explicit Android USB debugging authorization. Grant this authorization only to computers you trust; ADB is a powerful debugging interface.

**Key storage:** The Android application persists a random 128-bit key in its app-private storage and offers explicit regeneration. Windows stores the saved key using current-user DPAPI and only reveals it on a user click. A copied key may still be visible to clipboard monitoring tools.

**Camera activation:** Android streaming is started manually by the phone user with a visible foreground notification; the Windows USB monitor does not activate a phone's camera without consent.

## Known limitations

No TLS/end-to-end encryption over LAN, no cryptographic hardware attestation, no signed automatic update system. Do not use this application across untrusted networks.

## Responsible reporting

When publishing the repository, enable GitHub private security advisories. Supply a project-controlled contact channel for private vulnerability reports; do not use another person's contact or post confidential reports publicly.
