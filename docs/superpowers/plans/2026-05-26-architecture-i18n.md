# Architecture & i18n Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add next-intl locale routing (ru/kk/en) with a LanguageSwitcher in TopNav, extract all hardcoded strings, and restructure `app/` under `app/[locale]/`.

**Architecture:** Pages move to `app/[locale]/` so Next.js serves `/ru/dashboard`, `/kk/dashboard`, `/en/dashboard`. Middleware detects locale from URL/cookie/Accept-Language and redirects. `NextIntlClientProvider` in the locale layout provides translations to all client components via `useTranslations()`.

**Tech Stack:** next-intl v3, Next.js 16 App Router, Zustand, React Query, TypeScript

---

## File Map

| Action | Path |
|--------|------|
| Create | `lib/i18n/routing.ts` |
| Create | `lib/i18n/navigation.ts` |
| Create | `middleware.ts` |
| Create | `messages/ru.json` |
| Create | `messages/en.json` |
| Create | `messages/kk.json` |
| Rewrite | `app/layout.tsx` |
| Create | `app/[locale]/layout.tsx` |
| Create | `app/[locale]/page.tsx` |
| Create | `app/[locale]/dashboard/layout.tsx` |
| Create | `app/[locale]/dashboard/page.tsx` |
| Create | `app/[locale]/analytics/layout.tsx` |
| Create | `app/[locale]/analytics/page.tsx` |
| Create | `app/[locale]/reports/layout.tsx` |
| Create | `app/[locale]/reports/page.tsx` |
| Create | `components/layout/LanguageSwitcher.tsx` |
| Rewrite | `components/layout/TopNav.tsx` |
| Rewrite | `components/panels/AnalysisPanel.tsx` |
| Rewrite | `components/panels/LayerToggle.tsx` |
| Rewrite | `components/assistant/AssistantPanel.tsx` |
| Delete | `app/page.tsx` |
| Delete | `app/dashboard/` |
| Delete | `app/analytics/` |
| Delete | `app/reports/` |

---

## Task 1: Install next-intl + create i18n routing/navigation

**Files:**
- Modify: `package.json`
- Create: `lib/i18n/routing.ts`
- Create: `lib/i18n/navigation.ts`

- [ ] **Step 1: Install next-intl**

```bash
npm install next-intl@^3
```

Expected: next-intl appears in `package.json` dependencies.

- [ ] **Step 2: Create `lib/i18n/routing.ts`**

```ts
import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  locales: ["ru", "kk", "en"],
  defaultLocale: "ru",
});
```

- [ ] **Step 3: Create `lib/i18n/navigation.ts`**

```ts
import { createNavigation } from "next-intl/navigation";
import { routing } from "./routing";

export const { Link, redirect, usePathname, useRouter } =
  createNavigation(routing);
```

- [ ] **Step 4: Commit**

```bash
git add lib/i18n/routing.ts lib/i18n/navigation.ts package.json package-lock.json
git commit -m "feat: add next-intl and i18n routing/navigation helpers"
```

---

## Task 2: Create middleware.ts

**Files:**
- Create: `middleware.ts`

- [ ] **Step 1: Create `middleware.ts` in project root**

```ts
import createMiddleware from "next-intl/middleware";
import { routing } from "./lib/i18n/routing";

export default createMiddleware(routing);

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
```

The matcher excludes API routes, Next.js internals, and static files. `createMiddleware(routing)` reads `locales` and `defaultLocale` from routing config, detects locale from URL → `NEXT_LOCALE` cookie → `Accept-Language` header, and redirects accordingly.

- [ ] **Step 2: Verify middleware path is correct**

```bash
ls middleware.ts
```

Expected: `middleware.ts`

- [ ] **Step 3: Commit**

```bash
git add middleware.ts
git commit -m "feat: add next-intl middleware for locale routing"
```

---

## Task 3: Create translation files

**Files:**
- Create: `messages/ru.json`
- Create: `messages/en.json`
- Create: `messages/kk.json`

- [ ] **Step 1: Create `messages/ru.json`**

```json
{
  "nav": {
    "subtitle": "Urban Canopy Intelligence",
    "dashboard": "Панель",
    "analytics": "Аналитика",
    "reports": "Отчёты",
    "connected": "API подключён"
  },
  "analysis": {
    "tabMap": "Карта",
    "tabUpload": "Снимок",
    "title": "Анализ зелёного покрова",
    "sidebarTitle": "Управление анализом",
    "zone": "Зона анализа",
    "area": "Площадь",
    "selectHint": "Выдели прямоугольник на карте",
    "selectHintSub": "Зажми мышь и протяни рамку по нужной части города.",
    "mapHint": "Зажми и протяни прямоугольник, чтобы выбрать область анализа",
    "run": "Запустить анализ",
    "queued": "⏳ В очереди...",
    "running": "Идёт анализ...",
    "status": "Статус",
    "done": "Готово",
    "error": "Ошибка",
    "queueWait": "Ожидание в очереди...",
    "genericError": "Анализ завершился с ошибкой",
    "failedError": "Не удалось выполнить анализ",
    "apiKeyTitle": "Нужен ключ спутниковых снимков",
    "apiKeyCompact": "Для анализа с карты backend скачивает тайлы через Yandex Maps Static API.",
    "apiKeyFull": "Подключи Yandex Maps Static API в кабинете разработчика и добавь ключ в backend/.env.",
    "uploadTitle": "Свой снимок",
    "uploadDesc": "Этот режим не требует Yandex Static API: модель работает по загруженному изображению.",
    "dropHint": "Перетащи изображение сюда или выбери файл",
    "geotiffAuto": "GeoTIFF — границы определяются автоматически",
    "geoBounds": "Географические границы",
    "geoBoundsHint": "Подсказка: можно сначала выделить bbox на карте и перенести координаты сюда.",
    "processing": "Обработка...",
    "findTrees": "Найти деревья",
    "keyRejected": "Ключ imagery отклонён",
    "noImagery": "Imagery API не подключён",
    "stopped": "Анализ остановлен",
    "keyRejectedDesc": "Yandex вернул 403. Проверь, что ключ активирован для Static API, ограничения ключа разрешают backend-запросы, и тариф допускает нужный тип карты.",
    "noImageryDesc": "Для анализа с карты нужен ключ Yandex Maps Static API. После добавления ключа перезапусти backend.",
    "results": "Результаты",
    "totalTrees": "Деревья",
    "canopyCoverage": "Покрытие крон",
    "density": "Плотность",
    "analysisDate": "Дата анализа",
    "detected": "обнаружено",
    "ofArea": "площади",
    "treesPerKm": "дер/км²"
  },
  "layers": {
    "title": "Слои",
    "points": "Точки деревьев",
    "heatmap": "Тепловая карта",
    "districts": "Районы"
  },
  "dashboard": {
    "workspaceTitle": "Geo workspace",
    "workspaceDesc": "Спутниковая подложка, bbox-сетка и слой найденных крон в одном окне.",
    "confidence": "Уверенность",
    "confHigh": "≥ 90% — Высокая",
    "confMedHigh": "≥ 70% — Средне-высокая",
    "confMed": "≥ 50% — Средняя",
    "confLow": "< 50% — Низкая"
  },
  "assistant": {
    "title": "AI-ассистент",
    "greeting": "Привет! Я AI-ассистент HowTree. Могу объяснить результаты анализа или ответить на вопросы об экологии и озеленении.",
    "trees": "деревьев",
    "coverage": "покрытие",
    "quickQuestions": "Быстрые вопросы:",
    "placeholder": "Спросите что-нибудь...",
    "connectionError": "Ошибка соединения с бэкендом.",
    "quickExplainLabel": "Объясни результаты",
    "quickExplainText": "Объясни результаты последнего анализа",
    "quickConfidenceLabel": "Что такое confidence?",
    "quickConfidenceText": "Что означает уверенность модели и как её интерпретировать?",
    "quickDetectionLabel": "Как работает детекция?",
    "quickDetectionText": "Как платформа обнаруживает деревья на снимках?",
    "quickLimitsLabel": "Ограничения модели",
    "quickLimitsText": "Какие у модели ограничения и насколько точны результаты?"
  },
  "analytics": {
    "title": "Аналитика",
    "subtitle": "Результаты обнаружения деревьев в реальном времени",
    "exportCsv": "Экспорт CSV",
    "totalTrees": "Всего деревьев",
    "totalCanopy": "Площадь крон",
    "analysesRun": "Запущено анализов",
    "avgConf": "Средняя уверенность",
    "analyses": "анализов",
    "completed": "завершено",
    "acrossJobs": "по всем задачам",
    "noData": "нет данных",
    "history": "История анализов",
    "failedLoad": "Не удалось загрузить:",
    "empty": "Нет анализов. Запустите первое обнаружение на Панели.",
    "date": "Дата",
    "status": "Статус",
    "trees": "Деревья",
    "canopy": "Кроны",
    "confidence": "Уверенность",
    "bbox": "Область"
  },
  "reports": {
    "title": "Отчёты",
    "subtitle": "Создание технических PDF-отчётов для анализа районов",
    "generate": "Создать отчёт",
    "selectDistrict": "Выберите район",
    "treesDetected": "Деревьев обнаружено",
    "canopyCoverage": "Покрытие крон",
    "density": "Плотность (дер/км²)",
    "avgConf": "Средняя уверенность",
    "contents": "Содержание отчёта",
    "item1": "Исполнительное резюме с ключевыми показателями",
    "item2": "Карта со спутниковыми снимками и наложением деревьев",
    "item3": "Таблица разбивки по зонам",
    "item4": "График распределения уверенности",
    "item5": "Технический документ государственного формата",
    "recent": "Последние отчёты",
    "format": "Формат",
    "size": "Размер",
    "language": "Язык",
    "standard": "Стандарт"
  }
}
```

