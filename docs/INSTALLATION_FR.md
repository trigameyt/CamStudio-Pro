# Installation de CamStudio Pro V1 RC

## Préparer le PC

- Windows 10/11, 64 bits, et un téléphone Android 8+ avec caméra.
- Pour la webcam virtuelle : OBS Studio et son pilote Virtual Camera.
- Pour l'USB : Android Platform Tools officiels, contenant ADB, et un câble USB de données.
- Un APK Android compatible avec le client Windows.

## Démarrer Android

Ouvre l'application CamStudio Pro sur le téléphone, autorise la caméra et appuie sur **Démarrer la diffusion**. La notification permanente indique que la caméra fonctionne, y compris quand l'écran est verrouillé. Aucune activation silencieuse depuis le PC.

## USB automatique après appairage

1. Dans les options développeur du téléphone, active le débogage USB.
2. Branche le téléphone et accepte sur Android **Autoriser le débogage USB** pour ce PC de confiance.
3. Depuis PowerShell, vérifie que la commande **adb devices -l** montre le téléphone dans l'état **device**, et non **unauthorized**.
4. Dans CamStudio Pro Windows, va dans **Connexions**, entre la clé affichée sur Android, puis choisis **USB**.
5. Au prochain démarrage, si la diffusion Android est déjà active, CamStudio Windows recherchera et reconnectera ce téléphone automatiquement.

Si la clé a été régénérée sur Android, mets-la à jour côté Windows. L'app utilise cette clé même en USB : aucune protection n'est désactivée. Si le téléphone est introuvable, vérifie le câble de données, ADB et les autorisations Android.

## Wi-Fi

Sur un même réseau privé, utilise l'IP et la clé de l'application Android dans Connexions, choisis Wi-Fi, puis Connecter. N'expose jamais le port 8765 à Internet.

## Zone de notification et instance unique

Quand tu fermes la fenêtre Windows, CamStudio peut rester actif près de l'horloge. Cliquer sur le raccourci V1 réaffiche la fenêtre existante. Pour fermer complètement, clic droit sur l'icône → Quitter CamStudio Pro.

## Sauvegarde des paramètres

Les paramètres sont sauvegardés automatiquement dans le profil Windows, dans le dossier AppData\Roaming\CamStudioPro. La clé est protégée par Windows DPAPI. Une fin de tâche brutale ne supprime pas les paramètres déjà enregistrés ; un changement effectué au cours de la dernière fraction de seconde peut ne pas avoir été écrit.

## Dépannage

- Clé refusée : re-copie la clé Android, ou démarre la diffusion puis vérifie qu'elle n'a pas été régénérée.
- USB introuvable : exécute adb devices -l, autorise le débogage, utilise un câble de données, ferme les autres sessions ADB concurrentes.
- Webcam invisible dans Discord : vérifie le pilote OBS Virtual Camera.
- Flux à 20–30 FPS : sélectionner 60 FPS dans la sortie ne crée pas de nouvelles images capturées.
- La vidéo reste sans son ; cette application n'enregistre pas de microphone.

## Choisir la langue

Dans Windows, ouvre **Settings → Language** : anglais par défaut, français et dix autres langues. Le choix est conservé après le redémarrage. Sur Android, le sélecteur de langue est affiché près du haut de l'écran.
