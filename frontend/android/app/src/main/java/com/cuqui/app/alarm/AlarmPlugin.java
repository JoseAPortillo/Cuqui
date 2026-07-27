package com.cuqui.app.alarm;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "Alarm")
public class AlarmPlugin extends Plugin {

    private static final String TAG = "AlarmPlugin";
    private static final String EXTRA_TIMER_ID = "timerId";
    private static final String EXTRA_TIMER_NAME = "timerName";
    private static final String EXTRA_FIRE_TIME = "fireTime";

    private AlarmManager getAlarmManager() {
        return (AlarmManager) getContext().getSystemService(Context.ALARM_SERVICE);
    }

    private PendingIntent getAlarmPendingIntent(String timerId, String timerName, long fireTime, int flags) {
        Intent intent = new Intent(getContext(), AlarmReceiver.class);
        intent.putExtra(EXTRA_TIMER_ID, timerId);
        intent.putExtra(EXTRA_TIMER_NAME, timerName);
        intent.putExtra(EXTRA_FIRE_TIME, fireTime);
        return PendingIntent.getBroadcast(
                getContext(),
                timerId.hashCode(),
                intent,
                flags | PendingIntent.FLAG_UPDATE_CURRENT
        );
    }

    @PluginMethod
    public void schedule(PluginCall call) {
        try {
            String timerId = call.getString("timerId", "");
            String timerName = call.getString("timerName", "Timer");
            int seconds = call.getInt("seconds", 0);

            Log.d(TAG, "schedule() called with timerId=" + timerId + " timerName=" + timerName + " seconds=" + seconds);

            if (timerId.isEmpty()) {
                call.reject("timerId is required");
                return;
            }

            long fireTime = System.currentTimeMillis() + ((long) seconds * 1000);
            Log.d(TAG, "fireTime=" + fireTime + " (now=" + System.currentTimeMillis() + ")");
            int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                    ? PendingIntent.FLAG_IMMUTABLE
                    : 0;

            PendingIntent pendingIntent = getAlarmPendingIntent(timerId, timerName, fireTime, flags);
            AlarmManager alarmManager = getAlarmManager();

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                if (!alarmManager.canScheduleExactAlarms()) {
                    call.reject("SCHEDULE_EXACT_ALARM permission not granted");
                    return;
                }
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP,
                        fireTime,
                        pendingIntent
                );
            } else {
                alarmManager.setExact(
                        AlarmManager.RTC_WAKEUP,
                        fireTime,
                        pendingIntent
                );
            }

            Log.d(TAG, "Scheduled alarm for timer " + timerId + " at " + fireTime);
            JSObject result = new JSObject();
            result.put("success", true);
            result.put("timerId", timerId);
            call.resolve(result);
        } catch (Exception e) {
            Log.e(TAG, "Failed to schedule alarm", e);
            call.reject("Failed to schedule alarm: " + e.getMessage());
        }
    }

    @PluginMethod
    public void cancel(PluginCall call) {
        try {
            String timerId = call.getString("timerId", "");
            if (timerId.isEmpty()) {
                call.reject("timerId is required");
                return;
            }

            int flags = Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                    ? PendingIntent.FLAG_IMMUTABLE
                    : 0;

            PendingIntent pendingIntent = getAlarmPendingIntent(timerId, "", 0, flags);
            AlarmManager alarmManager = getAlarmManager();
            alarmManager.cancel(pendingIntent);
            pendingIntent.cancel();

            Log.d(TAG, "Cancelled alarm for timer " + timerId);

            JSObject result = new JSObject();
            result.put("success", true);
            result.put("timerId", timerId);
            call.resolve(result);
        } catch (Exception e) {
            Log.e(TAG, "Failed to cancel alarm", e);
            call.reject("Failed to cancel alarm: " + e.getMessage());
        }
    }
}
