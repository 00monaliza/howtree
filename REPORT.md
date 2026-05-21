# Технический отчёт: HowTree — Платформа детекции деревьев

**Версия:** 1.0  
**Дата:** Май 2026  
**Проект:** howTree — автоматизированный анализ зелёного покрытия городских территорий по спутниковым снимкам

---

## 1. Общее описание проекта

HowTree — веб-платформа для автоматического обнаружения и подсчёта деревьев на спутниковых снимках. Пользователь выделяет прямоугольную зону на интерактивной карте, система скачивает спутниковые тайлы, запускает детекцию методами компьютерного зрения и возвращает результат в виде геопривязанных точек на карте.

Платформа решает задачу инвентаризации городского зелёного покрова без ручного объезда территорий, что актуально для городского планирования, экологического мониторинга и оценки озеленения.

---

## 2. Архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│  Браузер (Next.js + MapLibre GL)                                 │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐   │
│  │  Карта ESRI  │   │ AnalysisPanel  │   │  Результаты      │   │
│  │  (MapLibre)  │   │ (управление)   │   │  (деревья / GeoJSON│  │
│  └──────────────┘   └────────────────┘   └──────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP REST + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│  FastAPI (Python 3.11, uvicorn)  — порт 8000                     │
│  ┌──────────────┐   ┌────────────────┐   ┌──────────────────┐   │
│  │ /analyze     │   │ /jobs (WS+REST)│   │ /trees /stats    │   │
│  └──────┬───────┘   └────────────────┘   └──────────────────┘   │
│         │ Celery dispatch                                         │
└─────────┼───────────────────────────────────────────────────────┘
          │
┌─────────▼───────────────────────────────────────────────────────┐
│  Celery Worker (Python 3.11)                                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Pipeline:                                                  │ │
│  │  1. Tile grid generation (GIS)                              │ │
│  │  2. Tile download (ESRI / Yandex / Mapbox)                  │ │
│  │  3. DeepForest inference (PyTorch ResNet50)                 │ │
│  │  4. NMS deduplication                                       │ │
│  │  5. Geo-coordinate conversion                               │ │
│  │  6. DB write (PostgreSQL + PostGIS)                         │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼───────┐  ┌───────▼───────┐  ┌──────▼──────────┐
│  PostgreSQL   │  │    Redis      │  │  ESRI / Yandex  │
│  + PostGIS    │  │  (Celery      │  │  Maps API       │
│  (хранение    │  │   брокер +    │  │  (спутниковые   │
│   деревьев,   │  │   pub/sub     │  │   тайлы)        │
│   джобов)     │  │   прогресс)   │  │                 │
└───────────────┘  └───────────────┘  └─────────────────┘
```

---

## 3. Стек технологий

### 3.1 Фронтенд

| Технология | Версия | Назначение |
|---|---|---|
| **Next.js** | 16.2 | React-фреймворк, SSR/RSC, роутинг |
| **React** | 19 | UI-компоненты |
| **MapLibre GL JS** | 5.x | Интерактивная карта, отрисовка GeoJSON-слоёв |
| **Tailwind CSS** | 3.x | Утилитарные стили |
| **Radix UI** | — | Headless UI-компоненты (кнопки, прогресс) |
| **Turf.js** | 7.x | Геопространственные вычисления на клиенте (площадь bbox) |
| **Zustand** | 5.x | Глобальный стор карты (bbox, статус джоба, слои) |
| **Lucide React** | — | Иконки |
| **TypeScript** | 5.x | Типизация |

### 3.2 Бэкенд

| Технология | Версия | Назначение |
|---|---|---|
| **Python** | 3.11 | Основной язык |
| **FastAPI** | 0.115 | REST API + WebSocket-сервер |
| **uvicorn + uvloop** | 0.32 | ASGI-сервер (высокопроизводительный event loop) |
| **SQLAlchemy** | 2.0 | ORM, async-сессии |
| **Alembic** | 1.14 | Миграции базы данных |
| **Pydantic v2** | 2.10 | Валидация схем запросов/ответов |
| **Celery** | 5.4 | Очередь задач для асинхронного ML-анализа |
| **httpx** | 0.28 | Асинхронный HTTP-клиент (скачивание тайлов) |
| **tenacity** | 9.0 | Retry-логика при скачивании тайлов |
| **structlog** | 24.4 | Структурированное JSON-логирование |

### 3.3 Компьютерное зрение и GIS

| Технология | Версия | Назначение |
|---|---|---|
| **DeepForest** | 1.4.1 | Нейросетевой детектор деревьев (основной метод) |
| **PyTorch** | 2.1.2 (CPU) | Нейросетевой бэкенд для DeepForest |
| **torchvision** | 0.16.2 | Вспомогательные операции PyTorch |
| **OpenCV** | 4.10 | Обработка изображений, HSV-маскирование |
| **scikit-image** | 0.24 | Watershed-сегментация, regionprops |
| **scipy** | — | Distance transform, gaussian filter |
| **rasterio** | 1.4 | Работа с геопространственными растрами |
| **geopandas** | 1.0 | Геопространственные датафреймы |
| **shapely** | 2.0 | Геометрические операции (bbox, полигоны) |
| **geoalchemy2** | 0.15 | PostGIS-типы в SQLAlchemy |
| **pyproj** | 3.7 | Перепроецирование координат |

### 3.4 Инфраструктура

| Технология | Версия | Назначение |
|---|---|---|
| **PostgreSQL** | 15 | Основная БД |
| **PostGIS** | 3.4 | Геопространственное расширение PostgreSQL |
| **Redis** | 7.4 | Брокер задач Celery + pub/sub для прогресса |
| **Docker** | 29 | Контейнеризация |
| **Docker Compose** | v3.9 | Оркестрация сервисов |

---

## 4. Используемые API и внешние сервисы

### 4.1 ESRI World Imagery (основной, бесплатный)

**Endpoint:**
```
https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export
  ?bbox={lon_min},{lat_min},{lon_max},{lat_max}
  &bboxSR=4326&imageSR=4326
  &size={width},{height}
  &format=png&f=image
```

- **Ключ:** не требуется
- **Ограничения:** публичный сервис, без официальной SLA
- **Применение:** скачивание спутниковых тайлов для ML-анализа, фоновая карта в браузере
- **Провайдер:** Esri / Maxar / GeoEye / Earthstar Geographics

### 4.2 ESRI Reference Labels (бесплатный)

**Endpoint:**
```
https://server.arcgisonline.com/ArcGIS/rest/services/
Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}
```

- **Ключ:** не требуется
- **Применение:** слой подписей (названия улиц, районов) поверх спутниковой карты

### 4.3 Yandex Static Maps (опциональный)

**Endpoint:**
```
https://static-maps.yandex.ru/1.x/
  ?ll={lon},{lat}&z={zoom}&l=sat
  &size={width},{height}&apikey={key}
