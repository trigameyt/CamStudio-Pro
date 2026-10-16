# Architecture, construction et validation

## Dossiers

- Windows Python/PySide6 : windows/app.py et windows/camstudio_v04 pour l'interface moderne.
- Traitement vidéo : windows/stream.py et windows/processor.py.
- USB : windows/usb_transport.py pour le tunnel ADB, windows/usb_monitor.py pour la découverte en arrière-plan.
- Instance unique : windows/single_instance.py avec IPC Qt local ; nouveau lancement = réafficher l'ancien.
- Confidentialité : windows/secure_store.py avec DPAPI utilisateur Windows.
- Android Java : android/app/src/main/java/com/camstudio/pro/ ; CameraService ouvre le port 8765 avec clé d'accès et notification.

## Compiler Windows

Python 3.12 et les dépendances de windows/requirements.txt. Ouvre PowerShell dans windows et exécute :

    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    .\.venv\Scripts\python.exe -m unittest discover -s tests -v
    .\.venv\Scripts\python.exe test_v100_release.py
    .\.venv\Scripts\python.exe app.py

Générer l'EXE en mode one-directory :

    .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name CamStudioPro --collect-all pyvirtualcam --collect-submodules camstudio_v04 --collect-all PySide6.QtMultimedia --collect-all PySide6.QtMultimediaWidgets app.py

Distribuer le dossier de sortie entier. Le pilote OBS Virtual Camera est un prérequis indépendant.

## Compiler Android

Importer android dans Android Studio, installer SDK 35, JDK 17/21 et les dépendances Gradle. Construire assembleDebug pour tester. Ne pas partager publiquement un APK de développement en prétendant qu'il s'agit d'une release signée. Pour l'APK final, signer avec une clé release conservée hors GitHub.

## Vérifier

- tests unitaires et tests test_v*.py sous windows ;
- ADB réel, autorisation du débogage et reconnexion après câble retiré ;
- mode Wi-Fi sur réseau privé et clé régénérée ;
- relancer deux fois le programme Windows et vérifier une seule instance V1 ;
- terminer depuis le Gestionnaire des tâches puis rouvrir et confirmer la persistance ;
- vidéo et webcam virtuelle réellement reçues dans OBS et Discord ;
- examen du dossier GitHub sans secrets, vidéos, caches, clés de signature ou documents personnels.

## Architecture de sécurité

Le flux Wi-Fi actuel n'est pas chiffré en transit. Le tunnel ADB est sur localhost mais l'autorisation USB demeure indispensable. L'Android foreground service nécessite un démarrage explicite par l'utilisateur. La clé Windows est liée au compte via DPAPI. Ne jamais écrire de clé dans les tests, logs ou copies d'écran.
