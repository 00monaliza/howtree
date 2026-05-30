import createNextIntlPlugin from 'next-intl/plugin';

// Явно указываем плагину, где лежит наш конфигурационный файл
const withNextIntl = createNextIntlPlugin('./lib/i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {},
  serverExternalPackages: ["@react-pdf/renderer"],
  /* ваши остальные настройки, если будут */
};

export default withNextIntl(nextConfig);