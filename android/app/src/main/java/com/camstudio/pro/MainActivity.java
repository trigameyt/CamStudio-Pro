package com.camstudio.pro;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.ClipboardManager;
import android.content.ClipData;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.widget.Button;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.AdapterView;
import android.view.View;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class MainActivity extends Activity {
    private final Handler ui=new Handler(Looper.getMainLooper());
    private TextView statusText,batteryText,endpointText;
    private TextView subtitleText,backgroundInfo,stopInfo,languageTitle;
    private Button streamButton,switcher,copy,regenerate;
    private String language="en";
    private String t(String key){return AppStrings.text(language,key);}
    private void setLanguage(String code){
        language=code;
        getSharedPreferences("interface",MODE_PRIVATE).edit().putString("language",language).apply();
        if(subtitleText!=null)subtitleText.setText(t("subtitle"));
        if(languageTitle!=null)languageTitle.setText(t("language"));
        if(backgroundInfo!=null)backgroundInfo.setText(t("background"));
        if(stopInfo!=null)stopInfo.setText(t("note"));
        if(switcher!=null)switcher.setText(t("switch"));
        if(copy!=null)copy.setText(t("copy"));
        if(regenerate!=null)regenerate.setText(t("regen"));
        CameraService service=CameraService.current();
        boolean active=service!=null && service.isStreaming();
        if(streamButton!=null)streamButton.setText(t(active?"stop":"start"));
        if(statusText!=null)statusText.setText(t(active?"active":"stopped"));
    }
    private ImageView preview;
    private boolean visible=false;
    private final Runnable update=new Runnable(){
        @Override public void run(){
            if(!visible)return;
            CameraService service=CameraService.current();
            if(service!=null){
                boolean active=service.isStreaming();
                statusText.setText(active?t("active"):service.getStatus());
                streamButton.setText(t(active?"stop":"start"));
                endpointText.setText(t("ip")+" : "+service.getAddress()+"\n"+t("port")+" : 8765\n"+t("key")+" : "+service.getKey());
                batteryText.setText(t("battery")+" : "+service.getBattery()+" %"+(service.isCharging()?" · "+t("charging"):""));
                byte[] jpeg=service.getLatestJpeg();
                if(active && jpeg!=null){
                    Bitmap frame=BitmapFactory.decodeByteArray(jpeg,0,jpeg.length);
                    if(frame!=null)preview.setImageBitmap(frame);
                }
            }else{
                statusText.setText(t("stopped"));
                streamButton.setText(t("start"));
                endpointText.setText(t("wait"));
                preview.setImageDrawable(null);
            }
            ui.postDelayed(this,500);
        }
    };
    private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}
    private TextView txt(String value,int size,int color){
        TextView t=new TextView(this);t.setText(value);t.setTextColor(color);t.setTextSize(size);
        t.setPadding(dp(2),dp(7),dp(2),dp(7));return t;
    }
    private Button button(String value){
        Button b=new Button(this);b.setText(value);b.setAllCaps(false);
        b.setTextColor(Color.WHITE);
        GradientDrawable shape=new GradientDrawable();
        shape.setColor(0xff916bf9);shape.setCornerRadius(dp(12));
        b.setBackground(shape);return b;
    }
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        language=getSharedPreferences("interface",MODE_PRIVATE).getString("language","en");
        ScrollView scroll=new ScrollView(this);
        scroll.setFillViewport(true);scroll.setBackgroundColor(0xff10121d);
        LinearLayout root=new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(20),dp(28),dp(20),dp(28));
        scroll.addView(root);setContentView(scroll);
        TextView title=txt("◉  CAMSTUDIO PRO",25,Color.WHITE);
        title.setTypeface(null,Typeface.BOLD);root.addView(title);
        subtitleText=txt(t("subtitle"),11,0xffa4a7bd);
        root.addView(subtitleText);
        languageTitle=txt(t("language"),13,0xffa4a7bd);
        root.addView(languageTitle);
        Spinner languagePicker=new Spinner(this);
        ArrayAdapter<String> languages=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,AppStrings.NAMES);
        languagePicker.setAdapter(languages);
        languagePicker.setSelection(AppStrings.index(language),false);
        root.addView(languagePicker);
        languagePicker.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(AdapterView<?> parent,View view,int position,long id){
                setLanguage(AppStrings.CODES[position]);
            }
            @Override public void onNothingSelected(AdapterView<?> parent){}
        });
        preview=new ImageView(this);
        preview.setScaleType(ImageView.ScaleType.FIT_CENTER);
        preview.setBackgroundColor(0xff090b13);
        LinearLayout.LayoutParams pp=new LinearLayout.LayoutParams(-1,dp(240));
        pp.topMargin=dp(16);pp.bottomMargin=dp(12);root.addView(preview,pp);
        statusText=txt(t("stopped"),16,0xffd5d5e2);root.addView(statusText);
        batteryText=txt(t("battery")+" : -- %",13,0xffa1a7b9);root.addView(batteryText);
        endpointText=txt(t("wait"),16,Color.WHITE);root.addView(endpointText);
        backgroundInfo=txt(t("background"),13,0xffa0a7c5);root.addView(backgroundInfo);
        streamButton=button(t("start"));
        LinearLayout.LayoutParams bp=new LinearLayout.LayoutParams(-1,dp(55));bp.topMargin=dp(20);
        root.addView(streamButton,bp);
        streamButton.setOnClickListener(v->{
            CameraService current=CameraService.current();
            if(current!=null && current.isStreaming()){
                Intent stop=new Intent(this,CameraService.class).setAction(CameraService.ACTION_STOP);
                startService(stop);
            }else if(checkSelfPermission(Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED){
                Intent start=new Intent(this,CameraService.class).setAction(CameraService.ACTION_START);
                startForegroundService(start);
            }else requestPermissions(new String[]{Manifest.permission.CAMERA},200);
        });
        switcher=button(t("switch"));
        LinearLayout.LayoutParams sp=new LinearLayout.LayoutParams(-1,dp(54));sp.topMargin=dp(12);
        root.addView(switcher,sp);
        switcher.setOnClickListener(v->{
            CameraService service=CameraService.current();
            if(service!=null && service.isStreaming()) service.switchCamera();
        });
        copy=button(t("copy"));
        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(-1,dp(54));cp.topMargin=dp(12);
        root.addView(copy,cp);
        copy.setOnClickListener(v->{
            CameraService service=CameraService.current();
            if(service==null || !service.isStreaming())return;
            ClipboardManager cm=(ClipboardManager)getSystemService(CLIPBOARD_SERVICE);
            cm.setPrimaryClip(ClipData.newPlainText("CamStudio",service.getAddress()+":8765\n"+service.getKey()));
        });
        regenerate=button(t("regen"));
        LinearLayout.LayoutParams rp=new LinearLayout.LayoutParams(-1,dp(52));
        rp.topMargin=dp(12);
        root.addView(regenerate,rp);
        regenerate.setOnClickListener(v->{
            CameraService service=CameraService.current();
            if(service==null)return;
            new android.app.AlertDialog.Builder(this)
                .setTitle(t("regenTitle"))
                .setMessage(t("regenBody"))
                .setNegativeButton(t("cancel"),null)
                .setPositiveButton(t("confirm"),(dialog,which)->service.regenerateAccessKey())
                .show();
        });
        root.addView(txt("The pairing key is stored on this phone. Use Regenerate if compromised. Unencrypted Wi-Fi HTTP is only for a private network.",12,0xffa0a7c5));
        stopInfo=txt(t("note"),12,0xffa0a7c5);root.addView(stopInfo);
        if(checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.CAMERA},200);
    }
    @Override public void onRequestPermissionsResult(int code,String[] perms,int[] results){
        super.onRequestPermissionsResult(code,perms,results);
        if(code==200 && results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED)
            statusText.setText(t("granted"));
    }
    @Override protected void onResume(){super.onResume();visible=true;ui.post(update);}
    @Override protected void onPause(){visible=false;ui.removeCallbacks(update);super.onPause();}
    @Override protected void onDestroy(){ui.removeCallbacks(update);super.onDestroy();}
}
