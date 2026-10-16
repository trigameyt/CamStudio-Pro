# CamStudio Pro — Android webcam for Windows

## Développé avec l'aide de l'intelligence artificielle

**CamStudio Pro a été développé principalement avec l'aide de ChatGPT
(OpenAI), sous la direction d'un créateur humain qui a proposé les
fonctionnalités, testé et amélioré le logiciel.**
Le projet est indépendant et n'est pas affilié à OpenAI.
[En savoir plus sur le développement avec IA](AI_DISCLOSURE.md).


**V1.0.0 Release Candidate 1 · Windows + Android · Vidéo uniquement · Sans cloud**

[English](README.en.md) · [Installation FR](docs/INSTALLATION_FR.md) · [Sécurité](SECURITY.md) · [Checklist V1](docs/RELEASE_CHECKLIST.md)

Utilise un téléphone Android comme webcam sur un PC Windows via USB (ADB) ou Wi-Fi privé. La diffusion peut être utilisée dans Discord et OBS grâce à une webcam virtuelle compatible. L'application possède un aperçu, des réglages d'image, des scènes personnalisables, des photos et des enregistrements MP4 silencieux.

**Nom provisoire :** un logiciel indépendant appelé CamStudio existe déjà. Pour une publication officielle, un nom distinctif est recommandé afin d'éviter toute confusion.

## Fonctionnalités

- USB : détection d'un appareil Android autorisé et connexion automatique après appairage initial.
- Wi-Fi : connexion locale manuelle avec adresse IP et clé d'accès.
- Une seule fenêtre V1 : relancer le logiciel rouvre la fenêtre déjà lancée, même si elle était masquée près de l'horloge.
- Réglages sauvegardés automatiquement et remplacement atomique du fichier de configuration ; clé chiffrée avec Windows DPAPI.
- Image : zoom, recadrage, rotation, miroir, contraste, luminosité, saturation, netteté, température et profils.
- Scènes : textes, images, couleurs, transitions, déplacement à la souris.
- Webcam virtuelle avec un pilote compatible OBS Virtual Camera.
- Photos PNG, vidéo MP4 **sans son**, pause/reprise, bibliothèque avec miniatures et lecteur silencieux.
- Mode simple / avancé, indicateur de batterie et diagnostic des FPS réels.

## Installation rapide en USB

1. Installer l'application Android, autoriser la caméra, puis appuyer sur **Démarrer la diffusion**. CamStudio Windows n'active jamais silencieusement le capteur du téléphone.
2. Activer les options développeur et le **débogage USB** sur Android.
3. Installer les Android Platform Tools officiels (https://developer.android.com/tools/releases/platform-tools) : ADB doit être dans le PATH ou le répertoire standard du SDK Android.
4. Brancher le câble USB, déverrouiller le téléphone et accepter la demande « Autoriser le débogage USB » pour cet ordinateur de confiance.
5. Ouvrir **Connexions** sur Windows et saisir une première fois la **clé affichée par l'application Android**. Elle restera masquée par défaut mais pourra être affichée au clic.
6. Sélectionner **USB**. L'application recherche les téléphones USB autorisés et essaie de se connecter quand le flux Android est actif.

La clé du téléphone survit aux redémarrages du service Android. Le bouton **Régénérer la clé** permet de la remplacer volontairement. Après régénération, mettre à jour la clé côté Windows.

La connexion USB automatique nécessite **un appareil autorisé dans ADB et sa clé**. Elle ne contourne pas les permissions du téléphone.

## Wi-Fi

Démarrer la diffusion Android. Entrer son adresse IPv4 locale et sa clé dans la page Connexions, choisir Wi-Fi puis Connecter. Utiliser exclusivement un **réseau privé de confiance** : le flux MJPEG circule en HTTP **non chiffré**. Ne jamais ouvrir le port 8765 vers Internet.

## Windows : installation et compilation

Conditions : Windows 10/11 x64, Python 3.12 pour compiler, OBS Virtual Camera pour la webcam virtuelle, Android Platform Tools pour l'USB. Avec un EXE compilé, conserver **tout le dossier CamStudioPro**, et pas seulement l'EXE.

Depuis PowerShell, dans le dossier windows :

    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    .\.venv\Scripts\python.exe test_v100_release.py
    .\.venv\Scripts\python.exe app.py

Pour générer le dossier EXE :

    .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name CamStudioPro --collect-all pyvirtualcam --collect-submodules camstudio_v04 --collect-all PySide6.QtMultimedia --collect-all PySide6.QtMultimediaWidgets app.py

## Android : compilation

Ouvrir le dossier android dans Android Studio (SDK 35, JDK 17/21, AGP défini dans settings.gradle). Compiler assembleDebug pour les tests. **Pour publier**, construire et signer un APK release avec une clé de signature qui t'appartient et qui ne doit jamais être mise dans GitHub.

## Fichiers utilisateur

| Fichier | Dossier |
| --- | --- |
| Paramètres (clé DPAPI protégée) | %APPDATA%\CamStudioPro\config.json |
| Scènes | %APPDATA%\CamStudioPro\scenes.json |
| Préférences d'interface | %APPDATA%\CamStudioPro\interface-v04.json |
| Photos et vidéos | %USERPROFILE%\Videos\CamStudioPro |

Les modifications sont sauvegardées après environ 350 ms d'inactivité, même avant la fermeture. Une interruption au tout premier instant suivant un changement peut encore faire perdre le dernier réglage. Les données DPAPI ne sont pas transférables vers un autre compte Windows : il faudra ressaisir la clé Android.

## Limitations de cette release candidate

- Pas d'audio, volontairement.
- Débit MJPEG et FPS natifs variables. Un mode de sortie 1440p / 60 FPS ne garantit pas 1440p ou 60 FPS natifs ; des images sont parfois agrandies.
- Pas encore de transport H.264/H.265 matériel sur Android.
- OBS Virtual Camera et Discord doivent être testés sur chaque configuration.
- La **connexion USB physique**, la signature de l'APK public, l'installation sur un PC vierge et les tests longs restent à valider avant la **V1.0 stable**.
- Une ancienne V0.x peut encore tourner à côté de V1 : fermer manuellement les anciennes instances lors de la migration.

## Community / Contribuer

**Everyone can suggest improvements through GitHub Issues and Pull Requests.**
The official main branch and releases are maintained by **@trigameyt**.
AI-assisted contributions are welcome with human review and testing.

- [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)
- [Governance](GOVERNANCE.md) · [Code of Conduct](CODE_OF_CONDUCT.md)
- [AI development disclosure](AI_DISCLOSURE.md) · [Security](SECURITY.md)
- [Maintainer setup checklist](docs/COMMUNITY_SETUP.md)

En français : la communauté peut proposer et tester des améliorations, mais le mainteneur valide chaque version officielle. Les fonctions sont centrées sur la vidéo, sans audio.

## Contribuer

Lire [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md) et la [checklist](docs/RELEASE_CHECKLIST.md). Licence MIT préparée (à confirmer par le propriétaire avant la première publication).

**Projet indépendant, sans affiliation au logiciel d'enregistrement d'écran CamStudio existant.**

## Langues de l'interface

L'application Windows démarre en **anglais**. Dans **Settings → Language**, tu peux choisir le **français**, chinois simplifié, hindi, espagnol, arabe, portugais, bengali, russe, ourdou, indonésien ou japonais. Le choix est sauvegardé et rétabli après redémarrage. Android propose aussi ces 12 langues pour les commandes principales. Certaines instructions techniques des traductions secondaires sont affichées en anglais par défaut.
