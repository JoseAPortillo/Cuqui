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

  const vibrateOnAction = async () => {
    if (!isNative) return
    try {
      await Haptics.impact({ style: ImpactStyle.Light })
    } catch { /* ignore */ }
  }

  return {
    isNative,
    vibrateOnAction,
  }
}
