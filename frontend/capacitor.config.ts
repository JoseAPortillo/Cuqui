import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.cuqui.app',
  appName: 'Cuqui',
  webDir: 'dist',
  server: {
    androidScheme: 'https',
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
      launchShowDuration: 2000,
      backgroundColor: '#0f0f23',
      showSpinner: true,
      spinnerColor: '#4fc3f7',
    },
    LocalNotifications: {
      smallIcon: 'ic_stat_icon_config_sample',
      iconColor: '#4fc3f7',
    },
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#0f0f23',
    },
  },
};

export default config;
