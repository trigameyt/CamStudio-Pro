"""CamStudio Pro V1 internationalization.

English is the default. French plus ten additional widely spoken languages
can be selected in Settings. UI strings are never sent to an online translator;
all catalogs ship with the application.
"""
from __future__ import annotations
from PySide6.QtWidgets import QLabel,QPushButton,QCheckBox,QLineEdit,QComboBox,QGroupBox
from PySide6.QtCore import Qt
import re

LANGUAGES=(
    ('en','English'),
    ('fr','Français'),
    ('zh','简体中文'),
    ('hi','हिन्दी'),
    ('es','Español'),
    ('ar','العربية'),
    ('pt','Português'),
    ('bn','বাংলা'),
    ('ru','Русский'),
    ('ur','اردو'),
    ('id','Bahasa Indonesia'),
    ('ja','日本語'),
)
SUPPORTED={code for code,_ in LANGUAGES}
ACTIVE='en'

# Source text (legacy French) to canonical English.
FR_EN={
'Accueil':'Home','Caméra':'Camera','Studio':'Studio','Scènes':'Scenes',
'Sorties':'Outputs','Enregistrement':'Recording','Connexions':'Connections',
'Paramètres':'Settings','Statut et actions rapides':'Status and quick actions',
'Retour vidéo et contrôles complets':'Live preview and full controls',
'Image, filtres et cadrage':'Image, filters and framing',
'Profils et compositions':'Profiles and layouts',
'Webcam virtuelle, Discord et OBS':'Virtual webcam, Discord and OBS',
'Photos et vidéo':'Photos and videos','Wi-Fi et USB':'Wi-Fi and USB',
'Apparence et mode avancé':'Appearance and advanced mode',
'Caméra active même en arrière-plan':'Camera works in the background',
'Diffusion locale uniquement':'Local streaming only',
'Vidéo non envoyée au cloud':'Video is never sent to the cloud',
'Vue d’ensemble':'Overview','Connexion, batterie, caméra et actions rapides':'Connection, battery, camera and quick actions',
'Connecte une caméra pour afficher le retour vidéo.':'Connect a camera to see the live preview.',
'● Hors ligne':'● Offline','Batterie : -- %':'Battery: -- %',
'Source : en attente':'Source: waiting','Diagnostic : aucune source':'Diagnostics: no source',
'Flux réel : -- FPS · Webcam virtuelle : -- FPS':'Actual stream: -- FPS · Virtual camera: -- FPS',
'Flux réel : en attente de connexion':'Actual stream: waiting for connection',
'Connecter la caméra':'Connect camera','Déconnecter':'Disconnect','Connecter':'Connect',
'Déconnecter la caméra':'Disconnect camera','Capture photo':'Take photo',
'Prendre une photo':'Take a photo','Caméra déconnectée':'Camera disconnected',
'Webcam virtuelle':'Virtual camera',
'Sortie pour Discord, OBS et les applications compatibles.':'Output for Discord, OBS and compatible applications.',
'Activer / arrêter la webcam virtuelle':'Toggle virtual camera',
'Fluidité Discord':'Discord performance',
'Tant que le téléphone produit environ 20 à 30 FPS réels, choisis 30 FPS dans Discord, et non 60 FPS. Évite les filtres trop lourds ou un éclairage faible.':'If your phone delivers 20–30 actual FPS, use 30 FPS in Discord instead of 60. Avoid heavy filters and low light.',
'Traitement d’image':'Image processing',
'Les profils existants fonctionnent immédiatement.':'Existing profiles can be applied instantly.',
'Naturel':'Natural','Cinéma':'Cinema','Streaming':'Streaming',
'Ouvrir les réglages manuels de la caméra':'Open manual camera settings',
'Ajustements fins':'Fine adjustments',
'Les paramètres ISO, obturation et contrôle Camera2 nécessitent une implémentation Android distincte.':'ISO, shutter and Camera2 controls require additional Android implementation.',
'Profils disponibles':'Available profiles',
'Appliquer les profils sauvegardés sans interrompre la vidéo.':'Apply saved profiles without interrupting the video.',
'Appliquer':'Apply','Nouveau profil':'New profile','Enregistrer profil':'Save profile',
'Éditeur de scènes':'Scene editor',
'Crée des scènes avec une caméra, des images et des textes. Déplace les éléments à la souris ; tes scènes sont sauvegardées automatiquement.':'Create scenes with camera, images and text. Drag elements to position them. Scenes are saved automatically.',
'Webcam virtuelle':'Virtual webcam','Sortie inactive':'Output inactive',
'Contrôle de la webcam système utilisée par Discord et OBS.':'Control the system webcam used by Discord and OBS.',
'Résolution de sortie':'Output resolution',
'Diagnostic sortie':'Output diagnostics','Diagnostic réseau':'Network diagnostics',
'1440p / 60 FPS dans la liste correspond à un format proposé, pas à une capture native garantie.':'1440p / 60 FPS is an output format, not a guarantee of native capture.',
'Photos et vidéos':'Photos and videos',
'Captures via les fonctions existantes de CamStudio.':'Capture using CamStudio built-in tools.',
'Démarrer / arrêter la vidéo':'Start / stop video',
'⏸  Pause':'⏸ Pause','⏸ Pause':'⏸ Pause',
'▶  Reprendre':'▶ Resume','■  Arrêter vidéo':'■ Stop recording',
'Enregistrement : inactif':'Recording: inactive',
'Mes enregistrements':'My recordings',
'Toutes tes captures locales avec miniatures, dates, lecture et accès aux fichiers.':'Your local captures with thumbnails, dates, playback and file access.',
'Enregistrement pro':'Advanced recording',
'H.264/H.265 matériel, choix du débit et des codecs : futures évolutions.':'Hardware H.264/H.265, bitrate and codecs: planned features.',
'Connexion du téléphone':'Phone connection',
'Les identifiants restent stockés uniquement dans ton profil utilisateur local.':'Pairing details stay in your local user profile.',
'Statut : hors ligne':'Status: offline',
'Adresse Wi-Fi du téléphone (ignorée si USB est choisi)':'Phone Wi-Fi address (ignored when USB is selected)',
'Clé privée affichée par l’application Android':'Private key shown by the Android application',
'Clé affichée dans l’application Android':'Key shown in the Android application',
'Clé de connexion':'Pairing key',
'Afficher la clé':'Show key','Masquer la clé':'Hide key','Copier la clé':'Copy key',
'Ne communique jamais cette clé publiquement.':'Never share this key publicly.',
'USB : connexion automatique dès que le téléphone autorise ADB et que la clé est enregistrée.':'USB reconnects automatically after Android authorizes ADB and the key is saved.',
'Transport':'Transport',
'USB (câble + débogage USB)':'USB (cable + USB debugging)',
'Le sélecteur USB sera disponible après installation de la V0.3.1 sur ce projet.':'The USB selector requires the Windows USB transport.',
'Le transport USB passe par ADB local. Ne jamais ouvrir le serveur MJPEG directement sur Internet.':'USB uses local ADB forwarding. Never expose the MJPEG server to the internet.',
'Mode d’utilisation':'Usage mode',
'Une interface simple pour démarrer ; des options supplémentaires pour les utilisateurs expérimentés.':'A simple interface to get started, with extra options for experienced users.',
'Mode actuel : Simple':'Current mode: Simple','Activer le mode avancé':'Enable advanced mode',
'Simple : aperçu et actions essentielles. Avancé : contrôles complets et diagnostics disponibles.':'Simple: preview and essential actions. Advanced: complete controls and diagnostics.',
'Apparence':'Appearance',
'La V0.4 Preview utilise un thème sombre violet unique, optimisé pour le streaming.':'A dark purple theme designed for streaming.',
'Afficher les informations techniques dans l’accueil':'Show technical information on Home',
'Projet et confidentialité':'Project and privacy',
'Préparation à une publication open source.':'Preparing for open-source publication.',
'Aucun mot de passe, clé USB/ADB, IP personnelle ou identifiant du téléphone ne doit entrer dans GitHub.':'Never put passwords, pairing keys, personal IP addresses or device IDs on GitHub.',
'Version de travail : V1.0 GitHub — moteur de caméra V0.3.1 conservé.':'CamStudio Pro V1.0 — GitHub release candidate.',
'  ·  Mode avancé':'  ·  Advanced mode','  ·  À venir':'  ·  Coming soon',
'Mode actuel : ':'Current mode: ','Avancé':'Advanced','Simple':'Simple',
'● Caméra ':'● Camera ','connectée':'connected','connecté':'connected',
'hors ligne':'offline','en pause':'paused','en cours':'recording',
'Enregistrement : ':'Recording: ',
'Webcam virtuelle : ':'Virtual camera: ',
'active':'active','inactive':'inactive','inactif':'inactive',
'Statut : ':'Status: ','Images reçues : ':'Frames received: ',
' FPS · Webcam envoyée : ':' FPS · Webcam sent: ',
' FPS (Discord : 30 FPS conseillé)':' FPS (30 FPS recommended for Discord)',
'Capture : ':'Capture: ',' · sortie vidéo : ':' · output video: ',
'Source caméra : en attente':'Camera source: waiting',
'Sortie : ':'Output: ','Sortie inactive':'Output inactive',
'Batterie : ':'Battery: ','CamStudio Pro | Studio caméra':'CamStudio Pro | Camera studio',
'CamStudio Pro · Studio caméra (V1.0 Préparation GitHub)':'CamStudio Pro · Camera studio (V1.0)',
'CamStudio Pro reste actif dans la zone de notification.':'CamStudio Pro is still running in the system tray.',
'Ne plus afficher ce message':'Do not show this message again',
'CamStudio Pro · Toujours actif':'CamStudio Pro · Still running',
'Afficher CamStudio Pro':'Show CamStudio Pro','Quitter CamStudio Pro':'Exit CamStudio Pro',
'Connexion du téléphone':'Phone connection','Mode de connexion':'Connection mode',
'Adresse IP du téléphone (mode Wi-Fi)':'Phone IP address (Wi-Fi mode)',
'Contrôles de la caméra':'Camera controls',
'⟳ Changer caméra':'⟳ Switch camera',
'☼ Lampe OFF':'☼ Light OFF','☼ Lampe ON':'☼ Light ON',
'Zoom optique / numérique téléphone':'Phone optical / digital zoom',
'Qualité JPEG réseau':'Network JPEG quality',
'Exposition matérielle téléphone':'Phone exposure',
'Limite FPS réseau':'Network FPS limit',
'Réglages de l’image':'Image settings',
'Luminosité':'Brightness','Contraste':'Contrast','Saturation':'Saturation','Netteté':'Sharpness','Température':'Temperature',
'Recadrage / Zoom':'Crop / Zoom','Rotation':'Rotation',
'Cadrage et proportions':'Framing and aspect ratio',
'Contenir : image entière (bandes)':'Fit: whole image (letterbox)',
'Remplir : recadrer sans étirer':'Fill: crop without stretching',
'Réinitialiser cadrage et zoom':'Reset framing and zoom',
'Sur l’aperçu : molette = zoom, clic = centrage, glisser = déplacement':'Preview: wheel = zoom, click = center, drag = move',
'Effet miroir':'Mirror','Noir & blanc':'Black and white','Grille de composition':'Composition grid',
'Profils':'Profiles',
'Qualité de sortie / OBS / partage Discord':'Output quality / OBS / Discord sharing',
'Codec H.264 : évolution future':'H.264 codec: future feature',
'Qualité USB élevée : 1080p / JPEG 90':'USB high quality: 1080p / JPEG 90',
'USB via ADB : liaison locale plus stable. La résolution native et les FPS restent limités par le Samsung.':'USB over ADB is local and stable. Native resolution and FPS depend on the phone.',
'1440p/60 : format de sortie, pas promesse de 60 images natives. Pour Nitro utiliser Go Live / partage d’écran.':'1440p/60 is an output format, not guaranteed native capture. Use Go Live / screen share for Discord.',
'1080p / 30 FPS (agrandi si nécessaire)':'1080p / 30 FPS (upscaled if needed)',
'1440p / 60 FPS (agrandi si nécessaire)':'1440p / 60 FPS (upscaled if needed)',
'● HORS LIGNE':'● OFFLINE','● CONNECTÉ':'● CONNECTED',
'◉  Activer webcam virtuelle':'◉ Enable virtual camera','■  Arrêter webcam virtuelle':'■ Stop virtual camera',
'●  Enregistrer':'● Record','▧  Capture photo':'▧ Capture photo',
'◉   Caméra':'◉   Camera','◈   Studio':'◈   Studio',
'◉   Sortie webcam':'◉   Webcam output','▣   Profils':'▣   Profiles',
'PRO   /   VERSION 0.3.1':'PRO   /   VERSION 1.0',
'Diffusion locale uniquement':'Local streaming only',
'Enregistrement en pause':'Recording paused','Enregistrement repris dans le même fichier':'Recording resumed in same file',
'Vidéo enregistrée : ':'Video saved: ',
'Photo enregistrée : ':'Photo saved: ',
'Connecte la caméra avant l’enregistrement':'Connect the camera before recording',
'Pas encore d’image à capturer':'No image available to capture',
'Impossible d’enregistrer cette photo':'Could not save this photo',
'Connexion impossible : ':'Connection failed: ','Erreur de connexion : ':'Connection error: ',
'Erreur traitement vidéo : ':'Video processing error: ',
'USB détecté : saisis une fois la clé affichée sur Android.':'USB detected: enter the key shown on Android once.',
'Téléphone USB détecté : connexion automatique…':'USB phone detected: connecting automatically…',
'Connexion':'Connection','Caméra déconnectée':'Camera disconnected',
'Enregistrement en cours : ':'Recording in progress: ',
'Profils disponibles':'Available profiles',
'Enregistrer profil':'Save profile','Nouveau profil':'New profile','Nom du profil :':'Profile name:',
'Profils et compositions':'Profiles and layouts',
'Scène active :':'Active scene:','Nouvelle scène':'New scene','Renommer':'Rename',
'Dupliquer':'Duplicate','Supprimer':'Delete','Renommer la scène':'Rename scene',
'Nom de la scène :':'Scene name:','Supprimer la scène':'Delete scene',
'Caméra du téléphone':'Phone camera','Couleur unie':'Solid color',
'Arrière-plan :':'Background:','Transition :':'Transition:','Fondu':'Fade','Aucune':'None',
'Durée du fondu :':'Fade duration:',
'Ajouter du texte':'Add text','Ajouter un texte':'Add text','Ajouter une image':'Add image',
'Supprimer l’élément':'Remove element',
'Éléments de la scène (du bas vers le haut)':'Scene elements (back to front)',
'↑ Devant':'↑ Bring forward','↓ Derrière':'↓ Send backward',
'Propriétés de l’élément sélectionné':'Selected element properties',
'Visible':'Visible','Opacité':'Opacity','Taille du texte / largeur de l’image':'Text size / image width',
'Couleur du texte':'Text color','Couleur de fond de cette scène':'Scene background color',
'Personnaliser…':'Customize…',
'Choisir une couleur de fond active automatiquement « Couleur unie ». Pour revoir la caméra, sélectionne « Caméra du téléphone ».':'Choosing a background color enables Solid color. Select Phone camera to show video again.',
'Les scènes sont sauvegardées uniquement sur ce PC. Les sources caméra supplémentaires seront intégrées séparément.':'Scenes are saved on this PC only. Additional camera sources may be added later.',
'Caméra + textes + images : l’aperçu correspond à la scène envoyée aux sorties. Clique un élément et déplace-le directement sur l’image.':'Camera + text + images: the preview matches the output scene. Click and drag to position an element.',
'Mon titre':'My title','Texte affiché':'Display text','Texte à afficher :':'Text to display:',
'Image':'Image','Photo':'Photo',
'Bibliothèque des enregistrements':'Recording library',
'Photos et vidéos conservées sur cet ordinateur.':'Photos and videos stored on this computer.',
'Bibliothèque · ':'Library · ',
'Tous':'All','Vidéos':'Videos','Photos':'Photos',
'↻ Actualiser':'↻ Refresh','Ouvrir le dossier':'Open folder',
'Afficher plus d’enregistrements':'Show more recordings',
'Aucun enregistrement pour le moment.':'No recordings yet.',
'Utilise « Prendre une photo » ou « Démarrer la vidéo ».':'Use Take a photo or Start video.',
'Chargement…':'Loading…','Aperçu indisponible':'Preview unavailable',
'▶ Regarder':'▶ Watch','◉ Voir':'◉ View','Dossier':'Folder',
'▶ Lire':'▶ Play','⏸ Pause':'⏸ Pause','Fermer':'Close',
'Ouvrir avec Windows':'Open with Windows',
'Lecture de ':'Playing ','Lecture':'Playback',
'CamStudio Pro · Lecture · ':'CamStudio Pro · Playback · ',
'Ce fichier ne peut pas être lu ici. Utilise « Ouvrir avec Windows ». ':'Cannot play this file here. Try Open with Windows. ',
'Ce fichier n’existe plus. Actualise la bibliothèque.':'This file no longer exists. Refresh the library.',
'Fichier introuvable':'File not found',
'Impossible de lire cette photo.':'Could not open this photo.',
'CamStudio Pro · Photo · ':'CamStudio Pro · Photo · ',
'Couleur ':'Color ',
'Choisir une couleur personnalisée':'Choose a custom color',
'Sélecteur de couleur : ':'Color picker: ',
'Code couleur hexadécimal (exemple : #845CF7)':'Hex color code (example: #845CF7)',
'Valeur invalide : utilise #RRGGBB (exemple : #845CF7).':'Invalid value: use #RRGGBB (example: #845CF7).',
'Texte affiché':'Displayed text',
'Réception réelle : ':'Actual input: ',
'Source caméra : ':'Camera source: ',
'Flux en direct':'Live stream','Réglages image':'Image settings','Scènes personnalisées':'Custom scenes',
'OBS / Discord':'OBS / Discord',
'Contrôle vidéo • correction d’image • capture • webcam virtuelle':'Video controls • image correction • capture • virtual webcam',
'Studio caméra':'Camera studio',
'Préparation à une publication open source.':'Preparing for open-source publication.',
}