```

- **Ключ:** требуется (регистрация на developer.yandex.ru)
- **Бесплатный лимит:** 1000 запросов/сутки
- **Применение:** альтернативный провайдер тайлов, лучшее покрытие Казахстана и СНГ
- **Конфиг:** `MAP_PROVIDER=yandex`, `YANDEX_MAPS_API_KEY=...` в `.env`

### 4.4 Mapbox Satellite (опциональный, фоллбэк)

**Endpoint:**
```
https://api.mapbox.com/styles/v1/mapbox/satellite-v9/static
  /{lon},{lat},{zoom}/{width}x{height}
  ?access_token={token}
```

- **Ключ:** требуется (mapbox.com)
- **Бесплатный лимит:** 50 000 запросов/месяц
- **Применение:** фоллбэк если Yandex недоступен
- **Конфиг:** `MAP_PROVIDER=mapbox`, `MAPBOX_TOKEN=...` в `.env`

### 4.5 MapLibre Glyph CDN (бесплатный)

```
https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf
```

- Шрифты для векторных подписей на карте

### 4.6 DeepForest pretrained model (встроенный)

- Модель скачивается автоматически при первом запуске воркера
- Хранится в `/root/.deepforest/` (volume `model_cache`)
- Источник: GitHub Releases проекта DeepForest

---

## 5. Методы детекции деревьев

### 5.1 DeepForest (основной метод)

**Принцип:** нейросетевой детектор на базе Faster R-CNN с backbone ResNet-50, обученный на датасете NEON (аэрофотосъёмка лесов Северной Америки).

**Пайплайн:**

```
Спутниковый тайл (PNG, 600×600 px, zoom=17)
       ↓
