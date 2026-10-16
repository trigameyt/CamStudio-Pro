# Checklist avant la publication stable V1.0

**État : release candidate de test, pas encore une stable pour tous les utilisateurs.**

## Implémentation vérifiée

- [x] Une seule instance V1 et réactivation de la fenêtre depuis la zone de notification (simulation IPC).
- [x] Clé Android visible sur demande, masquée par défaut et protégée par DPAPI sur Windows.
- [x] Sauvegarde automatique et écriture atomique des paramètres ; restauration contrôlée par test.
- [x] Détection USB autorisée et reconnexion logique automatique dans les tests simulés.
- [x] Clé Android conservée entre les redémarrages et bouton de régénération.
- [x] Compilation APK de développement Android.
- [x] Documentation en français et anglais, politique de sécurité, contribution et ignore GitHub.
- [x] Scènes, capture photo et vidéo MP4 sans son.

## À valider AVANT un dépôt public annoncé comme stable

- [ ] Brancher un vrai téléphone Android et confirmer la connexion USB / déconnexion / reconnexion.
- [ ] Tester l'APK V1 sur le téléphone en conservant les permissions et la clé entre redémarrages.
- [ ] Confirmer le double-clic sur l'EXE lorsqu'il est déjà masqué dans Windows.
- [ ] Tester une fin de tâche forcée et une nouvelle ouverture sur le PC physique.
- [ ] Installer la version Windows sur un PC neuf avec les dépendances documentées.
- [ ] Tester OBS et Discord avec vraie webcam virtuelle et vérifier les FPS réels.
- [ ] Produire l'APK Android release signé avec une clé privée contrôlée par le propriétaire.
- [ ] Vérifier les droits et licences des dépendances.
- [ ] Confirmer la licence MIT proposée avant publication.
- [ ] Choisir un nom distinctif (CamStudio existe déjà comme autre produit).
- [ ] Vérifier le dépôt et l'archive pour données personnelles, identifiants, clés, fichiers de profil et médias privés.

Une fois tous ces tests passés, préparer la V1.0.0 stable et le tag GitHub v1.0.0.

- [x] Sélecteur multilingue Windows et Android (anglais par défaut, français et 10 autres langues).
- [x] Choix de langue restauré au redémarrage dans les tests Windows.
- [ ] Relecture humaine des traductions avant la publication stable, notamment les textes techniques et les écritures de droite à gauche.