# Localized primary navigation, actions and Settings labels.
# Non-core technical descriptions fall back to English to avoid fabricating
# machine translations or breaking camera/device terminology.
CORE_KEYS=(
    'Home','Camera','Studio','Scenes','Outputs','Recording','Connections','Settings',
    'Overview','Camera studio','Image processing','Scene editor','My recordings',
    'Recording library','Phone connection','Usage mode','Enable advanced mode',
    'Appearance','Project and privacy','Connect','Disconnect','Connect camera',
    'Take photo','Start / stop video','⏸ Pause','▶ Resume',
    'New scene','Add text','Add image','Delete','Show key','Hide key',
    'Copy key','Language','Simple','Advanced','Virtual camera',
    'Refresh','Videos','Photos','All','Apply','Save profile','Open folder',
    'Status and quick actions','Output resolution','Background:','Text color',
    'Scene background color','Current mode: ','Recording: '
)
CORE_LOCAL={
'fr':(
    'Accueil','Caméra','Studio','Scènes','Sorties','Enregistrement','Connexions','Paramètres',
    'Vue d’ensemble','Studio caméra','Traitement d’image','Éditeur de scènes','Mes enregistrements',
    'Bibliothèque des enregistrements','Connexion du téléphone','Mode d’utilisation','Activer le mode avancé',
    'Apparence','Projet et confidentialité','Connecter','Déconnecter','Connecter la caméra',
    'Prendre une photo','Démarrer / arrêter la vidéo','⏸ Pause','▶ Reprendre',
    'Nouvelle scène','Ajouter du texte','Ajouter une image','Supprimer','Afficher la clé','Masquer la clé',
    'Copier la clé','Langue','Simple','Avancé','Webcam virtuelle',
    'Actualiser','Vidéos','Photos','Tous','Appliquer','Enregistrer profil','Ouvrir le dossier',
    'Statut et actions rapides','Résolution de sortie','Arrière-plan :','Couleur du texte',
    'Couleur de fond de cette scène','Mode actuel : ','Enregistrement : '
),
'zh':(
    '主页','摄像头','工作室','场景','输出','录制','连接','设置',
    '概览','摄像头工作室','图像处理','场景编辑器','我的录制',
    '录制库','手机连接','使用模式','启用高级模式',
    '外观','项目与隐私','连接','断开','连接摄像头',
    '拍照','开始/停止录制','⏸ 暂停','▶ 继续',
    '新建场景','添加文本','添加图片','删除','显示密钥','隐藏密钥',
    '复制密钥','语言','简单','高级','虚拟摄像头',
    '刷新','视频','照片','全部','应用','保存预设','打开文件夹',
    '状态与快捷操作','输出分辨率','背景：','文本颜色',
    '场景背景颜色','当前模式：','录制：'
),
'hi':(
    'होम','कैमरा','स्टूडियो','सीन','आउटपुट','रिकॉर्डिंग','कनेक्शन','सेटिंग्स',
    'अवलोकन','कैमरा स्टूडियो','छवि प्रोसेसिंग','सीन एडिटर','मेरी रिकॉर्डिंग',
    'रिकॉर्डिंग लाइब्रेरी','फ़ोन कनेक्शन','उपयोग मोड','एडवांस्ड मोड चालू करें',
    'दिखावट','परियोजना और गोपनीयता','कनेक्ट करें','डिस्कनेक्ट करें','कैमरा कनेक्ट करें',
    'फ़ोटो लें','वीडियो शुरू/बंद करें','⏸ रोकें','▶ फिर चलाएं',
    'नया सीन','टेक्स्ट जोड़ें','चित्र जोड़ें','हटाएं','कुंजी दिखाएं','कुंजी छिपाएं',
    'कुंजी कॉपी करें','भाषा','सरल','उन्नत','वर्चुअल कैमरा',
    'रीफ़्रेश','वीडियो','फ़ोटो','सभी','लागू करें','प्रोफ़ाइल सहेजें','फ़ोल्डर खोलें',
    'स्थिति और त्वरित कार्य','आउटपुट रिज़ॉल्यूशन','पृष्ठभूमि:','टेक्स्ट रंग',
    'सीन पृष्ठभूमि रंग','वर्तमान मोड: ','रिकॉर्डिंग: '
),
'es':(
    'Inicio','Cámara','Estudio','Escenas','Salidas','Grabación','Conexiones','Configuración',
    'Vista general','Estudio de cámara','Procesamiento de imagen','Editor de escenas','Mis grabaciones',
    'Biblioteca de grabaciones','Conexión del teléfono','Modo de uso','Activar modo avanzado',
    'Apariencia','Proyecto y privacidad','Conectar','Desconectar','Conectar cámara',
    'Tomar foto','Iniciar / detener vídeo','⏸ Pausa','▶ Reanudar',
    'Nueva escena','Añadir texto','Añadir imagen','Eliminar','Mostrar clave','Ocultar clave',
    'Copiar clave','Idioma','Simple','Avanzado','Cámara virtual',
    'Actualizar','Vídeos','Fotos','Todos','Aplicar','Guardar perfil','Abrir carpeta',
    'Estado y acciones rápidas','Resolución de salida','Fondo:','Color del texto',
    'Color de fondo de la escena','Modo actual: ','Grabación: '
),
'ar':(
    'الرئيسية','الكاميرا','الاستوديو','المشاهد','المخرجات','التسجيل','الاتصالات','الإعدادات',
    'نظرة عامة','استوديو الكاميرا','معالجة الصورة','محرر المشاهد','تسجيلاتي',
    'مكتبة التسجيلات','اتصال الهاتف','وضع الاستخدام','تفعيل الوضع المتقدم',
    'المظهر','المشروع والخصوصية','اتصال','قطع الاتصال','اتصال بالكاميرا',
    'التقاط صورة','بدء / إيقاف الفيديو','⏸ إيقاف مؤقت','▶ استئناف',
    'مشهد جديد','إضافة نص','إضافة صورة','حذف','إظهار المفتاح','إخفاء المفتاح',
    'نسخ المفتاح','اللغة','بسيط','متقدم','كاميرا افتراضية',
    'تحديث','فيديوهات','صور','الكل','تطبيق','حفظ الملف','فتح المجلد',
    'الحالة والإجراءات السريعة','دقة الإخراج','الخلفية:','لون النص',
    'لون خلفية المشهد','الوضع الحالي: ','التسجيل: '
),
'pt':(
    'Início','Câmera','Estúdio','Cenas','Saídas','Gravação','Conexões','Configurações',
    'Visão geral','Estúdio de câmera','Processamento de imagem','Editor de cenas','Minhas gravações',
    'Biblioteca de gravações','Conexão do celular','Modo de uso','Ativar modo avançado',
    'Aparência','Projeto e privacidade','Conectar','Desconectar','Conectar câmera',
    'Tirar foto','Iniciar / parar vídeo','⏸ Pausar','▶ Retomar',
    'Nova cena','Adicionar texto','Adicionar imagem','Excluir','Mostrar chave','Ocultar chave',
    'Copiar chave','Idioma','Simples','Avançado','Câmera virtual',
    'Atualizar','Vídeos','Fotos','Todos','Aplicar','Salvar perfil','Abrir pasta',
    'Status e ações rápidas','Resolução de saída','Fundo:','Cor do texto',
    'Cor de fundo da cena','Modo atual: ','Gravação: '
),
'bn':(
    'হোম','ক্যামেরা','স্টুডিও','দৃশ্য','আউটপুট','রেকর্ডিং','সংযোগ','সেটিংস',
    'সারসংক্ষেপ','ক্যামেরা স্টুডিও','ছবি প্রক্রিয়াকরণ','দৃশ্য সম্পাদক','আমার রেকর্ডিং',
    'রেকর্ডিং লাইব্রেরি','ফোন সংযোগ','ব্যবহার মোড','উন্নত মোড চালু করুন',
    'চেহারা','প্রকল্প ও গোপনীয়তা','সংযোগ করুন','বিচ্ছিন্ন করুন','ক্যামেরা সংযোগ করুন',
    'ছবি তুলুন','ভিডিও শুরু / বন্ধ','⏸ বিরতি','▶ চালু করুন',
    'নতুন দৃশ্য','লেখা যোগ করুন','ছবি যোগ করুন','মুছুন','চাবি দেখান','চাবি লুকান',
    'চাবি কপি করুন','ভাষা','সহজ','উন্নত','ভার্চুয়াল ক্যামেরা',
    'রিফ্রেশ','ভিডিও','ছবি','সব','প্রয়োগ করুন','প্রোফাইল সংরক্ষণ','ফোল্ডার খুলুন',
    'অবস্থা ও দ্রুত কাজ','আউটপুট রেজোলিউশন','পটভূমি:','লেখার রং',
    'দৃশ্যের পটভূমির রং','বর্তমান মোড: ','রেকর্ডিং: '
),
'ru':(
    'Главная','Камера','Студия','Сцены','Вывод','Запись','Подключения','Настройки',
    'Обзор','Студия камеры','Обработка изображения','Редактор сцен','Мои записи',
    'Библиотека записей','Подключение телефона','Режим работы','Включить расширенный режим',
    'Оформление','Проект и конфиденциальность','Подключить','Отключить','Подключить камеру',
    'Сделать фото','Начать / остановить видео','⏸ Пауза','▶ Продолжить',
    'Новая сцена','Добавить текст','Добавить изображение','Удалить','Показать ключ','Скрыть ключ',
    'Скопировать ключ','Язык','Простой','Расширенный','Виртуальная камера',
    'Обновить','Видео','Фото','Все','Применить','Сохранить профиль','Открыть папку',
    'Состояние и быстрые действия','Разрешение вывода','Фон:','Цвет текста',
    'Цвет фона сцены','Текущий режим: ','Запись: '
),
'ur':(
    'ہوم','کیمرہ','اسٹوڈیو','مناظر','آؤٹ پٹ','ریکارڈنگ','کنکشن','ترتیبات',
    'جائزہ','کیمرہ اسٹوڈیو','تصویر کی پروسیسنگ','منظر ایڈیٹر','میری ریکارڈنگز',
    'ریکارڈنگ لائبریری','فون کنکشن','استعمال کا موڈ','ایڈوانسڈ موڈ فعال کریں',
    'ظاہری شکل','پروجیکٹ اور رازداری','کنیکٹ','منقطع','کیمرہ کنیکٹ کریں',
    'تصویر لیں','ویڈیو شروع / بند','⏸ توقف','▶ دوبارہ چلائیں',
    'نیا منظر','متن شامل کریں','تصویر شامل کریں','حذف','کلید دکھائیں','کلید چھپائیں',
    'کلید کاپی کریں','زبان','آسان','جدید','ورچوئل کیمرہ',
    'تازہ کریں','ویڈیوز','تصاویر','سب','لاگو کریں','پروفائل محفوظ کریں','فولڈر کھولیں',
    'حالت اور فوری کام','آؤٹ پٹ ریزولوشن','پس منظر:','متن کا رنگ',
    'منظر کا پس منظر رنگ','موجودہ موڈ: ','ریکارڈنگ: '
),
'id':(
    'Beranda','Kamera','Studio','Adegan','Keluaran','Rekaman','Koneksi','Pengaturan',
    'Ringkasan','Studio kamera','Pemrosesan gambar','Editor adegan','Rekaman saya',
    'Perpustakaan rekaman','Koneksi ponsel','Mode penggunaan','Aktifkan mode lanjutan',
    'Tampilan','Proyek dan privasi','Hubungkan','Putuskan','Hubungkan kamera',
    'Ambil foto','Mulai / hentikan video','⏸ Jeda','▶ Lanjutkan',
    'Adegan baru','Tambah teks','Tambah gambar','Hapus','Tampilkan kunci','Sembunyikan kunci',
    'Salin kunci','Bahasa','Sederhana','Lanjutan','Kamera virtual',
    'Segarkan','Video','Foto','Semua','Terapkan','Simpan profil','Buka folder',
    'Status dan tindakan cepat','Resolusi keluaran','Latar belakang:','Warna teks',
    'Warna latar adegan','Mode saat ini: ','Rekaman: '
),
'ja':(
    'ホーム','カメラ','スタジオ','シーン','出力','録画','接続','設定',
    '概要','カメラスタジオ','画像処理','シーンエディター','マイ録画',
    '録画ライブラリ','スマートフォン接続','利用モード','詳細モードを有効化',
    '外観','プロジェクトとプライバシー','接続','切断','カメラを接続',
    '写真を撮る','録画開始 / 停止','⏸ 一時停止','▶ 再開',
    '新しいシーン','テキストを追加','画像を追加','削除','キーを表示','キーを隠す',
    'キーをコピー','言語','シンプル','詳細','仮想カメラ',
    '更新','動画','写真','すべて','適用','プロファイルを保存','フォルダーを開く',
    '状態とクイック操作','出力解像度','背景:','文字色',
    'シーンの背景色','現在のモード: ','録画: '
)
}
assert all(len(row)==len(CORE_KEYS) for row in CORE_LOCAL.values()),[(k,len(v)) for k,v in CORE_LOCAL.items()]

