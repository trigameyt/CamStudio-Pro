package com.camstudio.pro;

import android.Manifest;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.app.Service;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.BatteryManager;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.ImageFormat;
import android.graphics.Rect;
import android.graphics.YuvImage;
import android.hardware.Camera;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Enumeration;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.pm.ServiceInfo;
import android.graphics.SurfaceTexture;
import android.net.wifi.WifiManager;
import android.os.PowerManager;
/** Active foreground camera capture with an always-visible notification.
 * Service owns camera and HTTP socket, never the Activity. */
@SuppressWarnings("deprecation")
public class CameraService extends Service {
    public static final String ACTION_START="com.camstudio.pro.START";
    public static final String ACTION_STOP="com.camstudio.pro.STOP";
    private static final int PORT=8765;
    private static final int NOTIFICATION_ID=4215;
    private static final String CHANNEL="camstudio_capture";
    private static volatile CameraService instance;
    public static CameraService current(){return instance;}
    private final Object frameLock=new Object();
    private final AtomicInteger clientCount=new AtomicInteger(0);
    private final Handler ui=new Handler(Looper.getMainLooper());
    private volatile byte[] latestJpeg;
    private volatile long frameSerial=0;
    private volatile boolean streaming=false;
    private volatile int frameQuality=75,maxFramesPerSecond=25,requestedHeight=720;
    private volatile int currentSourceWidth=0,currentSourceHeight=0,previewFpsRangeMax=0;
    private volatile ServerSocket httpServer;
    private volatile String accessKey;
    private volatile String status="Prête";
    private long lastEncodedAt=0;
    private Camera camera;
    private SurfaceTexture surfaceTexture;
    private int cameraId=-1;
    private PowerManager.WakeLock cpuLock;
    private WifiManager.WifiLock wifiLock;
    public boolean isStreaming(){return streaming;}
    public String getKey(){return accessKey;}
    public String getStatus(){return status;}
    public String getAddress(){return wifiIp();}
    public byte[] getLatestJpeg(){return latestJpeg;}
    public int getBattery(){return batteryLevel();}
    public boolean isCharging(){return batteryCharging();}
    public void setStatus(String msg){status=msg;android.util.Log.i("CamStudio",msg);}
    @Override public android.os.IBinder onBind(Intent intent){return null;}
    @Override public void onCreate(){
        super.onCreate();
        instance=this;
        // Pairing survives camera restarts; the old temporary key forced
        // re-pairing after every Android process restart.
        accessKey=getSharedPreferences("pairing",MODE_PRIVATE)
                .getString("access_key",null);
        if(accessKey==null || !accessKey.matches("[A-F0-9]{32}")){
            accessKey=newAccessKey();
            getSharedPreferences("pairing",MODE_PRIVATE).edit()
                .putString("access_key",accessKey).apply();
        }
        NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL,"CamStudio - caméra active",NotificationManager.IMPORTANCE_LOW));
    }
    private Notification notification(){
        Intent open=new Intent(this,MainActivity.class);
        open.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent show=PendingIntent.getActivity(this,1,open,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Intent stop=new Intent(this,CameraService.class).setAction(ACTION_STOP);
        PendingIntent shut=PendingIntent.getService(this,2,stop,PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        return new Notification.Builder(this,CHANNEL)
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setContentTitle("CamStudio Pro · Caméra en direct")
            .setContentText("Caméra active pour le PC · Appuyer pour les réglages")
            .setContentIntent(show)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel,"Arrêter",shut)
            .setOngoing(true)
            .setCategory(Notification.CATEGORY_SERVICE)
            .build();
    }
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        if(intent!=null && ACTION_STOP.equals(intent.getAction())){
            stopSelf();
            return START_NOT_STICKY;
        }
        if(streaming)return START_NOT_STICKY;
        try{
            if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){
                setStatus("Autorisation caméra nécessaire");stopSelf();return START_NOT_STICKY;
            }
            if(android.os.Build.VERSION.SDK_INT>=29)
                startForeground(NOTIFICATION_ID,notification(),ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA);
            else startForeground(NOTIFICATION_ID,notification());
            acquireLocks();
            openCamera();
            if(camera!=null)startServer();
            else {stopSelf();return START_NOT_STICKY;}
        }catch(Exception e){
            setStatus("Erreur de démarrage : "+e);
            android.util.Log.e("CamStudio","Foreground camera start failed",e);
            stopSelf();
        }
        return START_NOT_STICKY;
    }
    private void acquireLocks(){
        PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);
        cpuLock=pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"CamStudioPro:CameraCPU");
        cpuLock.acquire();
        WifiManager wm=(WifiManager)getApplicationContext().getSystemService(WIFI_SERVICE);
        if(wm!=null){
            wifiLock=wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF,"CamStudioPro:WiFi");
            wifiLock.acquire();
        }
    }
    private void releaseLocks(){
        if(wifiLock!=null && wifiLock.isHeld())wifiLock.release();
        if(cpuLock!=null && cpuLock.isHeld())cpuLock.release();
    }
    @Override public void onDestroy(){
        stopServer();releaseCamera();releaseLocks();instance=null;
        super.onDestroy();
    }
    private int batteryLevel() {
        try {
            Intent state=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if(state != null) {
                int level=state.getIntExtra(BatteryManager.EXTRA_LEVEL,-1);
                int scale=state.getIntExtra(BatteryManager.EXTRA_SCALE,100);
                if(level>=0 && scale>0)return Math.min(100,Math.max(0,Math.round(level*100f/scale)));
            }
            BatteryManager manager=(BatteryManager)getSystemService(BATTERY_SERVICE);
            return manager == null ? -1 : manager.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
        }catch(Exception e) {return -1;}
    }

    private boolean batteryCharging() {
        try {
            Intent state=registerReceiver(null,new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
            if(state == null)return false;
            int status=state.getIntExtra(BatteryManager.EXTRA_STATUS,-1);
            return status==BatteryManager.BATTERY_STATUS_CHARGING || status==BatteryManager.BATTERY_STATUS_FULL;
        }catch(Exception e) {return false;}
    }

    public synchronized void regenerateAccessKey(){
        String changed=newAccessKey();
        getSharedPreferences("pairing",MODE_PRIVATE).edit()
            .putString("access_key",changed).apply();
        accessKey=changed;
    }

    private String newAccessKey() {
        byte[] bytes=new byte[16]; new SecureRandom().nextBytes(bytes);
        StringBuilder sb=new StringBuilder();
        for(byte b: bytes) sb.append(String.format(Locale.US,"%02X",b & 0xff));
        return sb.toString();
    }

    private String wifiIp() {
        try {
            Enumeration<NetworkInterface> ni=NetworkInterface.getNetworkInterfaces();
            while(ni.hasMoreElements()) {
                NetworkInterface iface=ni.nextElement();
                if(!iface.isUp() || iface.isLoopback() || iface.isVirtual()) continue;
                String n=iface.getName().toLowerCase(Locale.ROOT);
                if(!(n.contains("wlan") || n.contains("wifi") || n.contains("ap"))) continue;
                Enumeration<InetAddress> addresses=iface.getInetAddresses();
                while(addresses.hasMoreElements()) {
                    InetAddress a=addresses.nextElement();
                    if(a instanceof Inet4Address && !a.isLoopbackAddress()) return a.getHostAddress();
                }
            }
        } catch (Exception ignored) {}
        return "IP Wi-Fi introuvable";
    }

    private int chooseCamera(int facing) {
        Camera.CameraInfo info=new Camera.CameraInfo();
        for(int i=0;i<Camera.getNumberOfCameras();i++){
            Camera.getCameraInfo(i,info);
            if(info.facing==facing) return i;
        }
        return Camera.getNumberOfCameras()>0?0:-1;
    }

    private void openCamera() {
        if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED) return;
        releaseCamera();
        if(cameraId<0) cameraId=chooseCamera(Camera.CameraInfo.CAMERA_FACING_BACK);
        if(cameraId<0) { setStatus("Aucune caméra détectée");return; }
        try {
            Camera opened=Camera.open(cameraId);
            Camera.Parameters p=opened.getParameters();
            Camera.Size best=null;
            for(Camera.Size sz:p.getSupportedPreviewSizes()){
                int requestedWidth=requestedHeight*16/9;
                double diff=Math.abs(sz.width*1.0/sz.height-16.0/9.0)*3000+Math.abs(sz.width-requestedWidth)+Math.abs(sz.height-requestedHeight);
                if(best==null || diff < Math.abs(best.width*1.0/best.height-16.0/9.0)*3000+Math.abs(best.width-requestedWidth)+Math.abs(best.height-requestedHeight))best=sz;
            }
            if(best!=null) {
                p.setPreviewSize(best.width,best.height);
                currentSourceWidth=best.width;currentSourceHeight=best.height;
            }
            // Request up to 60 FPS only when the device advertises a suitable range.
            int[] selectedRange=null;
            int desired=maxFramesPerSecond*1000;
            for(int[] range:p.getSupportedPreviewFpsRange()) {
                if(selectedRange==null || Math.abs(range[1]-desired)<Math.abs(selectedRange[1]-desired)) selectedRange=range;
            }
            if(selectedRange!=null) {
                p.setPreviewFpsRange(selectedRange[0],selectedRange[1]);
                previewFpsRangeMax=selectedRange[1]/1000;
            }
            p.setPreviewFormat(ImageFormat.NV21);
            List<String> focus=p.getSupportedFocusModes();
            if(focus!=null && focus.contains(Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO))p.setFocusMode(Camera.Parameters.FOCUS_MODE_CONTINUOUS_VIDEO);
            opened.setParameters(p);
            opened.setDisplayOrientation(90);
            surfaceTexture = new SurfaceTexture(0);
            opened.setPreviewTexture(surfaceTexture);
            opened.setPreviewCallback((data,c)->{
                if(!streaming || data==null) return;
                long now=android.os.SystemClock.elapsedRealtime();
                if(now-lastEncodedAt < 1000/Math.max(5,maxFramesPerSecond))return;
                lastEncodedAt=now;
                try {
                    Camera.Size s=c.getParameters().getPreviewSize();
                    YuvImage yuv=new YuvImage(data,ImageFormat.NV21,s.width,s.height,null);
                    ByteArrayOutputStream buffer=new ByteArrayOutputStream(150000);
                    if(yuv.compressToJpeg(new Rect(0,0,s.width,s.height),frameQuality,buffer)){
                        synchronized(frameLock){latestJpeg=buffer.toByteArray();frameSerial++;frameLock.notifyAll();}
                    }
                } catch (RuntimeException ignored) { }
            });
            opened.startPreview();
            camera=opened;
            setStatus(streaming?"● Diffusion active":"● Caméra prête");
        } catch(Exception ex) {setStatus("Caméra indisponible : "+ex.getMessage());releaseCamera();}
    }

    private void releaseCamera() {
        if(camera!=null){
            try {camera.setPreviewCallback(null);camera.stopPreview();camera.release();} catch(Exception ignored) {}
            camera=null;
        }
        if(surfaceTexture!=null){surfaceTexture.release();surfaceTexture=null;}
    }

    public void switchCamera() {
        int front=chooseCamera(Camera.CameraInfo.CAMERA_FACING_FRONT);
        int back=chooseCamera(Camera.CameraInfo.CAMERA_FACING_BACK);
        cameraId=(cameraId==back && front>=0)?front:back;
        openCamera();
    }

    private void startServer() {
        if(camera==null){setStatus("Autorise la caméra puis réessaie.");return;}
        if(streaming) return;
        try {
            ServerSocket ss=new ServerSocket(PORT);
            ss.setReuseAddress(true);
            httpServer=ss;streaming=true;

            setStatus("● Diffusion active");

            Thread loop=new Thread(()->{
                while(streaming && !ss.isClosed()){
                    try {
                        Socket sock=ss.accept();
                        Thread t=new Thread(()->handleClient(sock),"client-camstudio");t.setDaemon(true);t.start();
                    } catch(Exception e){if(streaming) android.util.Log.w("CamStudio","Accept error",e);}
                }
            },"camstudio-server");loop.setDaemon(true);loop.start();
        } catch(Exception e){setStatus("Impossible d'ouvrir le port 8765 : "+e.getMessage());}
    }

    private void stopServer() {
        streaming=false;
        try{if(httpServer!=null)httpServer.close();}catch(Exception ignored){}
        httpServer=null;

        setStatus("● Diffusion arrêtée");
        synchronized(frameLock){frameLock.notifyAll();}
    }

    private String readRequestBody(BufferedReader reader, int length) throws Exception {
        if(length<1 || length>2048)return "{}";
        char[] data=new char[length];int n=0;
        while(n<length){int next=reader.read(data,n,length-n);if(next<0)break;n+=next;}
        return new String(data,0,n);
    }

    private void handleClient(Socket socket) {
        try (Socket sock=socket){
            sock.setSoTimeout(10000);
            BufferedReader reader=new BufferedReader(new InputStreamReader(sock.getInputStream(),StandardCharsets.US_ASCII));
            String line=reader.readLine();if(line==null)return;
            String[] parts=line.split(" ");if(parts.length<2)return;
            String method=parts[0],path=parts[1];
            int length=0;
            while((line=reader.readLine())!=null && !line.isEmpty()) {
                if(line.toLowerCase(Locale.ROOT).startsWith("content-length:")){
                    try{length=Integer.parseInt(line.substring(15).trim());}catch(Exception ignored){}
                }
            }
            Uri uri=Uri.parse(path);
            String body="POST".equals(method)?readRequestBody(reader,length):"{}";
            OutputStream out=sock.getOutputStream();
            String key=uri.getQueryParameter("key");
            if(!accessKey.equals(key)) {reply(out,403,"{\"error\":\"bad_key\"}");return;}
            if("/video".equals(uri.getPath()) && "GET".equals(method)) {
                if(!streaming){reply(out,503,"{\"error\":\"offline\"}");return;}
                out.write(("HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=camstudio\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));
                clientCount.incrementAndGet();
                long last=-1;
                try {
                    while(streaming && !sock.isClosed()) {
                        byte[] jpg;
                        synchronized(frameLock){
                            if(frameSerial==last || latestJpeg==null)frameLock.wait(1000);
                            if(frameSerial==last || latestJpeg==null)continue;
                            jpg=latestJpeg;last=frameSerial;
                        }
                        byte[] headers=("--camstudio\r\nContent-Type: image/jpeg\r\nContent-Length: "+jpg.length+"\r\n\r\n").getBytes(StandardCharsets.US_ASCII);
                        out.write(headers);out.write(jpg);out.write("\r\n".getBytes(StandardCharsets.US_ASCII));out.flush();
                    }
                }finally{clientCount.decrementAndGet();}
            }else if("/status".equals(uri.getPath()) && "GET".equals(method)) {
                JSONObject j=new JSONObject();j.put("app","CamStudioPro");j.put("streaming",streaming);j.put("clients",clientCount.get());j.put("quality",frameQuality);j.put("fps_limit",maxFramesPerSecond);
                j.put("battery_percent",batteryLevel());j.put("battery_charging",batteryCharging());
                j.put("source_width",currentSourceWidth);j.put("source_height",currentSourceHeight);
                j.put("preview_fps_max",previewFpsRangeMax);
                reply(out,200,j.toString());
            }else if("/control".equals(uri.getPath()) && "POST".equals(method)) {
                JSONObject j=new JSONObject(body);String action=j.optString("action");String value=j.optString("value");
                if(!action.matches("zoom|quality|fps|torch|exposure|switch|resolution")) {reply(out,400,"{\"error\":\"unknown_control\"}");return;}
                if("quality".equals(action))frameQuality=clamp(toInt(value,75),40,95);
                else if("fps".equals(action)) {
                    maxFramesPerSecond=clamp(toInt(value,25),5,60);
                    ui.post(()->openCamera());
                }
                else if("resolution".equals(action)) {
                    int wanted=toInt(value,720);
                    if(wanted!=720 && wanted!=1080 && wanted!=1440){reply(out,400,"{\"error\":\"invalid_resolution\"}");return;}
                    requestedHeight=wanted;
                    ui.post(()->openCamera());
                }
                else ui.post(()->cameraControl(action,value));
                reply(out,200,"{\"ok\":true}");
            }else {reply(out,404,"{\"error\":\"not_found\"}");}
        }catch(Exception ignored){ }
    }

    private static int toInt(String s,int fallback){try{return Integer.parseInt(s);}catch(Exception e){return fallback;}}
    private static int clamp(int v,int a,int b){return Math.max(a,Math.min(v,b));}
    private void cameraControl(String action, String value) {
        if("switch".equals(action)) { switchCamera();return; }
        if(camera==null)return;
        try {
            Camera.Parameters p=camera.getParameters();
            switch(action) {
                case "zoom": if(p.isZoomSupported())p.setZoom(clamp(Math.round(p.getMaxZoom()*clamp(toInt(value,0),0,100)/100f),0,p.getMaxZoom()));break;
                case "torch":
                    List<String> modes=p.getSupportedFlashModes();
                    if(modes!=null && modes.contains(Camera.Parameters.FLASH_MODE_TORCH))p.setFlashMode("1".equals(value)?Camera.Parameters.FLASH_MODE_TORCH:Camera.Parameters.FLASH_MODE_OFF);
                    break;
                case "exposure":
                    int mapped=p.getMinExposureCompensation() + (int)((p.getMaxExposureCompensation()-p.getMinExposureCompensation())*clamp(toInt(value,50),0,100)/100f);
                    p.setExposureCompensation(mapped);break;
            }
            camera.setParameters(p);
        }catch(Exception e){android.util.Log.w("CamStudio","Unsupported camera control: "+action,e);}
    }

    private void reply(OutputStream out,int code,String json)throws Exception {
        String txt=code==200?"OK":code==403?"Forbidden":code==400?"Bad Request":code==503?"Unavailable":"Not Found";
        byte[] b=json.getBytes(StandardCharsets.UTF_8);
        String header="HTTP/1.1 "+code+" "+txt+"\r\nContent-Type: application/json; charset=utf-8\r\nCache-Control: no-store\r\nContent-Length: "+b.length+"\r\nConnection: close\r\n\r\n";
        out.write(header.getBytes(StandardCharsets.US_ASCII));out.write(b);out.flush();
    }

}
