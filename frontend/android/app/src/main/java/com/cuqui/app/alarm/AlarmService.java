package com.cuqui.app.alarm;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import java.util.Collections;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class AlarmService extends Service {

    public static final String ACTION_STOP = "com.cuqui.app.alarm.STOP";
    private static final String CHANNEL_ID = "cuqui-alarm";
    private static final String TAG = "AlarmService";
    private static final int NOTIFICATION_ID = 9999;

    private static final Set<String> activeAlarms = Collections.newSetFromMap(new ConcurrentHashMap<>());

    private MediaPlayer mediaPlayer;
    private Vibrator vibrator;
    private PowerManager.WakeLock wakeLock;
    private android.os.Handler vibrationHandler;
    private final Runnable vibrationRunnable = new Runnable() {
        @Override
        public void run() {
            if (vibrator != null && vibrator.hasVibrator()) {
                long[] pattern = {0, 800, 400};
                int[] amplitudes = {0, 255, 0};
                VibrationEffect effect = VibrationEffect.createWaveform(pattern, amplitudes, -1);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    android.os.VibrationAttributes attrs = new android.os.VibrationAttributes.Builder()
                            .setUsage(android.os.VibrationAttributes.USAGE_ALARM)
                            .build();
                    vibrator.vibrate(effect, attrs);
                } else {
                    vibrator.vibrate(effect);
                }
                vibrationHandler.postDelayed(this, 1200);
            }
        }
    };

    @SuppressWarnings("deprecation")
    private Vibrator getVibrator() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            VibratorManager vm = (VibratorManager) getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
            return vm.getDefaultVibrator();
        }
        return (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
    }

    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "onCreate");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        String action = intent != null ? intent.getAction() : null;
        String timerId = intent != null ? intent.getStringExtra("timerId") : null;
        String timerName = intent != null ? intent.getStringExtra("timerName") : "Cuqui";
        Log.d(TAG, "onStartCommand action=" + action + " id=" + timerId + " name=" + timerName);

        if (ACTION_STOP.equals(action)) {
            Log.d(TAG, "STOP received");
            if (timerId != null) activeAlarms.remove(timerId);
            stopEverything();
            return START_NOT_STICKY;
        }

        if (timerId != null && !activeAlarms.add(timerId)) {
            Log.d(TAG, "Alarm already active for " + timerId + ", ignoring duplicate");
            return START_STICKY;
        }

        PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
        wakeLock = pm.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                "cuqui:alarm"
        );
        wakeLock.acquire(10 * 60 * 1000L);
        Log.d(TAG, "Wake lock acquired");

        Notification notification = buildNotification(timerId, timerName);
        Log.d(TAG, "Notification built, calling startForeground");
        try {
            if (Build.VERSION.SDK_INT >= 34) {
                startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);
            } else {
                startForeground(NOTIFICATION_ID, notification);
            }
            Log.d(TAG, "startForeground completed successfully");
        } catch (Exception e) {
            Log.e(TAG, "startForeground with type failed, trying without", e);
            try {
                startForeground(NOTIFICATION_ID, notification);
                Log.d(TAG, "startForeground without type completed successfully");
            } catch (Exception e2) {
                Log.e(TAG, "startForeground also failed", e2);
            }
        }
        Log.d(TAG, "startForeground DONE");

        startSound();
        startVibration();
        launchAlarmActivity(timerName);

        new android.os.Handler(getMainLooper()).postDelayed(this::stopEverything, 10 * 60 * 1000L);

        return START_STICKY;
    }

    @Override
    public void onTimeout(int startId) {
        Log.d(TAG, "onTimeout - SHORT_SERVICE time limit reached");
        stopEverything();
    }

    private Notification buildNotification(String timerId, String timerName) {
        Intent stopIntent = new Intent(this, AlarmService.class);
        stopIntent.setAction(ACTION_STOP);
        stopIntent.putExtra("timerId", timerId);
        PendingIntent stopPI = PendingIntent.getService(this, 0, stopIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Intent openIntent = new Intent(this, AlarmActivity.class);
        openIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        openIntent.putExtra("timerId", timerId);
        openIntent.putExtra("timerName", timerName);
        PendingIntent openPI = PendingIntent.getActivity(this, 100, openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        Log.d(TAG, "Building notification with fullScreenIntent for timer " + timerId);
        
        Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle("Cuqui - " + timerName)
                .setContentText("Timer completado. Toca para cancelar.")
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setOngoing(true)
                .setContentIntent(openPI)
                .setFullScreenIntent(openPI, true)
                .addAction(0, "OK", stopPI)
                .build();
        
        Log.d(TAG, "Notification built successfully");
        return notification;
    }

    private void launchAlarmActivity(String timerName) {
        try {
            Intent intent = new Intent(this, AlarmActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                    | Intent.FLAG_ACTIVITY_CLEAR_TOP
                    | Intent.FLAG_ACTIVITY_EXCLUDE_FROM_RECENTS
                    | Intent.FLAG_ACTIVITY_REORDER_TO_FRONT);
            intent.putExtra("timerName", timerName);
            startActivity(intent);
            Log.d(TAG, "AlarmActivity launched");
        } catch (Exception e) {
            Log.e(TAG, "AlarmActivity launch FAILED", e);
        }
    }

    private void startSound() {
        try {
            Uri uri = Uri.parse("android.resource://" + getPackageName() + "/raw/alarm_beep");
            mediaPlayer = MediaPlayer.create(this, uri);
            if (mediaPlayer != null) {
                mediaPlayer.setLooping(true);
                mediaPlayer.setVolume(1.0f, 1.0f);
                mediaPlayer.start();
                Log.d(TAG, "Sound started");
            }
        } catch (Exception e) {
            Log.e(TAG, "Sound failed", e);
        }
    }

    @SuppressWarnings("deprecation")
    private void startVibration() {
        try {
            vibrator = getVibrator();
            if (vibrator != null && vibrator.hasVibrator()) {
                vibrationHandler = new android.os.Handler(getMainLooper());
                vibrationHandler.post(vibrationRunnable);
                Log.d(TAG, "Vibration started with manual loop");
            }
        } catch (Exception e) {
            Log.e(TAG, "Vibration failed", e);
        }
    }

    private void stopEverything() {
        Log.d(TAG, "stopEverything");
        try {
            if (vibrationHandler != null) { vibrationHandler.removeCallbacks(vibrationRunnable); vibrationHandler = null; }
        } catch (Exception ignored) {}
        try {
            if (vibrator != null) { vibrator.cancel(); vibrator = null; }
        } catch (Exception ignored) {}
        try {
            if (mediaPlayer != null) {
                if (mediaPlayer.isPlaying()) mediaPlayer.stop();
                mediaPlayer.release();
                mediaPlayer = null;
            }
        } catch (Exception ignored) {}
        try {
            if (wakeLock != null && wakeLock.isHeld()) { wakeLock.release(); wakeLock = null; }
        } catch (Exception ignored) {}
        try { stopForeground(true); } catch (Exception ignored) {}
        try { stopSelf(); } catch (Exception ignored) {}
    }

    @Override
    public void onDestroy() {
        Log.d(TAG, "onDestroy");
        stopEverything();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) { return null; }
}