LOCALIZED={code:dict(zip(CORE_KEYS,row)) for code,row in CORE_LOCAL.items()}
# Additional common variant (icon-prefix) translations are based on canonical text.
# Suffix/prefix fragments in runtime status messages also pass through translate().

FR_EN.update({
    'CAMSTUDIO PRO\n\nAucune caméra connectée':'CAMSTUDIO PRO\n\nNo camera connected',
    'Aucune caméra connectée':'No camera connected',
    'Prêt — connecte ton application Android CamStudio Pro':'Ready — connect your CamStudio Pro Android app',
    '  ·  Mode avancé':'  ·  Advanced mode',
    '  ·  À venir':'  ·  Coming soon',
    ' vidéo(s), ':' video(s), ',
    ' photo(s)':' photo(s)',
})

def translate(text: str, code: str | None = None) -> str:
    source=str(text)
    language=code or ACTIVE
    if chr(10) in source:
        return chr(10).join(translate(part,language) for part in source.split(chr(10)))
    for ending in ('  ·  Mode avancé','  ·  À venir'):
        if source.endswith(ending) and source!=ending:
            return translate(source[:-len(ending)],language)+translate(ending,language)
    if source.startswith('Bibliothèque · ') and source!='Bibliothèque · ':
        tail=source[len('Bibliothèque · '):].replace('vidéo(s)','video(s)').replace('photo(s)','photo(s)')
        return translate('Bibliothèque · ',language)+tail
    icon_match=re.match(r'^([^\w\s]{1,3}\s+)(.+)$',source)
    if icon_match and source not in FR_EN:
        # Preserve decorative icons and translate the label itself.
        return icon_match.group(1)+translate(icon_match.group(2),language)
    english=FR_EN.get(source,source)
    if english==source:
        # Translate dynamic, preformatted status strings safely by a known prefix.
        for fr,en in sorted(FR_EN.items(), key=lambda kv: len(kv[0]), reverse=True):
            if len(fr)>5 and source.startswith(fr) and source!=fr and not fr.startswith(' '):
                english=en+source[len(fr):]
                break
    if language=='fr':
        if source in FR_EN:
            return source
        if english!=source:
            return source
        return LOCALIZED['fr'].get(source,source)
    if language=='en':
        return english
    catalog=LOCALIZED.get(language,{})
    return catalog.get(english,english)


