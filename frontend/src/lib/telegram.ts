import type { TelegramWebApp } from '@/types/telegram';

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

export function initializeTelegram(): TelegramWebApp | null {
  const webApp = getTelegramWebApp();
  if (!webApp) return null;

  webApp.ready();
  webApp.expand();
  webApp.setHeaderColor?.('#07090d');
  webApp.setBackgroundColor?.('#07090d');
  return webApp;
}

export function setTelegramBackButton(visible: boolean, onBack: () => void): () => void {
  const button = getTelegramWebApp()?.BackButton;
  if (!button) return () => {};
  if (visible) { button.show(); button.onClick(onBack); } else button.hide();
  return () => { button.offClick(onBack); button.hide(); };
}

export function hapticSuccess(): void {
  getTelegramWebApp()?.HapticFeedback?.notificationOccurred('success');
}

export function hapticTap(): void {
  getTelegramWebApp()?.HapticFeedback?.impactOccurred('light');
}

export function getTelegramStartParam(webApp: TelegramWebApp): string | undefined {
  const signedStartParam = webApp.initDataUnsafe?.start_param;
  if (signedStartParam) return signedStartParam;

  return new URLSearchParams(window.location.search).get('tgWebAppStartParam') ?? undefined;
}

export function openExternalUrl(url: string): void {
  const webApp = getTelegramWebApp();
  if (webApp?.openLink) {
    webApp.openLink(url);
    return;
  }
  window.open(url, '_blank', 'noopener,noreferrer');
}

export function shareOnTelegram(url: string): void {
  const shareUrl = new URL('https://t.me/share/url');
  shareUrl.searchParams.set('url', url);
  shareUrl.searchParams.set('text', 'Join me at SMC Academy using my referral link.');

  const webApp = getTelegramWebApp();
  if (webApp) {
    webApp.HapticFeedback?.impactOccurred('light');
    webApp.openTelegramLink(shareUrl.toString());
    return;
  }
  window.open(shareUrl.toString(), '_blank', 'noopener,noreferrer');
}
