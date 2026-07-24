import { useEffect, useRef } from 'react'
import { LocalNotifications } from '@capacitor/local-notifications'
import { Haptics, ImpactStyle } from '@capacitor/haptics'
import { StatusBar, Style } from '@capacitor/status-bar'
import { SplashScreen } from '@capacitor/splash-screen'
import { isNativePlatform } from '../utils/platform'

export function useCapacitor() {
  const isNative = isNativePlatform()
  const notificationsAuthorized = useRef(false)

  useEffect(() => {
    if (!isNative) return

    async function init() {
      try {
        await StatusBar.setStyle({ style: Style.Dark })
        await StatusBar.setBackgroundColor({ color: '#0f0f23' })
      } catch { /* ignore */ }

      try {
        await SplashScreen.hide()
      } catch { /* ignore */ }

      try {
        const permission = await LocalNotifications.requestPermissions()
        notificationsAuthorized.current = permission.display === 'granted'
      } catch { /* ignore */ }
    }

    init()
  }, [isNative])

  const vibrateOnComplete = async () => {
    if (!isNative) return
    try {
      await Haptics.impact({ style: ImpactStyle.Heavy })
      setTimeout(async () => {
        await Haptics.impact({ style: ImpactStyle.Heavy })
      }, 300)
      setTimeout(async () => {
        await Haptics.impact({ style: ImpactStyle.Heavy })
      }, 600)
    } catch { /* ignore */ }
  }

  const vibrateOnAction = async () => {
    if (!isNative) return
    try {
      await Haptics.impact({ style: ImpactStyle.Light })
    } catch { /* ignore */ }
  }

  const scheduleLocalNotification = async (_timerId: string, timerName: string, seconds: number) => {
    if (!isNative || !notificationsAuthorized.current) return
    try {
      await LocalNotifications.schedule({
        notifications: [{
          title: 'Cuqui',
          body: `${timerName} está listo!`,
          id: Math.floor(Math.random() * 100000),
          schedule: { at: new Date(Date.now() + seconds * 1000) },
          smallIcon: 'ic_stat_icon_config_sample',
          largeIcon: 'ic_launcher',
          channelId: 'cuqui-timers',
        }],
      })
    } catch { /* ignore */ }
  }

  const cancelAllLocalNotifications = async () => {
    if (!isNative) return
    try {
      const pending = await LocalNotifications.getPending()
      if (pending.notifications.length > 0) {
        await LocalNotifications.cancel({ notifications: pending.notifications })
      }
    } catch { /* ignore */ }
  }

  return {
    isNative,
    vibrateOnComplete,
    vibrateOnAction,
    scheduleLocalNotification,
    cancelAllLocalNotifications,
  }
}
