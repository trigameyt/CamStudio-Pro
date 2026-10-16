package com.camstudio.pro;

import java.util.HashMap;
import java.util.Map;

/** Offline Android companion UI strings; English first, user-selected language. */
public final class AppStrings {
    private AppStrings() {}
    public static final String[] CODES={
        "en","fr","zh","hi","es","ar","pt","bn","ru","ur","id","ja"
    };
    public static final String[] NAMES={
        "English","Français","简体中文","हिन्दी","Español","العربية",
        "Português","বাংলা","Русский","اردو","Bahasa Indonesia","日本語"
    };
    private static final String[] KEYS={
        "language","start","stop","active","stopped","switch",
        "copy","regen","battery","charging","key","port","ip",
        "wait","granted","subtitle","background","note",
        "regenTitle","regenBody","cancel","confirm"
    };
    private static final Map<String,String[]> DATA=new HashMap<>();
    static {
        DATA.put("en",new String[]{
            "Language","Start streaming","Stop streaming","● Streaming active","● Streaming stopped","Switch front / rear camera",
            "Copy address and key","Regenerate pairing key","Battery","charging","KEY","PORT","IP",
            "Start streaming to generate a pairing key.","Camera permission granted · Start streaming",
            "ANDROID CAMERA · VERSION 1.0","Video may continue in the background or with the screen locked, with a permanent notification.",
            "Stop streaming here or via the Android notification. The camera never starts automatically without permission.",
            "Regenerate pairing key?","You must enter the new key in the Windows app. Connections with the old key will be rejected.","Cancel","Regenerate"
        });
        DATA.put("fr",new String[]{
            "Langue","Démarrer la diffusion","Arrêter la diffusion","● Diffusion active","● Diffusion arrêtée","Changer caméra avant / arrière",
            "Copier l’adresse et la clé","Régénérer la clé","Batterie","en charge","CLÉ","PORT","IP",
            "Démarre la diffusion pour générer une clé.","Caméra autorisée · Démarre la diffusion",
            "CAMÉRA ANDROID · VERSION 1.0","La diffusion peut continuer en arrière-plan et écran verrouillé, avec une notification permanente.",
            "Arrête la diffusion ici ou via la notification. Aucun démarrage automatique sans autorisation.",
            "Régénérer la clé ?","Saisis ensuite la nouvelle clé sous Windows. Les connexions avec l’ancienne clé seront refusées.","Annuler","Régénérer"
        });
        DATA.put("zh",new String[]{"语言","开始直播","停止直播","● 正在直播","● 已停止直播","切换前后摄像头","复制地址和密钥","重新生成密钥","电量","充电中","密钥","端口","IP"});
        DATA.put("hi",new String[]{"भाषा","प्रसारण शुरू करें","प्रसारण रोकें","● प्रसारण चालू","● प्रसारण बंद","आगे/पीछे कैमरा बदलें","पता और कुंजी कॉपी करें","नई कुंजी बनाएं","बैटरी","चार्ज हो रहा है","कुंजी","पोर्ट","IP"});
        DATA.put("es",new String[]{"Idioma","Iniciar transmisión","Detener transmisión","● Transmisión activa","● Transmisión detenida","Cambiar cámara frontal/trasera","Copiar dirección y clave","Regenerar clave","Batería","cargando","CLAVE","PUERTO","IP"});
        DATA.put("ar",new String[]{"اللغة","بدء البث","إيقاف البث","● البث نشط","● توقف البث","تبديل الكاميرا الأمامية/الخلفية","نسخ العنوان والمفتاح","تجديد المفتاح","البطارية","جار الشحن","المفتاح","المنفذ","IP"});
        DATA.put("pt",new String[]{"Idioma","Iniciar transmissão","Parar transmissão","● Transmissão ativa","● Transmissão parada","Alternar câmera frontal/traseira","Copiar endereço e chave","Gerar nova chave","Bateria","carregando","CHAVE","PORTA","IP"});
        DATA.put("bn",new String[]{"ভাষা","সম্প্রচার শুরু","সম্প্রচার বন্ধ","● সম্প্রচার চলছে","● সম্প্রচার বন্ধ","সামনের/পিছনের ক্যামেরা বদল","ঠিকানা ও চাবি কপি","নতুন চাবি তৈরি","ব্যাটারি","চার্জ হচ্ছে","চাবি","পোর্ট","IP"});
        DATA.put("ru",new String[]{"Язык","Начать трансляцию","Остановить трансляцию","● Трансляция идёт","● Трансляция остановлена","Сменить камеру","Копировать адрес и ключ","Создать новый ключ","Батарея","зарядка","КЛЮЧ","ПОРТ","IP"});
        DATA.put("ur",new String[]{"زبان","نشریات شروع","نشریات بند","● نشریات جاری","● نشریات بند","اگلا/پچھلا کیمرہ بدلیں","پتہ اور کلید کاپی","نئی کلید بنائیں","بیٹری","چارج ہو رہی ہے","کلید","پورٹ","IP"});
        DATA.put("id",new String[]{"Bahasa","Mulai siaran","Hentikan siaran","● Siaran aktif","● Siaran berhenti","Ganti kamera depan/belakang","Salin alamat dan kunci","Buat ulang kunci","Baterai","mengisi daya","KUNCI","PORT","IP"});
        DATA.put("ja",new String[]{"言語","配信開始","配信停止","● 配信中","● 配信停止","前面/背面カメラ切替","アドレスとキーをコピー","キーを再発行","バッテリー","充電中","キー","ポート","IP"});
    }
    public static int index(String code){
        for(int i=0;i<CODES.length;i++)if(CODES[i].equals(code))return i;
        return 0;
    }
    public static String text(String code,String key){
        int i=-1;
        for(int j=0;j<KEYS.length;j++)if(KEYS[j].equals(key)){i=j;break;}
        if(i<0)return key;
        String[] values=DATA.get(code);
        if(values==null||i>=values.length)return DATA.get("en")[i];
        return values[i];
    }
}
