# Architecture & i18n Design — HowTree

**Date:** 2026-05-26  
**Scope:** Restructure app folder layout + add next-intl with locale routing (ru/kk/en)

---

## Goal

1. Move all pages into `app/[locale]/` to support locale-based routing
2. Add `next-intl` with middleware for locale detection
3. Extract all hardcoded strings into `messages/{locale}.json`
4. Add `LanguageSwitcher` component in TopNav
5. Keep existing component and store structure unchanged

---

## Architecture

### Folder Structure (after)

```
howTree/
├── app/
│   ├── [locale]/
│   │   ├── layout.tsx          ← NextIntlClientProvider + TopNav
│   │   ├── page.tsx            ← redirect → /[locale]/dashboard
│   │   ├── dashboard/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── analytics/
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   └── reports/
│   │       ├── layout.tsx
│   │       └── page.tsx
│   ├── favicon.ico
│   ├── globals.css
│   └── layout.tsx              ← root html/body layout (no changes)
│
├── messages/
│   ├── en.json
│   ├── ru.json
│   └── kk.json
│
├── middleware.ts                ← locale detection + redirect
│
├── components/
│   ├── layout/
│   │   ├── TopNav.tsx          ← add LanguageSwitcher
│   │   └── LanguageSwitcher.tsx  ← NEW
│   ├── map/
│   ├── panels/
│   ├── charts/
│   ├── assistant/
│   ├── reports/
│   └── ui/
│
├── lib/
│   ├── i18n/
│   │   ├── routing.ts          ← defineRouting (locales, defaultLocale: "ru")
│   │   └── navigation.ts       ← typed Link, useRouter, usePathname, redirect
│   ├── api/client.ts
│   ├── store/mapStore.ts
│   ├── providers.tsx
│   └── utils.ts
│
└── types/index.ts
```

---

## Components

### middleware.ts
- Uses `createLocalizedPathnameMiddleware` from next-intl
- Supported locales: `["ru", "kk", "en"]`, default: `"ru"`
- Detects locale from: URL path → cookie (`NEXT_LOCALE`) → `Accept-Language` header
- Redirects `/dashboard` → `/ru/dashboard` (or user's preferred locale)

### lib/i18n/routing.ts
```ts
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["ru", "kk", "en"],
  defaultLocale: "ru",
});
```

### lib/i18n/navigation.ts
```ts
import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter } =
  createNavigation(routing);
```

### app/[locale]/layout.tsx
- Receives `{ locale }` param
- Calls `getMessages()` from next-intl
- Wraps children with `NextIntlClientProvider`
- Renders `<TopNav />` above children

### messages/ JSON structure
```json
{
  "nav": {
    "dashboard": "...",
    "analytics": "...",
    "reports": "...",
    "connected": "..."
  },
  "analysis": {
    "title": "...",
    "tabMap": "...",
    "tabUpload": "...",
    "hint": "..."
  },
  "workspace": {
    "title": "Geo workspace",
    "description": "...",
    "aoi": "AOI",
    "mode": "Mode"
  },
  "confidence": {
    "title": "Confidence",
    "high": "≥ 90% — High",
    "medHigh": "≥ 70% — Medium-high",
    "med": "≥ 50% — Medium",
    "low": "< 50% — Low"
  },
  "layers": {
    "title": "Layers",
    "points": "Points",
    "heatmap": "Heatmap",
    "districts": "Districts"
  },
  "common": {
    "loading": "...",
    "error": "..."
  }
}
```

### components/layout/LanguageSwitcher.tsx
- Dropdown (Radix Select) showing current locale flag + code: `🇷🇺 RU`
- Options: RU, KK, EN
- On change: calls `useRouter().replace(pathname, { locale })` from `lib/i18n/navigation.ts`
- Placed in TopNav right side, before "API Connected" indicator

---

## Data Flow

```
User visits /dashboard
    ↓
middleware.ts
    → detects locale (cookie → Accept-Language → default "ru")
    → redirects to /ru/dashboard
    ↓
app/[locale]/layout.tsx
    → getMessages({ locale: "ru" }) loads messages/ru.json
    → NextIntlClientProvider provides messages to tree
    ↓
components use useTranslations("nav") etc.
    ↓
User clicks LanguageSwitcher → selects "kk"
    → router.replace(pathname, { locale: "kk" })
    → URL changes to /kk/dashboard
    → middleware sets NEXT_LOCALE cookie
    → page re-renders with kk messages
```

---

## Migration Plan

### Files to move
- `app/dashboard/` → `app/[locale]/dashboard/`
- `app/analytics/` → `app/[locale]/analytics/`
- `app/reports/` → `app/[locale]/reports/`
- `app/page.tsx` → `app/[locale]/page.tsx`

### Files to create
- `middleware.ts`
- `lib/i18n/routing.ts`
- `lib/i18n/navigation.ts`
- `app/[locale]/layout.tsx`
- `messages/en.json`
- `messages/ru.json`
- `messages/kk.json`
- `components/layout/LanguageSwitcher.tsx`

### Files to update
- `app/layout.tsx` — remove `<TopNav>` if present, keep html/body only
- `components/layout/TopNav.tsx` — add LanguageSwitcher, use `useTranslations`
- `components/panels/AnalysisPanel.tsx` — replace hardcoded strings
- `app/[locale]/dashboard/page.tsx` — replace hardcoded strings
- `package.json` — add `next-intl`

### Strings to extract (current hardcoded)
- TopNav: "Dashboard", "Analytics", "Reports", "API Connected"
- AnalysisPanel: "Карта", "Снимок", "Analysis Control"
- Dashboard: workspace card text, confidence legend, "Зажми и протяни..."
- All other UI text in components

---

## Error Handling

- If locale param is invalid, middleware redirects to default locale
- If message key missing, next-intl shows key name as fallback (visible in dev)
- Language switch uses client-side navigation, no full page reload

---

## Out of Scope

- Server-side SEO optimization per locale
- Pluralization rules (not needed yet)
- Date/number formatting per locale
- RTL support