predict_tile(image_path)
       ↓
DataFrame: [xmin, ymin, xmax, ymax, score, label]
       ↓
pixel_to_geo() — конвертация пиксельных координат в WGS-84
       ↓
Detection(lon, lat, lon_min, lat_min, lon_max, lat_max, confidence)
       ↓
NMS deduplication (IoU threshold = 0.3)
       ↓
Финальный список деревьев
```

**Параметры (настраиваются в `.env`):**

| Параметр | Значение | Описание |
|---|---|---|
| `TILE_SIZE` | 600 px | Размер тайла |
| `TILE_OVERLAP` | 0.1 (10%) | Перекрытие соседних тайлов |
| `zoom` | 17 | Уровень зума (~1.2 м/пиксель) |
| `DETECTION_CONFIDENCE_THRESHOLD` | 0.4 | Минимальный score детекции |

**Производительность:** ~2–3 сек/тайл на CPU. При zoom=17, tile_size=600, overlap=0.1 средняя зона (~1 км²) обрабатывается за ~50–90 секунд.

---

### 5.2 HSV + Watershed (альтернативный метод, `tree_detector.py`)

Быстрый метод на основе цветовой сегментации — не требует GPU и обрабатывает снимок целиком за секунды.

**Пайплайн:**

```
1. BGR → HSV конвертация
2. Маска зелёного: H∈[35,90], S∈[35,255], V∈[30,190]
3. Вычитание «не-деревьев»:
   - оранжевые крыши: H∈[0,22], S≥80, V≥100
   - жёлтые дороги:   H∈[22,34], S≥80, V≥150
   - яркие блики:     V≥195
