package com.cuqui.app.alarm;

import android.app.KeyguardManager;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import com.cuqui.app.R;

public class AlarmActivity extends AppCompatActivity {

    private static final String TAG = "AlarmActivity";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Log.d(TAG, ">>> onCreate");

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
            KeyguardManager km = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
            if (km != null && km.isKeyguardLocked()) {
                km.requestDismissKeyguard(this, null);
            }
        }

        getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                        | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
                        | WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                        | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
        );

        setContentView(R.layout.activity_alarm);

        String timerName = getIntent().getStringExtra("timerName");
        if (timerName == null || timerName.isEmpty()) {
            timerName = "Cuqui";
        }

        TextView titleText = findViewById(R.id.alarmTitle);
        TextView subtitleText = findViewById(R.id.alarmSubtitle);
        Button okButton = findViewById(R.id.alarmOkButton);

        titleText.setText(timerName);
        subtitleText.setText("Timer completado");

        okButton.setOnClickListener(v -> {
            Log.d(TAG, "OK pressed, stopping alarm");
            try {
                Intent intent = new Intent(this, AlarmService.class);
                intent.setAction(AlarmService.ACTION_STOP);
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(intent);
                } else {
                    startService(intent);
                }
            } catch (Exception e) {
                Log.e(TAG, "Stop service failed", e);
            }
            finish();
        });
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        Log.d(TAG, ">>> onNewIntent");
    }

    @Override
    public void onBackPressed() {
        // Don't allow back to dismiss
    }
}