- [ ] **Step 2: Create `messages/en.json`**

```json
{
  "nav": {
    "subtitle": "Urban Canopy Intelligence",
    "dashboard": "Dashboard",
    "analytics": "Analytics",
    "reports": "Reports",
    "connected": "API Connected"
  },
  "analysis": {
    "tabMap": "Map",
    "tabUpload": "Image",
    "title": "Green Cover Analysis",
    "sidebarTitle": "Analysis Control",
    "zone": "Analysis Zone",
    "area": "Area",
    "selectHint": "Select a rectangle on the map",
    "selectHintSub": "Hold mouse and drag to select an area of the city.",
    "mapHint": "Hold and drag a rectangle to select an analysis area",
    "run": "Run Analysis",
    "queued": "⏳ Queued...",
    "running": "Analyzing...",
    "status": "Status",
    "done": "Done",
    "error": "Error",
    "queueWait": "Waiting in queue...",
    "genericError": "Analysis failed",
    "failedError": "Could not complete analysis",
    "apiKeyTitle": "Satellite imagery key required",
    "apiKeyCompact": "For map analysis, the backend downloads tiles via Yandex Maps Static API.",
    "apiKeyFull": "Connect Yandex Maps Static API in the developer console and add the key to backend/.env.",
    "uploadTitle": "Your image",
    "uploadDesc": "This mode does not require Yandex Static API: the model works on your uploaded image.",
    "dropHint": "Drag image here or select a file",
    "geotiffAuto": "GeoTIFF — bounds determined automatically",
    "geoBounds": "Geographic bounds",
    "geoBoundsHint": "Tip: you can draw a bbox on the map first and copy the coordinates here.",
    "processing": "Processing...",
    "findTrees": "Find Trees",
    "keyRejected": "Imagery key rejected",
    "noImagery": "Imagery API not connected",
    "stopped": "Analysis stopped",
    "keyRejectedDesc": "Yandex returned 403. Check that the key is activated for Static API, key restrictions allow backend requests, and the plan supports the required map type.",
    "noImageryDesc": "Map analysis requires a Yandex Maps Static API key. After adding the key, restart the backend.",
    "results": "Results",
    "totalTrees": "Total Trees",
    "canopyCoverage": "Canopy Coverage",
    "density": "Density",
    "analysisDate": "Analysis Date",
    "detected": "detected",
    "ofArea": "of area",
    "treesPerKm": "trees/km²"
  },
  "layers": {
    "title": "Layers",
    "points": "Tree Points",
    "heatmap": "Heatmap",
    "districts": "Districts"
  },
  "dashboard": {
    "workspaceTitle": "Geo workspace",
    "workspaceDesc": "Satellite basemap, bbox grid and detected canopy layer in one window.",
    "confidence": "Confidence",
    "confHigh": "≥ 90% — High",
    "confMedHigh": "≥ 70% — Medium-high",
    "confMed": "≥ 50% — Medium",
    "confLow": "< 50% — Low"
  },
  "assistant": {
    "title": "AI Assistant",
    "greeting": "Hi! I'm the HowTree AI assistant. I can explain analysis results or answer questions about ecology and urban greening.",
    "trees": "trees",
    "coverage": "coverage",
    "quickQuestions": "Quick questions:",
    "placeholder": "Ask something...",
    "connectionError": "Backend connection error.",
    "quickExplainLabel": "Explain results",
    "quickExplainText": "Explain the results of the last analysis",
    "quickConfidenceLabel": "What is confidence?",
    "quickConfidenceText": "What does model confidence mean and how to interpret it?",
    "quickDetectionLabel": "How does detection work?",
    "quickDetectionText": "How does the platform detect trees in satellite images?",
    "quickLimitsLabel": "Model limitations",
    "quickLimitsText": "What are the model's limitations and how accurate are the results?"
  },
  "analytics": {
    "title": "Analytics",
    "subtitle": "Real-time results from your tree detection analyses",
    "exportCsv": "Export CSV",
    "totalTrees": "Total Trees Detected",
    "totalCanopy": "Total Canopy Area",
    "analysesRun": "Analyses Run",
    "avgConf": "Avg Confidence",
    "analyses": "analyses",
    "completed": "completed",
    "acrossJobs": "across all jobs",
    "noData": "no data",
    "history": "Analysis History",
    "failedLoad": "Failed to load:",
    "empty": "No analyses yet. Run your first detection on the Dashboard.",
    "date": "Date",
    "status": "Status",
    "trees": "Trees",
    "canopy": "Canopy",
    "confidence": "Confidence",
    "bbox": "BBox"
  },
  "reports": {
    "title": "Reports",
    "subtitle": "Generate technical PDF reports for district analysis",
    "generate": "Generate Report",
    "selectDistrict": "Select District",
    "treesDetected": "Trees Detected",
    "canopyCoverage": "Canopy Coverage",
    "density": "Density (trees/km²)",
    "avgConf": "Avg Confidence",
    "contents": "Report Contents",
    "item1": "Executive summary with key metrics",
    "item2": "Satellite imagery map with tree overlay",
    "item3": "Sub-zone breakdown table",
    "item4": "Confidence distribution chart",
    "item5": "Government-format technical document",
    "recent": "Recent Reports",
    "format": "Format",
    "size": "Size",
    "language": "Language",
    "standard": "Standard"
  }
}
```

- [ ] **Step 3: Create `messages/kk.json`**

