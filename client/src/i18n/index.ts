import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import HttpBackend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

i18n
  .use(HttpBackend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'zh-CN',
    debug: false,
    interpolation: {
      escapeValue: false,
    },
    backend: {
      loadPath: '/locales/{{lng}}/translation.json',
    },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
  });

export default i18n;

export const supportedLanguages = [
  { code: 'zh-CN', name: '简体中文', flag: '' },
  { code: 'zh-TW', name: '繁體中文', flag: '' },
  { code: 'en', name: 'English', flag: '' },
];

export type LanguageCode = 'zh-CN' | 'zh-TW' | 'en';