4. Морфология: MORPH_OPEN(3×3) → MORPH_CLOSE(5×5)
5. Distance Transform + gaussian_filter(σ=2.5)
6. peak_local_max(min_distance=10) → центры крон
7. watershed() → сегменты
8. Фильтр по площади: 50–2500 пикс²
9. Bounding boxes + статистика
```

**Преимущества:** мгновенная обработка (< 1 сек на снимок 1024×1024), не нужен PyTorch.

**Ограничения:** чувствителен к освещению и сезону, не различает деревья от кустарников, работает хуже на снимках с низким контрастом.

**Использование:**
```python
# Скачать тайл с карты и обработать
python tree_detector.py
# Результаты: result_boxes.jpg, result_centers.jpg, stats.txt
```

---

### 5.3 NMS (Non-Maximum Suppression)

После тайловой детекции соседние тайлы перекрываются → одно дерево может быть обнаружено дважды. NMS объединяет перекрывающиеся bbox по IoU:

```python
nms(detections, iou_threshold=0.3)
# IoU > 0.3 → детекция с меньшим score удаляется
```

---

## 6. База данных

### 6.1 Схема

**Таблица `analysis_jobs`** — задачи анализа:

| Поле | Тип | Описание |
|---|---|---|
| id | UUID | Первичный ключ |
| status | VARCHAR(50) | queued / downloading_tiles / running_detection / completed / failed |
| progress | INTEGER | Прогресс 0–100% |
| stage | VARCHAR(100) | Текущий этап (для UI) |
| bbox | GEOMETRY(POLYGON, 4326) | Зона анализа в WGS-84 |
| zoom | INTEGER | Уровень зума тайлов |
| map_provider | VARCHAR(50) | esri / yandex / mapbox |
| tree_count | INTEGER | Итого деревьев |
| canopy_area_m2 | FLOAT | Суммарная площадь крон, м² |
| avg_confidence | FLOAT | Средняя уверенность модели |
| created_at | TIMESTAMPTZ | Время создания |
| started_at | TIMESTAMPTZ | Время начала обработки |
| completed_at | TIMESTAMPTZ | Время завершения |
| error_message | TEXT | Текст ошибки если failed |

**Таблица `trees`** — обнаруженные деревья:

| Поле | Тип | Описание |
|---|---|---|
| id | UUID | Первичный ключ |
| location | GEOMETRY(POINT, 4326) | Центр кроны (lon, lat) |
| bbox | GEOMETRY(POLYGON, 4326) | Bounding box кроны |
| confidence | FLOAT | Score детекции [0, 1] |
| canopy_area_m2 | FLOAT | Площадь кроны, м² |
| analysis_id | UUID (FK) | Ссылка на analysis_jobs |
| detected_at | TIMESTAMPTZ | Время детекции |

**Таблица `districts`** — административные районы:

| Поле | Тип | Описание |
|---|---|---|
| id | UUID | Первичный ключ |
| name | VARCHAR(255) | Название района |
| city | VARCHAR(255) | Город |
| code | VARCHAR(50) | Код района |
| geometry | GEOMETRY(MULTIPOLYGON, 4326) | Граница района |

**Индексы:**
- `ix_trees_location_gist` — GIST по `location` (пространственные запросы)
- `ix_trees_bbox_gist` — GIST по `bbox`
- `ix_trees_analysis_confidence` — B-tree по `(analysis_id, confidence)`

### 6.2 PostGIS-запросы

Деревья в bbox (API `/trees/geojson`):
```sql
SELECT * FROM trees
WHERE ST_Intersects(location, ST_MakeEnvelope(lon1, lat1, lon2, lat2, 4326))
  AND confidence >= 0.4
  AND analysis_id = ANY(...)
```

---

## 7. REST API

**Base URL:** `http://localhost:8000/api/v1`

| Метод | Путь | Описание |
|---|---|---|
| POST | `/analyze` | Создать задачу анализа по bbox |
| POST | `/analyze/upload` | Анализ загруженного изображения |
| GET | `/jobs/{id}` | Статус и результат задачи |
| GET | `/jobs` | Список задач (с фильтром по статусу) |
| WS | `/jobs/ws/{id}` | WebSocket прогресс в реальном времени |
| GET | `/trees/geojson` | GeoJSON деревьев в bbox |
| GET | `/stats/bbox` | Статистика по bbox |
| GET | `/stats/{district}` | Статистика по району |
| GET | `/health` | Healthcheck |

### WebSocket-протокол прогресса

Клиент подключается к `/jobs/ws/{job_id}`. Сервер транслирует JSON-сообщения из Redis pub/sub:

```json
{
  "job_id": "bb43801d-...",
  "status": "running_detection",
  "progress": 67,
  "message": "Running inference on tile 14/21"
}
```

Соединение закрывается когда `status` = `"completed"` или `"failed"`.

**Фоллбэк:** если WebSocket закрывается раньше завершения (тайм-аут, сеть), фронтенд автоматически переключается на HTTP-polling каждые 3 секунды.

---

## 8. Очередь задач

Тяжёлые ML-задачи выполняются асинхронно через Celery:

```
FastAPI → celery_app.send_task() → Redis queue "analysis"
                                          ↓
                                   Celery Worker
                                          ↓
                          publish_progress() → Redis pub/sub
                                          ↓
                               WebSocket Manager
                                          ↓
                                      Браузер
```