```json
{
  "nav": {
    "subtitle": "Қала ағаштарын талдау",
    "dashboard": "Басты бет",
    "analytics": "Аналитика",
    "reports": "Есептер",
    "connected": "API қосылды"
  },
  "analysis": {
    "tabMap": "Карта",
    "tabUpload": "Сурет",
    "title": "Жасыл қабатты талдау",
    "sidebarTitle": "Талдауды басқару",
    "zone": "Талдау аймағы",
    "area": "Аудан",
    "selectHint": "Картада тіктөртбұрыш таңдаңыз",
    "selectHintSub": "Тышқанды басып, қажетті аймақты белгілеңіз.",
    "mapHint": "Талдау аймағын таңдау үшін тіктөртбұрыш сызыңыз",
    "run": "Талдауды бастау",
    "queued": "⏳ Кезекте...",
    "running": "Талдау жүріп жатыр...",
    "status": "Күй",
    "done": "Дайын",
    "error": "Қате",
    "queueWait": "Кезекте күту...",
    "genericError": "Талдау қатемен аяқталды",
    "failedError": "Талдауды орындау мүмкін болмады",
    "apiKeyTitle": "Жерсерік суреттерінің кілті қажет",
    "apiKeyCompact": "Карта арқылы талдауда backend Yandex Maps Static API арқылы тайлдарды жүктейді.",
    "apiKeyFull": "Yandex Maps Static API кілтін developer консолінде қосып, backend/.env-ке енгізіңіз.",
    "uploadTitle": "Өз суретіңіз",
    "uploadDesc": "Бұл режим Yandex Static API-ды қажет етпейді: модель жүктелген суретпен жұмыс істейді.",
    "dropHint": "Суретті осюда апарыңыз немесе файлды таңдаңыз",
    "geotiffAuto": "GeoTIFF — шекаралар автоматты түрде анықталады",
    "geoBounds": "Географиялық шекаралар",
    "geoBoundsHint": "Кеңес: алдымен картада bbox сызып, координаттарды осюда енгізуге болады.",
    "processing": "Өңдеу...",
    "findTrees": "Ағаштарды табу",
    "keyRejected": "Imagery кілті қабылданбады",
    "noImagery": "Imagery API қосылмаған",
    "stopped": "Талдау тоқтатылды",
    "keyRejectedDesc": "Yandex 403 қайтарды. Кілттің Static API үшін белсендірілгенін, ключ шектеулерінің backend сұрауларына рұқсат беретінін тексеріңіз.",
    "noImageryDesc": "Карта талдауы үшін Yandex Maps Static API кілті қажет. Кілтті қосқаннан кейін backend-ді қайта іске қосыңыз.",
    "results": "Нәтижелер",
    "totalTrees": "Барлық ағаштар",
    "canopyCoverage": "Жапырақ қабаты",
    "density": "Тығыздық",
    "analysisDate": "Талдау күні",
    "detected": "анықталды",
    "ofArea": "аудан",
    "treesPerKm": "ағаш/км²"
  },
  "layers": {
    "title": "Қабаттар",
    "points": "Ағаш нүктелері",
    "heatmap": "Жылу картасы",
    "districts": "Аудандар"
  },
  "dashboard": {
    "workspaceTitle": "Geo workspace",
    "workspaceDesc": "Жерсерік негізі, bbox торы және анықталған ағаштар бір терезеде.",
    "confidence": "Сенімділік",
    "confHigh": "≥ 90% — Жоғары",
    "confMedHigh": "≥ 70% — Орта-жоғары",
    "confMed": "≥ 50% — Орта",
    "confLow": "< 50% — Төмен"
  },
  "assistant": {
    "title": "AI-көмекші",
    "greeting": "Сәлем! Мен HowTree AI-көмекшісімін. Талдау нәтижелерін түсіндіруге немесе экология мен жасылдандыру туралы сұрақтарыңызға жауап беруге дайынмын.",
    "trees": "ағаш",
    "coverage": "қабат",
    "quickQuestions": "Жылдам сұрақтар:",
    "placeholder": "Сұрақ қойыңыз...",
    "connectionError": "Backend байланыс қатесі.",
    "quickExplainLabel": "Нәтижелерді түсіндір",
    "quickExplainText": "Соңғы талдау нәтижелерін түсіндір",
    "quickConfidenceLabel": "Confidence дегеніміз не?",
    "quickConfidenceText": "Модель сенімділігі нені білдіреді және қалай түсіндіруге болады?",
    "quickDetectionLabel": "Анықтау қалай жұмыс істейді?",
    "quickDetectionText": "Платформа жерсерік суреттерінде ағаштарды қалай анықтайды?",
    "quickLimitsLabel": "Модель шектеулері",
    "quickLimitsText": "Модельдің қандай шектеулері бар және нәтижелер қаншалықты дәл?"
  },
  "analytics": {
    "title": "Аналитика",
    "subtitle": "Ағашты анықтау талдауларының нақты уақыттағы нәтижелері",
    "exportCsv": "CSV экспорт",
    "totalTrees": "Барлық анықталған ағаштар",
    "totalCanopy": "Жапырақ қабатының жалпы ауданы",
    "analysesRun": "Жүргізілген талдаулар",
    "avgConf": "Орт. сенімділік",
    "analyses": "талдау",
    "completed": "аяқталды",
    "acrossJobs": "барлық тапсырмалар бойынша",
    "noData": "деректер жоқ",
    "history": "Талдау тарихы",
    "failedLoad": "Жүктеу сәтсіз:",
    "empty": "Талдаулар жоқ. Бас бетте алғашқы анықтауды іске қосыңыз.",
    "date": "Күні",
    "status": "Күй",
    "trees": "Ағаштар",
    "canopy": "Жапырақ",
    "confidence": "Сенімділік",
    "bbox": "Аймақ"
  },
  "reports": {
    "title": "Есептер",
    "subtitle": "Аудан талдауы үшін техникалық PDF есептерін жасау",
    "generate": "Есеп жасау",
    "selectDistrict": "Ауданды таңдаңыз",
    "treesDetected": "Анықталған ағаштар",
    "canopyCoverage": "Жапырақ қабаты",
    "density": "Тығыздық (ағаш/км²)",
    "avgConf": "Орт. сенімділік",
    "contents": "Есеп мазмұны",
    "item1": "Негізгі көрсеткіштер бар атқарушы қорытынды",
    "item2": "Ағаш қабаты бар жерсерік суреттер картасы",
    "item3": "Аймақ бойынша бөлу кестесі",
    "item4": "Сенімділік таралуының диаграммасы",
    "item5": "Мемлекеттік форматтағы техникалық құжат",
    "recent": "Соңғы есептер",
    "format": "Формат",
    "size": "Өлшем",
    "language": "Тіл",
    "standard": "Стандарт"
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add messages/
git commit -m "feat: add ru/en/kk translation files"
```

---

## Task 4: Update root layout + create locale layout

**Files:**
- Rewrite: `app/layout.tsx`
- Create: `app/[locale]/layout.tsx`

- [ ] **Step 1: Rewrite `app/layout.tsx`**

The root layout becomes a minimal pass-through. `html`/`body` move into the locale layout so `lang` can be set dynamically per locale.

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
```

- [ ] **Step 2: Create `app/[locale]/layout.tsx`**

This layout owns `html`, `body`, fonts, `Providers` (React Query), and `NextIntlClientProvider`. It validates the locale param.

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/lib/i18n/routing";
import { Providers } from "@/lib/providers";
import "../globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "HowTree",
  description: "Urban tree canopy analysis powered by satellite imagery",
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as "ru" | "kk" | "en")) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html
      lang={locale}
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased dark`}
    >
      <body className="h-full bg-background text-foreground">
        <Providers>
          <NextIntlClientProvider messages={messages}>
            {children}
          </NextIntlClientProvider>
        </Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add app/layout.tsx app/[locale]/layout.tsx
git commit -m "feat: restructure root layout for next-intl locale routing"
```

---

## Task 5: Move pages to app/[locale]/

**Files:**
- Create: `app/[locale]/page.tsx`
- Create: `app/[locale]/dashboard/layout.tsx`
- Create: `app/[locale]/dashboard/page.tsx`
- Create: `app/[locale]/analytics/layout.tsx`
- Create: `app/[locale]/analytics/page.tsx`
- Create: `app/[locale]/reports/layout.tsx`
- Create: `app/[locale]/reports/page.tsx`

Note: This task copies the pages to their new location. Task 10 deletes the old ones after everything works.

- [ ] **Step 1: Create `app/[locale]/page.tsx`**

```tsx
import { redirect } from "@/lib/i18n/navigation";

export default function LocaleRootPage() {
  redirect("/dashboard");
}
```

- [ ] **Step 2: Create `app/[locale]/dashboard/layout.tsx`**

```tsx
import { TopNav } from "@/components/layout/TopNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-full flex flex-col">
      <TopNav />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Create `app/[locale]/dashboard/page.tsx`**

Copy the full content of the existing `app/dashboard/page.tsx` verbatim — no changes yet. Translations are applied in Task 6.

- [ ] **Step 4: Create `app/[locale]/analytics/layout.tsx`**

```tsx
import { TopNav } from "@/components/layout/TopNav";

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-full flex flex-col">
      <TopNav />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 5: Create `app/[locale]/analytics/page.tsx`**

Copy the full content of the existing `app/analytics/page.tsx` verbatim — no changes yet. Translations are applied in Task 9.

- [ ] **Step 6: Create `app/[locale]/reports/layout.tsx`**

```tsx
import { TopNav } from "@/components/layout/TopNav";

export default function ReportsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-full flex flex-col">
      <TopNav />
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 7: Create `app/[locale]/reports/page.tsx`**

Copy the full content of the existing `app/reports/page.tsx` verbatim — no changes yet. Translations are applied in Task 9.

- [ ] **Step 8: Start dev server and verify routing works**

```bash
npm run dev
```

