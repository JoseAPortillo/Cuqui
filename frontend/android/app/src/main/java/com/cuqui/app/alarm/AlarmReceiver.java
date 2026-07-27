package com.cuqui.app.alarm;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

public class AlarmReceiver extends BroadcastReceiver {

    private static final String TAG = "AlarmReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        String timerId = intent.getStringExtra("timerId");
        String timerName = intent.getStringExtra("timerName");
        Log.d(TAG, ">>> onReceive timerId=" + timerId + " name=" + timerName);

        try {
            Intent serviceIntent = new Intent(context, AlarmService.class);
            serviceIntent.putExtra("timerId", timerId);
            serviceIntent.putExtra("timerName", timerName);

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
            Log.d(TAG, "Service started OK");
        } catch (Exception e) {
            Log.e(TAG, "Service start FAILED", e);
        }
    }
}
