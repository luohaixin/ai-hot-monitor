import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { LanguageCode } from '../i18n';

export function useLanguage() {
  const { i18n, t } = useTranslation();

  const currentLanguage = i18n.language as LanguageCode;

  const changeLanguage = useCallback((lang: LanguageCode) => {
    i18n.changeLanguage(lang);
  }, [i18n]);

  const isCurrentLanguage = useCallback((lang: LanguageCode) => {
    return currentLanguage === lang;
  }, [currentLanguage]);

  return {
    t,
    i18n,
    currentLanguage,
    changeLanguage,
    isCurrentLanguage,
  };
}