def _widget_text(widget,language):
    source=widget.property('_cs_original_text')
    previous=widget.property('_cs_last_translation')
    displayed=widget.text()
    if not isinstance(source,str) or (isinstance(previous,str) and displayed!=previous):
        source=displayed
        widget.setProperty('_cs_original_text',source)
    target=translate(source,language)
    if displayed!=target:
        widget.setText(target)
    widget.setProperty('_cs_last_translation',target)


def _placeholder_text(widget,language):
    displayed=widget.placeholderText()
    source=widget.property('_cs_original_placeholder')
    old=widget.property('_cs_last_placeholder')
    if not isinstance(source,str) or (isinstance(old,str) and displayed!=old):
        source=displayed
        widget.setProperty('_cs_original_placeholder',source)
    result=translate(source,language)
    if displayed!=result:
        widget.setPlaceholderText(result)
    widget.setProperty('_cs_last_placeholder',result)


def _items_text(combo,language):
    # Device/recording format identifiers or user profiles must not be translated.
    original=combo.property('_cs_original_items')
    if not isinstance(original,list) or len(original)!=combo.count():
        original=[combo.itemText(i) for i in range(combo.count())]
        combo.setProperty('_cs_original_items',original)
    changed=False
    old=combo.blockSignals(True)
    for i,source in enumerate(original):
        target=translate(source,language)
        if combo.itemText(i)!=target:
            combo.setItemText(i,target)
            changed=True
    combo.blockSignals(old)


def apply_tree(root,code):
    global ACTIVE
    if code not in SUPPORTED:
        code='en'
    ACTIVE=code
    for cls in (QLabel,QPushButton,QCheckBox,QGroupBox):
        for widget in root.findChildren(cls):
            _widget_text(widget,code)
    for w in root.findChildren(QLineEdit):
        _placeholder_text(w,code)
    for w in root.findChildren(QComboBox):
        if w.property('_cs_translate_items'):
            _items_text(w,code)

