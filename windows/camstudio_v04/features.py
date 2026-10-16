from dataclasses import dataclass
@dataclass(frozen=True)
class Section:
    id: str
    title: str
    subtitle: str
    icon: str
PAGES = (
    Section('home','Accueil','Statut et actions rapides','⌂'),
    Section('camera','Caméra','Retour vidéo et contrôles complets','◉'),
    Section('studio','Studio','Image, filtres et cadrage','◈'),
    Section('scenes','Scènes','Profils et compositions','▤'),
    Section('outputs','Sorties','Webcam virtuelle, Discord et OBS','▣'),
    Section('record','Enregistrement','Photos et vidéo','●'),
    Section('connections','Connexions','Wi-Fi et USB','⌁'),
    Section('settings','Paramètres','Apparence et mode avancé','⚙'),
)
PLANNED = {
    'Camera2, ISO manuel et obturation',
    'H.264/H.265 matériel',
    'Éditeur de scènes multi-sources',
    'Mise à jour automatique',
    'Pairing sécurisé de type cryptographique',
    '1440p/60 natif garanti',
}