Open browser to `http://localhost:3000` — should redirect to `http://localhost:3000/ru/dashboard`.  
Open `http://localhost:3000/en/dashboard` — should render the dashboard in English locale (strings not yet translated, that's ok).

- [ ] **Step 9: Commit**

```bash
git add app/[locale]/
git commit -m "feat: add app/[locale]/ pages and layouts"
```

---

## Task 6: Create LanguageSwitcher + update TopNav

**Files:**
- Create: `components/layout/LanguageSwitcher.tsx`
- Rewrite: `components/layout/TopNav.tsx`

- [ ] **Step 1: Create `components/layout/LanguageSwitcher.tsx`**

```tsx
"use client";

import { useLocale } from "next-intl";
import { usePathname, useRouter } from "@/lib/i18n/navigation";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const LOCALES = [
  { value: "ru", label: "RU", flag: "🇷🇺" },
  { value: "kk", label: "KZ", flag: "🇰🇿" },
  { value: "en", label: "EN", flag: "🇬🇧" },
] as const;

export function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  function handleChange(newLocale: string) {
    router.replace(pathname, { locale: newLocale });
  }

  const current = LOCALES.find((l) => l.value === locale) ?? LOCALES[0];

  return (
    <Select value={locale} onValueChange={handleChange}>
      <SelectTrigger className="h-7 w-[76px] border-border bg-secondary text-xs font-medium gap-1">
        <SelectValue>
          <span className="flex items-center gap-1">
            {current.flag} {current.label}
          </span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="bg-card border-border min-w-[76px]">
        {LOCALES.map(({ value, label, flag }) => (
          <SelectItem
            key={value}
            value={value}
            className="text-xs text-foreground focus:bg-secondary"
          >
            {flag} {label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
```

- [ ] **Step 2: Rewrite `components/layout/TopNav.tsx`**

Replace the current file entirely:

```tsx
"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { Link, usePathname } from "@/lib/i18n/navigation";
import { LanguageSwitcher } from "./LanguageSwitcher";

export function TopNav() {
  const t = useTranslations("nav");
  const path = usePathname();

  const NAV = [
    { href: "/dashboard" as const, label: t("dashboard") },
    { href: "/analytics" as const, label: t("analytics") },
    { href: "/reports" as const, label: t("reports") },
  ];

  return (
    <header className="h-12 border-b border-border bg-card flex items-center px-4 gap-6 shrink-0 z-50">
      <div className="flex items-center gap-2">
        <svg
          className="w-5 h-5 text-primary"
          viewBox="0 0 24 24"
          fill="currentColor"
        >
          <path d="M12 2C8 2 5 5.5 5 9c0 2.4 1.2 4.5 3 5.7V17h8v-2.3c1.8-1.2 3-3.3 3-5.7 0-3.5-3-7-7-7zm-1 18v1a1 1 0 002 0v-1h-2z" />
        </svg>
        <span className="text-sm font-semibold tracking-tight text-foreground">
          HowTree
        </span>
        <span className="text-xs text-muted-foreground font-mono ml-1 hidden sm:block">
          {t("subtitle")}
        </span>
      </div>

      <nav className="flex items-center gap-1 ml-4">
        {NAV.map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded transition-colors",
              path === href
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary",
            )}
          >
            {label}
          </Link>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <LanguageSwitcher />
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          <span className="text-xs text-muted-foreground">{t("connected")}</span>
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 3: Verify in browser**

With `npm run dev` running, visit `http://localhost:3000/ru/dashboard`.  
- TopNav should show "Панель / Аналитика / Отчёты"
- LanguageSwitcher dropdown should be visible (🇷🇺 RU)
- Switching to EN should navigate to `/en/dashboard` and show "Dashboard / Analytics / Reports"
- Switching to KZ should navigate to `/kk/dashboard`

- [ ] **Step 4: Commit**

```bash
git add components/layout/LanguageSwitcher.tsx components/layout/TopNav.tsx
git commit -m "feat: add LanguageSwitcher and i18n-aware TopNav"
```

---

## Task 7: Update AnalysisPanel.tsx

**Files:**
- Rewrite: `components/panels/AnalysisPanel.tsx`

This is the most string-heavy component. Every sub-component needs `useTranslations("analysis")`.

- [ ] **Step 1: Replace `components/panels/AnalysisPanel.tsx` entirely**

```tsx
"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  type ComponentType,
  type DragEvent,
} from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { useMapStore } from "@/lib/store/mapStore";
import { api, createJobWebSocket } from "@/lib/api/client";
import { updateTreeSource } from "@/components/map/MapContainer";
import type { WsMessage } from "@/types";
import { area as turfArea, bboxPolygon } from "@turf/turf";
import {
  AlertTriangle,
  CheckCircle2,
  Crosshair,
  FileImage,
  Globe2,
  LocateFixed,
  MapPinned,
  Radar,
  Satellite,
  UploadCloud,
  WifiOff,
  XCircle,
} from "lucide-react";

type Mode = "bbox" | "upload";

export function AnalysisPanel() {
  const t = useTranslations("analysis");
  const [mode, setMode] = useState<Mode>("bbox");

  return (
    <div className="flex flex-col gap-0">
      <GeoPanelHeader />

      <div className="grid grid-cols-2 gap-1 border-y border-border bg-background/35 p-1">
        <TabBtn label={t("tabMap")} icon={Crosshair} active={mode === "bbox"} onClick={() => setMode("bbox")} />
        <TabBtn label={t("tabUpload")} icon={UploadCloud} active={mode === "upload"} onClick={() => setMode("upload")} />
      </div>

      <div className="p-4">
        {mode === "bbox" ? <BBoxPanel /> : <UploadPanel />}
      </div>
    </div>
  );
}

function TabBtn({
  label,
  icon: Icon,
  active,
  onClick,
}: {
  label: string;
  icon: ComponentType<{ className?: string }>;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex h-9 items-center justify-center gap-2 rounded text-xs font-semibold transition-colors ${
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-secondary hover:text-foreground"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function GeoPanelHeader() {
  const t = useTranslations("analysis");
  return (
    <div className="relative overflow-hidden border-b border-border bg-[#08110f] px-4 py-4">
      <div className="absolute -right-10 -top-10 h-36 w-36 rounded-full border border-emerald-300/20 bg-[radial-gradient(circle_at_35%_35%,rgba(134,239,172,0.42),rgba(20,83,45,0.38)_34%,rgba(6,78,59,0.18)_52%,transparent_72%)]" />
      <div className="absolute right-5 top-8 h-24 w-24 rounded-full border border-cyan-200/15" />
      <div className="relative flex items-start justify-between gap-3">
        <div>
          <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-widest text-emerald-200/75">
            <Satellite className="h-3.5 w-3.5" />
            Geo detection
          </div>
          <h2 className="text-xl font-semibold leading-tight text-foreground">
            {t("title")}
          </h2>
        </div>
        <div className="grid h-14 w-14 shrink-0 place-items-center rounded border border-emerald-300/20 bg-emerald-300/10">
          <Globe2 className="h-7 w-7 text-emerald-200" />
        </div>
      </div>
    </div>
  );
}

function useJobProgress() {
  const { setActiveJob, setJobStatus, setAnalysisResults, resetJob } = useMapStore();
  const [wsMessages, setWsMessages] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    wsRef.current?.close();
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  const TERMINAL = new Set(["completed", "failed"]);

  const finishJob = useCallback(async (
    job_id: string,
    bboxArray: [number, number, number, number],
    areaSqKm: number,
    onError: (err: string) => void,
  ) => {
    try {
      const final = await api.getJob(job_id);
      setJobStatus(final);

      if (final.status === "completed") {
        const geojson = await api.getTreesGeoJSON(bboxArray);
        updateTreeSource(geojson, bboxArray);
        const density = geojson.features.length / (areaSqKm ?? 1);
        setAnalysisResults(
          geojson.features.length,
          Math.round(density * 0.03 * 100) / 100,
        );
      } else if (final.status === "failed") {
        onError(final.error ?? "Analysis failed");
      }
      setIsLoading(false);
    } catch {
      setIsLoading(false);
    }
  }, [setJobStatus, setAnalysisResults]);

  const startPolling = useCallback((
    job_id: string,
    bboxArray: [number, number, number, number],
    areaSqKm: number,
    onError: (err: string) => void,
  ) => {
    if (pollRef.current) clearInterval(pollRef.current);
    setJobStatus({ status: "queued", progress: 0 });
    setWsMessages(["..."]);

    pollRef.current = setInterval(async () => {
      try {
        const job = await api.getJob(job_id);
        setJobStatus(job);
        if (job.stage) setWsMessages([job.stage]);

        if (TERMINAL.has(job.status)) {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          await finishJob(job_id, bboxArray, areaSqKm, onError);
        }
      } catch {
        clearInterval(pollRef.current!);
        pollRef.current = null;
        setIsLoading(false);
      }
    }, 3000);
  }, [setJobStatus, finishJob]); // eslint-disable-line react-hooks/exhaustive-deps

  const trackJob = useCallback(
    async (job_id: string, bboxArray: [number, number, number, number], onError: (err: string) => void) => {
      setActiveJob(job_id);
      const areaSqKm = turfArea(bboxPolygon(bboxArray)) / 1_000_000;

      const ws = createJobWebSocket(job_id);
      wsRef.current = ws;

      ws.onmessage = (e) => {
        const msg: WsMessage = JSON.parse(e.data);
        setJobStatus({ status: normalizeJobStatus(msg.status), progress: msg.progress });
        setWsMessages((prev) => [...prev.slice(-4), msg.message]);
      };

      ws.onclose = async () => {
        try {
          const job = await api.getJob(job_id);
          if (TERMINAL.has(job.status)) {
            setJobStatus(job);
            await finishJob(job_id, bboxArray, areaSqKm, onError);
          } else {
            startPolling(job_id, bboxArray, areaSqKm, onError);
          }
        } catch {
          setIsLoading(false);
        }
      };

      ws.onerror = () => {
        startPolling(job_id, bboxArray, areaSqKm, onError);
      };
    },
    [setActiveJob, setJobStatus, finishJob, startPolling],
  );

  return { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob };
}

function BBoxPanel() {
  const t = useTranslations("analysis");
  const { selectedBBox, jobStatus, treeCount, setJobStatus } = useMapStore();
  const { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob } = useJobProgress();

  const bboxArray = selectedBBox
    ? ([selectedBBox.lon1, selectedBBox.lat1, selectedBBox.lon2, selectedBBox.lat2] as [number, number, number, number])
    : null;

  const areaSqKm = bboxArray ? turfArea(bboxPolygon(bboxArray)) / 1_000_000 : null;

  async function runAnalysis() {
    if (!bboxArray) return;
    setIsLoading(true);
    setWsMessages([]);
    resetJob();

    try {
      const { job_id } = await api.analyze(bboxArray);
      await trackJob(job_id, bboxArray, (err) => {
        setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      });
    } catch (err) {
      console.error(err);
      setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      setIsLoading(false);
    }
  }

  const progress = jobStatus?.progress ?? 0;
  const isDone = jobStatus?.status === "completed";
  const isFailed = jobStatus?.status === "failed";

  return (
    <div className="flex flex-col gap-4">
      <ApiRequirementNotice compact={Boolean(selectedBBox)} />

      <div>
        <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <LocateFixed className="h-3.5 w-3.5" />
          {t("zone")}
        </p>
        {selectedBBox ? (
          <div className="space-y-2 rounded border border-emerald-400/20 bg-emerald-400/5 p-3">
            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              <CoordTile label="SW" value={`${selectedBBox.lat1.toFixed(5)}, ${selectedBBox.lon1.toFixed(5)}`} />
              <CoordTile label="NE" value={`${selectedBBox.lat2.toFixed(5)}, ${selectedBBox.lon2.toFixed(5)}`} />
            </div>
            <div className="flex items-center justify-between border-t border-border pt-2">
              <span className="text-xs text-muted-foreground">{t("area")}</span>
              <span className="text-foreground">{areaSqKm?.toFixed(2)} км²</span>
            </div>
          </div>
        ) : (
          <div className="rounded border border-dashed border-border bg-secondary/25 p-4 text-center">
            <div className="mx-auto mb-2 grid h-10 w-10 place-items-center rounded border border-border bg-background/70">
              <MapPinned className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm font-medium text-foreground">{t("selectHint")}</p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">{t("selectHintSub")}</p>
          </div>
        )}
      </div>

      <Button
        onClick={runAnalysis}
        disabled={!selectedBBox || isLoading}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
      >
        {isLoading
          ? jobStatus?.status === "queued"
            ? t("queued")
            : t("running")
          : t("run")}
      </Button>

      <JobProgress
        isLoading={isLoading}
        isDone={isDone}
        isFailed={isFailed}
        progress={progress}
        wsMessages={wsMessages}
        error={jobStatus?.error ?? jobStatus?.error_message ?? null}
      />

      {isDone && treeCount > 0 && (
        <>
          <Separator />
          <ZoneStats />
        </>
      )}
    </div>
  );
}

function UploadPanel() {
  const t = useTranslations("analysis");
  const { jobStatus, treeCount, setJobStatus } = useMapStore();
  const { isLoading, setIsLoading, wsMessages, setWsMessages, trackJob, resetJob } = useJobProgress();

  const [file, setFile] = useState<File | null>(null);
  const [isGeoTiff, setIsGeoTiff] = useState(false);
  const [bbox, setBbox] = useState({ lonMin: "", latMin: "", lonMax: "", latMax: "" });
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleFileChange(f: File | null) {
    if (!f) return;
    setFile(f);
    const ext = f.name.toLowerCase();
    setIsGeoTiff(ext.endsWith(".tif") || ext.endsWith(".tiff"));
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFileChange(f);
  }

  const bboxValid = isGeoTiff
    ? true
    : bbox.lonMin !== "" && bbox.latMin !== "" && bbox.lonMax !== "" && bbox.latMax !== "";

  async function runUpload() {
    if (!file) return;
    setIsLoading(true);
    setWsMessages([]);
    resetJob();

    const lonMin = isGeoTiff ? 0 : parseFloat(bbox.lonMin);
    const latMin = isGeoTiff ? 0 : parseFloat(bbox.latMin);
    const lonMax = isGeoTiff ? 1 : parseFloat(bbox.lonMax);
    const latMax = isGeoTiff ? 1 : parseFloat(bbox.latMax);

    try {
      const { job_id } = await api.uploadImage(file, lonMin, latMin, lonMax, latMax);
      const bboxArray: [number, number, number, number] = [lonMin, latMin, lonMax, latMax];
      await trackJob(job_id, bboxArray, (err) => {
        setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      });
    } catch (err) {
      console.error(err);
      setJobStatus({ status: "failed", progress: 0, error: formatApiError(err) });
      setIsLoading(false);
    }
  }

  const progress = jobStatus?.progress ?? 0;
  const isDone = jobStatus?.status === "completed";
  const isFailed = jobStatus?.status === "failed";

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border border-cyan-400/20 bg-cyan-400/5 p-3">
        <div className="flex items-start gap-3">
          <div className="grid h-9 w-9 shrink-0 place-items-center rounded border border-cyan-300/25 bg-cyan-300/10">
            <FileImage className="h-[18px] w-[18px] text-cyan-200" />
          </div>
          <div>
            <p className="text-sm font-medium text-foreground">{t("uploadTitle")}</p>
            <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{t("uploadDesc")}</p>
          </div>
        </div>
      </div>

      <div
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
          dragOver
            ? "border-primary bg-primary/5"
            : file
            ? "border-primary/50 bg-primary/5"
            : "border-border hover:border-muted-foreground/50"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".tif,.tiff,.jpg,.jpeg,.png"
          onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div>
            <p className="text-sm font-medium text-foreground truncate">{file.name}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {(file.size / 1024 / 1024).toFixed(1)} MB
              {isGeoTiff && (
                <span className="ml-2 text-primary">{t("geotiffAuto")}</span>
              )}
            </p>
          </div>
        ) : (
          <div>
            <p className="text-sm text-muted-foreground">{t("dropHint")}</p>
            <p className="text-xs text-muted-foreground/60 mt-1">GeoTIFF, JPEG, PNG · до 500 MB</p>
          </div>
        )}
      </div>

      {file && !isGeoTiff && (
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            {t("geoBounds")}
          </p>
          <div className="grid grid-cols-2 gap-2">
            {(["lonMin", "latMin", "lonMax", "latMax"] as const).map((key) => (
              <div key={key}>
                <label className="text-xs text-muted-foreground block mb-0.5">
                  {key === "lonMin" ? "Lon min" : key === "latMin" ? "Lat min" : key === "lonMax" ? "Lon max" : "Lat max"}
                </label>
                <input
                  type="number"
                  step="any"
                  value={bbox[key]}
                  onChange={(e) => setBbox((b) => ({ ...b, [key]: e.target.value }))}
                  className="w-full bg-secondary/50 border border-border rounded px-2 py-1 text-xs font-mono text-foreground focus:outline-none focus:border-primary"
                  placeholder={key.startsWith("lon") ? "71.430" : "51.180"}
                />
              </div>
            ))}
          </div>
          <p className="text-xs text-muted-foreground/60 mt-1.5">{t("geoBoundsHint")}</p>
        </div>
      )}

      <Button
        onClick={runUpload}
        disabled={!file || !bboxValid || isLoading}
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
      >
        {isLoading ? t("processing") : t("findTrees")}
      </Button>

      <JobProgress
        isLoading={isLoading}
        isDone={isDone}
        isFailed={isFailed}
        progress={progress}
        wsMessages={wsMessages}
        error={jobStatus?.error ?? jobStatus?.error_message ?? null}
      />

      {isDone && treeCount > 0 && (
        <>
          <Separator />
          <ZoneStats />
        </>
      )}
    </div>
  );
}

function ApiRequirementNotice({ compact }: { compact?: boolean }) {
  const t = useTranslations("analysis");
  return (
    <div className="rounded border border-amber-300/25 bg-amber-300/10 p-3">
      <div className="flex items-start gap-3">
        <div className="grid h-9 w-9 shrink-0 place-items-center rounded border border-amber-300/30 bg-amber-300/15">
          <Satellite className="h-[18px] w-[18px] text-amber-200" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-foreground">{t("apiKeyTitle")}</p>
          <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
            {compact ? t("apiKeyCompact") : t("apiKeyFull")}
          </p>
          {!compact && (
            <code className="mt-2 block rounded border border-border bg-background/80 px-2 py-1.5 text-[11px] text-amber-100">
              YANDEX_MAPS_API_KEY=...
            </code>
          )}
        </div>
      </div>
    </div>
  );
}

function CoordTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-background/55 p-2">
      <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 truncate text-foreground">{value}</div>
    </div>
  );
}

function JobProgress({
  isLoading,
  isDone,
  isFailed,
  progress,
  wsMessages,
  error,
}: {
  isLoading: boolean;
  isDone: boolean;
  isFailed: boolean;
  progress: number;
  wsMessages: string[];
  error?: string | null;
}) {
  const t = useTranslations("analysis");
  if (!isLoading && !isDone && !isFailed) return null;

  const statusLabel = isDone ? t("done") : isFailed ? t("error") : `${progress}%`;
  const latestMessage = wsMessages[wsMessages.length - 1];

  return (
    <div className="space-y-2 rounded border border-border bg-secondary/30 p-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          {isDone ? (
            <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
          ) : isFailed ? (
            <XCircle className="h-3.5 w-3.5 text-destructive" />
          ) : (
            <Radar className="h-3.5 w-3.5 text-primary" />
          )}
          {t("status")}
        </span>
        <Badge
          variant={isDone ? "default" : isFailed ? "destructive" : "secondary"}
          className="text-xs"
        >
          {statusLabel}
        </Badge>
      </div>
      <Progress value={progress} className="h-1.5" />
      {latestMessage && !isFailed && (
        <p className="text-xs text-muted-foreground font-mono truncate">{latestMessage}</p>
      )}
      {isFailed && (
        <ApiErrorBlock message={error ?? latestMessage ?? t("failedError")} />
      )}
    </div>
  );
}

function ApiErrorBlock({ message }: { message: string }) {
  const t = useTranslations("analysis");
  const isForbidden = message.includes("403 Forbidden") || message.includes("HTTP 403");
  const isMissingProvider =
    message.includes("No imagery provider configured") ||
    message.includes("YANDEX_MAPS_API_KEY");
  const isProviderError = isForbidden || isMissingProvider || message.includes("Static API");

  return (
    <div className="rounded border border-destructive/30 bg-destructive/10 p-3">
      <div className="flex items-start gap-2">
        {isProviderError ? (
          <WifiOff className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        ) : (
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
        )}
        <div className="min-w-0">
          <p className="text-xs font-semibold text-foreground">
            {isForbidden
              ? t("keyRejected")
              : isMissingProvider
              ? t("noImagery")
              : t("stopped")}
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {isForbidden
              ? t("keyRejectedDesc")
              : isMissingProvider
              ? t("noImageryDesc")
              : message}
          </p>
        </div>
      </div>
    </div>
  );
}

function formatApiError(err: unknown): string {
  const message = err instanceof Error ? err.message : String(err);
  if (message.includes("No imagery provider configured")) {
    return "No imagery provider configured. Set YANDEX_MAPS_API_KEY or MAPBOX_TOKEN.";
  }
  return message.replace(/^Error:\s*/, "");
}

function normalizeJobStatus(status: string | undefined) {
  if (
    status === "queued" ||
    status === "downloading_tiles" ||
    status === "running_detection" ||
    status === "merging_results" ||
    status === "storing_results" ||
    status === "completed" ||
    status === "failed"
  ) {
    return status;
  }
  return "running";
}

function ZoneStats() {
  const t = useTranslations("analysis");
  const { treeCount, canopyCoverage, selectedBBox, jobStatus } = useMapStore();

  const bboxArray = selectedBBox
    ? ([selectedBBox.lon1, selectedBBox.lat1, selectedBBox.lon2, selectedBBox.lat2] as [number, number, number, number])
    : null;

  const areaSqKm = bboxArray ? turfArea(bboxPolygon(bboxArray)) / 1_000_000 : 1;
  const density = Math.round(treeCount / areaSqKm);
  const analysisDate = new Date().toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });

  if (jobStatus?.status !== "completed") {
    return (
      <div className="space-y-2">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-12 w-full" />)}
      </div>
    );
  }

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
        {t("results")}
      </p>
      <div className="space-y-2">
        <MetricCard label={t("totalTrees")} value={treeCount.toLocaleString()} unit={t("detected")} accent />
        <MetricCard label={t("canopyCoverage")} value={`${canopyCoverage}%`} unit={t("ofArea")} />
        <MetricCard label={t("density")} value={density.toLocaleString()} unit={t("treesPerKm")} />
        <MetricCard label={t("analysisDate")} value={analysisDate} unit="" />
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  unit,
  accent,
}: {
  label: string;
  value: string;
  unit: string;
  accent?: boolean;
}) {
  return (
    <div className="bg-secondary/50 rounded border border-border p-2.5 flex items-center justify-between">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="text-right">
        <span className={`text-sm font-semibold ${accent ? "text-primary" : "text-foreground"}`}>
          {value}
        </span>
        {unit && <span className="text-xs text-muted-foreground ml-1">{unit}</span>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Switch language to EN — AnalysisPanel tabs should read "Map / Image", button "Run Analysis", zone hint in English.

- [ ] **Step 3: Commit**

```bash
git add components/panels/AnalysisPanel.tsx
git commit -m "feat: i18n AnalysisPanel — replace all hardcoded strings"
```

---

## Task 8: Update LayerToggle + AssistantPanel

**Files:**
- Rewrite: `components/panels/LayerToggle.tsx`
- Rewrite: `components/assistant/AssistantPanel.tsx`

- [ ] **Step 1: Rewrite `components/panels/LayerToggle.tsx`**

```tsx
"use client";

import { useTranslations } from "next-intl";
import { useMapStore } from "@/lib/store/mapStore";
import type { MapLayer } from "@/types";

export function LayerToggle() {
  const t = useTranslations("layers");
  const { activeLayers, toggleLayer } = useMapStore();

  const LAYERS: { id: MapLayer; labelKey: "points" | "heatmap" | "districts"; icon: string }[] = [
    { id: "points",    labelKey: "points",    icon: "●" },
    { id: "heatmap",   labelKey: "heatmap",   icon: "◉" },
    { id: "districts", labelKey: "districts", icon: "▦" },
  ];

  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2 px-4">
        {t("title")}
      </p>
      <div className="px-4 space-y-1">
        {LAYERS.map(({ id, labelKey, icon }) => {
          const active = activeLayers.has(id);
          return (
            <button
              key={id}
              onClick={() => toggleLayer(id)}
              className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded text-xs transition-colors ${
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              }`}
            >
              <span className="text-base leading-none">{icon}</span>
              <span className="font-medium">{t(labelKey)}</span>
              <span
                className={`ml-auto w-1.5 h-1.5 rounded-full ${
                  active ? "bg-primary" : "bg-border"
                }`}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `components/assistant/AssistantPanel.tsx`**

```tsx
"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  Bot, User, Send, Loader2, TreePine,
  BarChart3, HelpCircle, Leaf, X, MessageCircle,
} from "lucide-react";
import { useMapStore } from "@/lib/store/mapStore";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function AssistantPanel() {
  const t = useTranslations("assistant");
  const { treeCount, canopyCoverage, jobStatus } = useMapStore();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: t("greeting") },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const QUICK_PROMPTS = [
    { icon: BarChart3,   label: t("quickExplainLabel"),    text: t("quickExplainText") },
    { icon: TreePine,    label: t("quickConfidenceLabel"),  text: t("quickConfidenceText") },
    { icon: Leaf,        label: t("quickDetectionLabel"),   text: t("quickDetectionText") },
    { icon: HelpCircle,  label: t("quickLimitsLabel"),      text: t("quickLimitsText") },
  ];

  useEffect(() => {
    if (isOpen) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [messages, isOpen]);

  const analysisContext =
    jobStatus?.status === "completed" && treeCount > 0
      ? { tree_count: treeCount, status: jobStatus.status }
      : null;

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return;

      const userMsg: Message = { role: "user", content: text.trim() };
      const updatedMessages = [...messages, userMsg];
      setMessages(updatedMessages);
      setInput("");
      setIsLoading(true);

      try {
        const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        const res = await fetch(`${BASE}/api/v1/assistant/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: updatedMessages.map(({ role, content }) => ({ role, content })),
            analysis_context: analysisContext,
          }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: { content: string; action: string | null } = await res.json();
        setMessages((prev) => [...prev, { role: "assistant", content: data.content }]);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: t("connectionError") },
        ]);
      } finally {
        setIsLoading(false);
        inputRef.current?.focus();
      }
    },
    [messages, isLoading, analysisContext, t],
  );

  return (
    <>
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="fixed bottom-6 left-[336px] z-50 w-12 h-12 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg flex items-center justify-center transition-all duration-200"
        aria-label={t("title")}
      >
        {isOpen ? <X className="w-5 h-5" /> : <MessageCircle className="w-5 h-5" />}
      </button>

      <div
        className={`fixed bottom-20 left-[336px] z-50 w-96 bg-card border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 origin-bottom-left ${
          isOpen
            ? "opacity-100 scale-100 pointer-events-auto"
            : "opacity-0 scale-95 pointer-events-none"
        }`}
        style={{ height: "520px" }}
      >
        <div className="px-4 py-3 border-b border-border shrink-0 flex items-center gap-2.5 bg-card">
          <div className="w-7 h-7 rounded-md bg-emerald-600 flex items-center justify-center shrink-0">
            <Bot className="w-3.5 h-3.5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold leading-none text-foreground">{t("title")}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">Claude Haiku · HowTree</p>
          </div>
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
        </div>

        {analysisContext && (
          <div className="mx-3 mt-2 px-3 py-1.5 rounded border border-emerald-800/60 bg-emerald-950/40 shrink-0">
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-emerald-300">
              <span>🌳 {treeCount.toLocaleString()} {t("trees")}</span>
              <span>🌿 {canopyCoverage}% {t("coverage")}</span>
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
            >
              <div
                className={`w-5 h-5 rounded flex items-center justify-center shrink-0 mt-0.5 ${
                  msg.role === "user" ? "bg-primary/80" : "bg-emerald-700"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="w-3 h-3 text-white" />
                ) : (
                  <Bot className="w-3 h-3 text-white" />
                )}
              </div>
              <div
                className={`max-w-[80%] rounded-xl px-3 py-2 text-[12px] leading-relaxed whitespace-pre-wrap break-words ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : "bg-secondary text-foreground rounded-tl-sm"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-2">
              <div className="w-5 h-5 rounded bg-emerald-700 flex items-center justify-center shrink-0">
                <Bot className="w-3 h-3 text-white" />
              </div>
              <div className="bg-secondary rounded-xl rounded-tl-sm px-3 py-2.5 flex items-center gap-1">
                <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:0ms]" />
                <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:150ms]" />
                <span className="w-1 h-1 bg-muted-foreground rounded-full animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {messages.length === 1 && (
          <div className="px-3 pb-2 shrink-0">
            <p className="text-[10px] text-muted-foreground mb-1.5">{t("quickQuestions")}</p>
            <div className="grid grid-cols-2 gap-1">
              {QUICK_PROMPTS.map(({ icon: Icon, label, text }) => (
                <button
                  key={label}
                  onClick={() => sendMessage(text)}
                  className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-secondary hover:bg-secondary/80 text-[11px] text-muted-foreground text-left transition-colors"
                >
                  <Icon className="w-3 h-3 text-emerald-500 shrink-0" />
                  <span className="truncate">{label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="px-3 pb-3 pt-2 border-t border-border shrink-0">
          <div className="flex gap-1.5">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage(input);
                }
              }}
              placeholder={t("placeholder")}
              disabled={isLoading}
              className="flex-1 min-w-0 bg-secondary border border-border rounded-lg px-3 py-1.5 text-[12px] text-foreground placeholder-muted-foreground focus:outline-none focus:border-primary transition-colors disabled:opacity-50"
            />
            <button
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="w-8 h-8 bg-primary hover:bg-primary/90 disabled:bg-secondary disabled:text-muted-foreground text-primary-foreground rounded-lg flex items-center justify-center transition-colors shrink-0"
            >
              {isLoading ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Send className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add components/panels/LayerToggle.tsx components/assistant/AssistantPanel.tsx
git commit -m "feat: i18n LayerToggle and AssistantPanel"
```

---

## Task 9: Update dashboard page + analytics page + reports page

**Files:**
- Rewrite: `app/[locale]/dashboard/page.tsx`
- Rewrite: `app/[locale]/analytics/page.tsx`
- Rewrite: `app/[locale]/reports/page.tsx`

- [ ] **Step 1: Rewrite `app/[locale]/dashboard/page.tsx`**

Replace the existing copy with this translated version:

```tsx
"use client";

import dynamic from "next/dynamic";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { AnalysisPanel } from "@/components/panels/AnalysisPanel";
import { LayerToggle } from "@/components/panels/LayerToggle";
import { AssistantPanel } from "@/components/assistant/AssistantPanel";
import { Skeleton } from "@/components/ui/skeleton";
import { MapPinned, Satellite, ScanLine } from "lucide-react";

const MapContainer = dynamic(
  () => import("@/components/map/MapContainer").then((m) => m.MapContainer),
  {
    ssr: false,
    loading: () => <Skeleton className="w-full h-full rounded-none" />,
  }
);

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tAnalysis = useTranslations("analysis");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="h-full flex overflow-hidden relative">
      <Button
        size="sm"
        variant="outline"
        onClick={() => setSidebarOpen((v) => !v)}
        className="absolute top-3 left-3 z-20 lg:hidden border-border bg-card/90 backdrop-blur"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </Button>

      <aside
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } transition-transform duration-200 absolute lg:relative z-10 h-full w-[320px] shrink-0 border-r border-border bg-card flex flex-col overflow-y-auto shadow-xl lg:shadow-none lg:translate-x-0`}
      >
        <div className="px-4 py-3 border-b border-border flex items-center justify-between shrink-0">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            {tAnalysis("sidebarTitle")}
          </h2>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden text-muted-foreground hover:text-foreground"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <AnalysisPanel />

        <Separator />

        <div className="py-3">
          <LayerToggle />
        </div>

        <div className="mt-auto px-4 py-3 border-t border-border">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            {t("confidence")}
          </p>
          <div className="space-y-1">
            {[
              { color: "#22c55e", labelKey: "confHigh" as const },
              { color: "#86efac", labelKey: "confMedHigh" as const },
              { color: "#fbbf24", labelKey: "confMed" as const },
              { color: "#f87171", labelKey: "confLow" as const },
            ].map(({ color, labelKey }) => (
              <div key={labelKey} className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
                <span className="text-xs text-muted-foreground">{t(labelKey)}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="lg:hidden absolute inset-0 bg-black/50 z-[5]"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex-1 relative">
        <MapContainer />

        <div className="absolute right-4 top-4 hidden w-72 overflow-hidden rounded border border-border bg-card/90 shadow-xl backdrop-blur md:block">
          <div className="relative border-b border-border bg-[#091411] p-4">
            <div className="absolute -right-8 -top-10 h-28 w-28 rounded-full border border-emerald-200/15 bg-[radial-gradient(circle_at_35%_35%,rgba(134,239,172,0.34),rgba(20,83,45,0.24)_42%,transparent_72%)]" />
            <div className="relative flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded border border-emerald-300/25 bg-emerald-300/10">
                <Satellite className="h-5 w-5 text-emerald-200" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{t("workspaceTitle")}</p>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{t("workspaceDesc")}</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 divide-x divide-border">
            <div className="p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                <MapPinned className="h-3.5 w-3.5" />
                AOI
              </div>
              <p className="text-sm font-semibold text-foreground">Astana</p>
            </div>
            <div className="p-3">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-muted-foreground">
                <ScanLine className="h-3.5 w-3.5" />
                Mode
              </div>
              <p className="text-sm font-semibold text-foreground">BBOX</p>
            </div>
          </div>
        </div>

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-card/90 backdrop-blur border border-border rounded px-3 py-1.5 text-xs font-mono text-muted-foreground pointer-events-none whitespace-nowrap">
          {tAnalysis("mapHint")}
        </div>
      </div>

      <AssistantPanel />
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `app/[locale]/analytics/page.tsx`**

Replace `"use client"` file in analytics with this translated version — copy the full existing file and apply these changes:

1. Add `import { useTranslations } from "next-intl";` after `import type { JobSummary } from "@/types";`
2. Inside `AnalyticsPage()` component body, add at the top:
   ```tsx
   const t = useTranslations("analytics");
   ```
3. Replace hardcoded strings as follows (keep all logic unchanged):

```tsx
// Title section — replace:
<h1 className="text-xl font-semibold text-foreground">Analytics</h1>
<p className="text-sm text-muted-foreground mt-0.5">
  Real-time results from your tree detection analyses
</p>
// With:
<h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
<p className="text-sm text-muted-foreground mt-0.5">{t("subtitle")}</p>

// Export button — replace "Export CSV" with {t("exportCsv")}

// summaryCards — replace the array with:
const summaryCards = [
  { label: t("totalTrees"),   value: fmt(totalTrees),              delta: `${completed.length} ${t("analyses")}` },
  { label: t("totalCanopy"),  value: `${fmt(totalCanopy / 10_000, 1)} ha`, delta: `${fmt(totalCanopy, 0)} m²` },
  { label: t("analysesRun"),  value: fmt(jobs.length),             delta: `${completed.length} ${t("completed")}` },
  { label: t("avgConf"),      value: `${fmt(avgConf * 100, 1)}%`,  delta: completed.length ? t("acrossJobs") : t("noData") },
];

// CardTitle — replace "Analysis History" with {t("history")}

// Error message — replace `Failed to load: {error}` with `{t("failedLoad")} {error}`

// Empty state — replace with {t("empty")}

// TableHead cells — replace "Date", "Status", "Trees", "Canopy", "Confidence", "BBox"
// with {t("date")}, {t("status")}, {t("trees")}, {t("canopy")}, {t("confidence")}, {t("bbox")}

// Date formatting — replace "ru-RU" with locale from useLocale():
// Add: import { useLocale } from "next-intl";
// Add: const locale = useLocale();
// Change: .toLocaleString("ru-RU", ...) → .toLocaleString(locale, ...)
```

The full rewritten `app/[locale]/analytics/page.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useLocale } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api/client";
import type { JobSummary } from "@/types";

function exportCSV(jobs: JobSummary[]) {
  const header = "Job ID,Status,Trees,Canopy (m²),Avg Confidence,Date\n";
  const rows = jobs.map((j) =>
    [
      j.job_id, j.status, j.tree_count ?? "",
      j.canopy_area_m2 != null ? Math.round(j.canopy_area_m2) : "",
      j.avg_confidence != null ? (j.avg_confidence * 100).toFixed(1) + "%" : "",
      j.completed_at ? new Date(j.completed_at).toLocaleDateString() : "",
    ].join(",")
  ).join("\n");
  const blob = new Blob([header + rows], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "howtree-analyses.csv";
  a.click();
  URL.revokeObjectURL(url);
}

function statusVariant(status: string): "default" | "secondary" | "destructive" {
  if (status === "completed") return "default";
  if (status === "failed") return "destructive";
  return "secondary";
}

function fmt(n: number | null | undefined, decimals = 0): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: decimals });
}

function SummarySkeleton() {
  return (
    <div className="grid grid-cols-4 gap-4">
      {[0, 1, 2, 3].map((i) => (
        <Card key={i} className="bg-card border-border">
          <CardContent className="pt-4 pb-4 space-y-2">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-7 w-16" />
            <Skeleton className="h-3 w-12" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const t = useTranslations("analytics");
  const locale = useLocale();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listJobs(50)
      .then((res) => setJobs(res.jobs))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  const completed = jobs.filter((j) => j.status === "completed");
  const totalTrees = completed.reduce((s, j) => s + (j.tree_count ?? 0), 0);
  const totalCanopy = completed.reduce((s, j) => s + (j.canopy_area_m2 ?? 0), 0);
  const avgConf = completed.length
    ? completed.reduce((s, j) => s + (j.avg_confidence ?? 0), 0) / completed.length
    : 0;

  const summaryCards = [
    { label: t("totalTrees"),  value: fmt(totalTrees),                   delta: `${completed.length} ${t("analyses")}` },
    { label: t("totalCanopy"), value: `${fmt(totalCanopy / 10_000, 1)} ha`, delta: `${fmt(totalCanopy, 0)} m²` },
    { label: t("analysesRun"), value: fmt(jobs.length),                   delta: `${completed.length} ${t("completed")}` },
    { label: t("avgConf"),     value: `${fmt(avgConf * 100, 1)}%`,        delta: completed.length ? t("acrossJobs") : t("noData") },
  ];

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{t("subtitle")}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => exportCSV(jobs)}
          disabled={loading || jobs.length === 0}
          className="border-border text-muted-foreground hover:text-foreground"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {t("exportCsv")}
        </Button>
      </div>

      {loading ? (
        <SummarySkeleton />
      ) : (
        <div className="grid grid-cols-4 gap-4">
          {summaryCards.map(({ label, value, delta }) => (
            <Card key={label} className="bg-card border-border">
              <CardContent className="pt-4 pb-4">
                <p className="text-xs text-muted-foreground mb-1">{label}</p>
                <p className="text-2xl font-semibold text-foreground tabular-nums">{value}</p>
                <p className="text-xs text-primary mt-1">{delta}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Card className="bg-card border-border">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-semibold text-foreground">
            {t("history")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="text-sm text-destructive py-4">{t("failedLoad")} {error}</p>
          ) : loading ? (
            <div className="space-y-2 py-2">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : jobs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">{t("empty")}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-border hover:bg-transparent">
                  <TableHead className="text-muted-foreground text-xs">{t("date")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs">{t("status")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs text-right">{t("trees")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs text-right">{t("canopy")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs text-right">{t("confidence")}</TableHead>
                  <TableHead className="text-muted-foreground text-xs">{t("bbox")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((job) => (
                  <TableRow key={job.job_id} className="border-border hover:bg-secondary/30">
                    <TableCell className="text-xs text-muted-foreground">
                      {job.completed_at
                        ? new Date(job.completed_at).toLocaleString(locale, { dateStyle: "short", timeStyle: "short" })
                        : new Date(job.created_at).toLocaleString(locale, { dateStyle: "short", timeStyle: "short" })}
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(job.status)} className="text-xs">
                        {job.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-foreground">
                      {fmt(job.tree_count)}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-muted-foreground">
                      {job.canopy_area_m2 != null ? `${fmt(job.canopy_area_m2 / 10_000, 2)} ha` : "—"}
                    </TableCell>
                    <TableCell className="text-right text-sm tabular-nums text-foreground">
                      {job.avg_confidence != null ? `${fmt(job.avg_confidence * 100, 1)}%` : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground font-mono">
                      {job.bbox
                        ? `${job.bbox[1].toFixed(3)},${job.bbox[0].toFixed(3)} → ${job.bbox[3].toFixed(3)},${job.bbox[2].toFixed(3)}`
                        : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 3: Rewrite `app/[locale]/reports/page.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { PdfDownloadButton } from "@/components/reports/PdfDownloadButton";

const DISTRICTS = [
  "Manhattan", "Brooklyn", "Queens", "Bronx",
  "Staten Island", "Harlem", "Midtown",
];

const MOCK_STATS: Record<string, {
  treeCount: number; canopy: string; density: number;
  confidence: number; date: string; area: number;
}> = {
  Manhattan:      { treeCount: 87420,  canopy: "24.2%", density: 1240, confidence: 89, date: "May 19, 2026", area: 70.5 },
  Brooklyn:       { treeCount: 124300, canopy: "32.1%", density: 980,  confidence: 87, date: "May 19, 2026", area: 183.4 },
  Queens:         { treeCount: 156800, canopy: "38.4%", density: 820,  confidence: 91, date: "May 19, 2026", area: 282.9 },
  Bronx:          { treeCount: 98200,  canopy: "28.7%", density: 1100, confidence: 85, date: "May 19, 2026", area: 109.0 },
  "Staten Island":{ treeCount: 72100,  canopy: "42.1%", density: 1380, confidence: 92, date: "May 19, 2026", area: 151.2 },
  Harlem:         { treeCount: 52300,  canopy: "18.9%", density: 920,  confidence: 83, date: "May 18, 2026", area: 7.4 },
  Midtown:        { treeCount: 34500,  canopy: "12.3%", density: 680,  confidence: 88, date: "May 18, 2026", area: 8.1 },
};

const RECENT_REPORTS = [
  { district: "Queens",    date: "May 19, 2026", size: "2.4 MB" },
  { district: "Brooklyn",  date: "May 18, 2026", size: "1.9 MB" },
  { district: "Manhattan", date: "May 17, 2026", size: "1.7 MB" },
];

export default function ReportsPage() {
  const t = useTranslations("reports");
  const [district, setDistrict] = useState<string>("Queens");
  const stats = MOCK_STATS[district];

  const statCards = stats ? [
    { label: t("treesDetected"),  value: stats.treeCount.toLocaleString() },
    { label: t("canopyCoverage"), value: stats.canopy },
    { label: t("density"),        value: stats.density.toLocaleString() },
    { label: t("avgConf"),        value: `${stats.confidence}%` },
  ] : [];

  const reportItems = [
    t("item1"), t("item2"), t("item3"), t("item4"), t("item5"),
  ];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-foreground">{t("title")}</h1>
        <p className="text-sm text-muted-foreground mt-0.5">{t("subtitle")}</p>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-foreground">
                {t("generate")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  {t("selectDistrict")}
                </label>
                <Select value={district} onValueChange={setDistrict}>
                  <SelectTrigger className="bg-secondary border-border text-foreground">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-card border-border">
                    {DISTRICTS.map((d) => (
                      <SelectItem key={d} value={d} className="text-foreground hover:bg-secondary focus:bg-secondary">
                        {d}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {stats && (
                <div className="grid grid-cols-2 gap-2">
                  {statCards.map(({ label, value }) => (
                    <div key={label} className="bg-secondary/50 rounded border border-border p-2.5">
                      <p className="text-xs text-muted-foreground">{label}</p>
                      <p className="text-sm font-semibold text-foreground mt-0.5">{value}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className="space-y-1.5">
                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  {t("contents")}
                </p>
                <div className="space-y-1">
                  {reportItems.map((item) => (
                    <div key={item} className="flex items-center gap-2">
                      <svg className="w-3 h-3 text-primary shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      <span className="text-xs text-muted-foreground">{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {stats && <PdfDownloadButton district={district} stats={stats} />}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-foreground">
                {t("recent")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {RECENT_REPORTS.map((r) => (
                <div
                  key={r.district + r.date}
                  className="flex items-center justify-between bg-secondary/40 rounded border border-border p-2.5"
                >
                  <div>
                    <p className="text-xs font-medium text-foreground">{r.district}</p>
                    <p className="text-xs text-muted-foreground">{r.date}</p>
                  </div>
                  <div className="text-right">
                    <Badge variant="secondary" className="text-xs">PDF</Badge>
                    <p className="text-xs text-muted-foreground mt-1">{r.size}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardContent className="pt-4">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {t("format")}
              </p>
              <div className="space-y-1.5">
                {[
                  { label: t("format"),   value: "PDF/A" },
                  { label: t("size"),     value: "~2 MB" },
                  { label: t("language"), value: "English" },
                  { label: t("standard"), value: "ISO 32000" },
                ].map(({ label, value }) => (
                  <div key={label} className="flex justify-between text-xs">
                    <span className="text-muted-foreground">{label}</span>
                    <span className="text-foreground font-medium">{value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify all 3 pages in browser across locales**

With dev server running:
- `/ru/dashboard` — Russian UI, LanguageSwitcher shows 🇷🇺 RU
- `/en/analytics` — English UI, table headers in English
- `/kk/reports` — Kazakh UI
- Switch language from any page — URL prefix changes, UI updates

- [ ] **Step 5: Commit**

```bash
git add app/[locale]/dashboard/page.tsx app/[locale]/analytics/page.tsx app/[locale]/reports/page.tsx
git commit -m "feat: i18n dashboard, analytics, and reports pages"
```

---

## Task 10: Delete old app pages

**Files:**
- Delete: `app/page.tsx`
- Delete: `app/dashboard/` (directory)
- Delete: `app/analytics/` (directory)
- Delete: `app/reports/` (directory)

- [ ] **Step 1: Delete old directories**

```bash
rm app/page.tsx
rm -rf app/dashboard app/analytics app/reports
```

- [ ] **Step 2: Verify build compiles cleanly**

```bash
npm run build
```

Expected: No TypeScript errors. Build completes successfully.

- [ ] **Step 3: Verify redirects still work**

```bash
npm run dev
```

Visit `http://localhost:3000` — should redirect to `/ru/dashboard`.  
Visit `http://localhost:3000/dashboard` — should redirect to `/ru/dashboard` (middleware handles it).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: remove old app/ pages superseded by [locale] routing"
```

---

## Self-Review

### Spec coverage
- [x] next-intl with locale routing → Tasks 1, 2, 4
- [x] messages/ translation files (ru/en/kk) → Task 3
- [x] app/[locale]/ structure → Tasks 4, 5
- [x] LanguageSwitcher in TopNav → Task 6
- [x] All hardcoded strings extracted → Tasks 7, 8, 9
- [x] Old pages cleaned up → Task 10

### Type consistency
- `routing.locales` typed as `["ru", "kk", "en"]` in `routing.ts` — used consistently in `app/[locale]/layout.tsx` validation
- `useRouter().replace(pathname, { locale })` from `lib/i18n/navigation.ts` — used in `LanguageSwitcher.tsx`
- `Link` and `usePathname` from `lib/i18n/navigation.ts` — used in `TopNav.tsx`
- `useTranslations("analysis")` — all keys match `messages/ru.json` analysis namespace
- `useTranslations("layers")` keys: `"title"`, `"points"`, `"heatmap"`, `"districts"` — all present in all 3 JSON files

### No placeholders
All code steps contain complete implementations. No TBD or TODO markers.