**Конфигурация:**
- Брокер: Redis `redis://redis:6379/0`
- Backend результатов: Redis `redis://redis:6379/1`
- Concurrency: 1 воркер (CPU-bound задача, параллелизм не нужен)
- Очередь: `analysis` (именованная, для возможного масштабирования)
- Прогресс: синхронный `publish_progress()` → Redis channel `job_progress:{job_id}`

---

## 9. Производительность

### До оптимизации (исходные параметры)
| Параметр | Значение |
|---|---|
| zoom | 18 |
| TILE_SIZE | 400 px |
| TILE_OVERLAP | 0.2 |
| Тайлов для 1 км² | ~234 |
| Время анализа 1 км² | ~10 минут |

### После оптимизации (текущие параметры)
| Параметр | Значение |
|---|---|
| zoom | 17 |
| TILE_SIZE | 600 px |
| TILE_OVERLAP | 0.1 |
| Тайлов для 1 км² | ~21 |
| Время анализа 1 км² | ~50–90 секунд |
| Ускорение | **~11×** |

Zoom=17 даёт разрешение ~1.2 м/пиксель — достаточно для детекции крон от ~2 метров диаметром.

---

## 10. Структура проекта

```
howTree/
├── app/                        # Next.js приложение
│   └── dashboard/page.tsx      # Основная страница
├── components/
│   ├── map/MapContainer.tsx    # MapLibre карта + bbox selection
│   └── panels/AnalysisPanel.tsx# Панель запуска анализа
├── lib/
│   ├── api/client.ts           # API-клиент
│   └── store/mapStore.ts       # Zustand стор
├── types/index.ts              # TypeScript типы
├── tree_detector.py            # Standalone HSV+Watershed детектор
│
└── backend/
    ├── app/
    │   ├── api/routes/         # FastAPI роуты
    │   ├── core/               # Конфиг, БД, WebSocket, логирование
    │   ├── models/             # SQLAlchemy модели
    │   ├── modules/
    │   │   ├── detection/      # Детектор, тайлер, пайплайн, дедупликация
    │   │   ├── gis/            # Coordinate transform, tile grid
    │   │   ├── jobs/           # Celery-задачи
    │   │   └── analytics/      # Статистика по районам
    │   ├── schemas/            # Pydantic схемы
    │   └── services/           # Бизнес-логика (JobService, TreeService)
    ├── migrations/             # Alembic миграции
    ├── worker.py               # Celery worker entrypoint
    ├── Dockerfile              # Multi-stage: api + worker
    ├── docker-compose.yml      # postgres + redis + api + worker
    └── .env                    # Конфигурация
```

---

## 11. Запуск проекта

### Предварительные требования
- Docker Desktop
- Node.js 20+

### Команды
```bash
# 1. Поднять инфраструктуру (PostgreSQL, Redis, API, Worker)
cd backend
docker compose up -d

# 2. Запустить фронтенд
cd ..
npm install
npm run dev

# 3. Открыть браузер
open http://localhost:3000
```

### Конфигурация (backend/.env)
```env
MAP_PROVIDER=esri        # esri (без ключа) | yandex | mapbox
YANDEX_MAPS_API_KEY=...  # если MAP_PROVIDER=yandex
MAPBOX_TOKEN=...         # если MAP_PROVIDER=mapbox
TILE_SIZE=600
TILE_OVERLAP=0.1
DETECTION_CONFIDENCE_THRESHOLD=0.4
```

---

## 12. Известные ограничения

1. **Скорость на CPU**: DeepForest работает на CPU (~2–3 сек/тайл). На GPU ускорение в 10–20×.
2. **Сезонность**: модель обучена на летних снимках, качество падает зимой.
3. **Покрытие обучающего датасета**: DeepForest обучен преимущественно на лесах Северной Америки. Для городских деревьев Казахстана точность ниже, чем на природных массивах.
4. **Один воркер**: `CELERY_CONCURRENCY=1` — задачи выполняются последовательно. При нескольких одновременных пользователях — очередь.
5. **Лимит bbox**: максимальная зона анализа — 50 км² (`max_bbox_area_km2` в конфиге).
