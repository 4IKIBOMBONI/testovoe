# Инструкция по запуску и проверке решения

Python-пайплайн для анализа заявок Фонда президентских грантов через LLM API. На выходе — PR-календарь внешних инфоповодов и стратегический PR-бриф со скрытым медиапотенциалом. Итог: **JSON** + **Excel** с двумя листами.

---

## 1. Что нужно установить

- **Python 3.10+** — проверь командой `python3 --version`
- **Git** — проверь командой `git --version`
- Доступ в интернет (для скачивания зависимостей и вызовов LLM API)

Если Python не установлен — поставь с [python.org](https://www.python.org/downloads/) или через Homebrew на macOS: `brew install python`.

---

## 2. Скачать проект

```bash
git clone <URL_РЕПОЗИТОРИЯ>
cd testovoe
git checkout claude/llm-grant-analysis-Ol289
```

> Замени `<URL_РЕПОЗИТОРИЯ>` на URL этого репозитория.

---

## 3. Установить зависимости

```bash
python3 -m pip install -r requirements.txt
```

Ставятся три пакета: `anthropic`, `pydantic`, `openpyxl`.

---

## 4. Решить проблему с SSL на macOS (если применимо)

На свежем Python на macOS HTTPS-запросы могут падать с ошибкой `CERTIFICATE_VERIFY_FAILED`. Если это случится — открой Finder → `Программы` → папка `Python 3.x` → двойной клик по **`Install Certificates.command`**. Один раз настроил — забыл.

---

## 5. Получить API-ключ Yandex GPT

1. Зайди в [Yandex Cloud Console](https://console.yandex.cloud/).
2. Перейди в **AI Studio** (в левом меню).
3. Справа сверху — **«Создать API-ключ»**.
4. Выбери сервисный аккаунт (создай новый, если его нет; роль `ai.languageModels.user`).
5. Скопируй **секретный ключ** (показывается один раз, вида `AQVN...`).
6. Также понадобится **folder_id** — ID каталога, в котором ты работаешь. Его можно взять:
   - из URL консоли: `https://console.yandex.cloud/folders/<ТУТ_folder_id>/...`
   - или из сообщения об ошибке API — оно содержит правильный ID сервисного аккаунта.

---

## 6. Задать переменные окружения

В том же окне терминала, из которого будешь запускать скрипт:

```bash
export YANDEX_API_KEY="AQVN..."                      # твой ключ
export YANDEX_FOLDER_ID="b1..."                       # twой folder_id
```

Проверить, что записалось:

```bash
echo $YANDEX_API_KEY
echo $YANDEX_FOLDER_ID
```

Обе команды должны вывести значения (не пусто).

> ⚠️ При закрытии терминала или открытии новой вкладки переменные сбрасываются — нужно будет задать заново.

---

## 7. Запустить пайплайн

```bash
python3 main.py --provider yandex --input data/sample_applications.json --output output
```

### Альтернативные сценарии

**С Anthropic Claude вместо Yandex:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python3 main.py --provider anthropic --input data/sample_applications.json --output output
```

**Демо-режим без API-ключа (генерирует тестовый вывод):**
```bash
python3 main.py --demo
```

**Со своим файлом заявок:**
```bash
python3 main.py --provider yandex --input путь/к/вашему/файлу.json --output output
```

---

## 8. Ожидаемый вывод в терминале

Примерно такое:
```
Loading applications from data/sample_applications.json
Loaded 3 application(s)
============================================================
Processing 1/3: PROJ-2025-001
Processing application: PROJ-2025-001
Extracted context for PROJ-2025-001 (2902 chars)
Yandex GPT call attempt 1/3
Yandex GPT response received (1943 chars)
PROJ-2025-001: 4 calendar events (3 accepted, 0 review, 1 rejected)
Yandex GPT call attempt 1/3
Yandex GPT response received (2435 chars)
PROJ-2025-001: 4 brief opportunities (4 accepted, 0 review)
============================================================
Processing 2/3: PROJ-2025-002
...
Pipeline complete:
  Applications processed: 3
  Calendar events: 14
  Brief opportunities: 14
  Errors: 0
  Calendar breakdown: 10 accepted, 0 review, 4 rejected
JSON saved to output/results.json
Excel saved to output/results.xlsx
```

Обработка занимает **~40–60 секунд** на 3 заявки.

---

## 9. Что проверять в результатах

### Файлы

```bash
ls -la output/
```

Должны появиться:
- `results.json` — машиночитаемый результат
- `results.xlsx` — Excel-таблицы

### Excel (`results.xlsx`)

Открой через Finder двойным кликом или командой:
```bash
open output/results.xlsx
```

В файле **два листа**:

1. **PR-календарь** — внешние инфоповоды
   - Колонки: Проект, Дата, Название, Тип, PR Score, Почему это инфоповод, Как усилить, Формат PR, Статус обработки, Комментарий QC
   - Статусы подсвечены: 🟢 accepted, 🟡 review, 🔴 rejected

2. **Стратегический PR-бриф** — скрытый медиапотенциал
   - Колонки: Проект, Название, Категория, Описание медиапотенциала, Тайминг, Уровень усилий, Форматы, Рекомендация, Статус, Комментарий QC

### JSON (`results.json`)

Структура:
```json
{
  "summary": {
    "total_applications": 3,
    "processed": 3,
    "errors": 0,
    "calendar_events_total": 14,
    "calendar_accepted": 10,
    "calendar_review": 0,
    "calendar_rejected": 4,
    "brief_opportunities_total": 14
  },
  "calendar": [...],       // все события PR-календаря
  "brief": [...],          // все возможности PR-брифа
  "per_project": [...],    // детализация по каждой заявке
  "errors": []             // ошибки обработки
}
```

---

## 10. Что должно быть в результате (критерии проверки)

- ✅ Пайплайн отработал **без ошибок** (`errors: 0` в summary)
- ✅ Обработаны **все заявки** из входного файла
- ✅ В PR-календаре есть **публичные события**: фестивали, открытия, запуски, акции
- ✅ В PR-календаре **отклонены внутренние процессы**: планёрки, закупки, отчётность, сбор команды (это значит quality layer реально фильтрует)
- ✅ В PR-брифе есть **разнообразные категории**: человеческие истории, сезонные привязки, партнёрства, визуальные форматы
- ✅ У каждой записи есть `quality_status` (accepted/review/rejected) и `quality_comment`
- ✅ Excel открывается, цветные статусы видны, заголовки закреплены

---

## 11. Структура проекта

```
testovoe/
├── main.py                         # точка входа
├── requirements.txt                # зависимости
├── README.md                       # краткое описание
├── INSTRUCTIONS.md                 # этот файл
├── data/
│   └── sample_applications.json    # тестовые заявки
├── output/                         # сюда сохраняются results.json и results.xlsx
└── src/
    ├── config.py                   # конфигурация (env-переменные, пороги)
    ├── data_extractor.py           # JSON заявки → структурированный текст для LLM
    ├── prompts.py                  # промпты для PR-календаря и брифа
    ├── llm_client.py               # Anthropic Claude клиент
    ├── yandex_client.py            # Yandex GPT клиент
    ├── llm_factory.py              # фабрика провайдеров
    ├── json_parser.py              # безопасное извлечение JSON из ответов LLM
    ├── validators.py               # Pydantic-валидаторы
    ├── quality_layer.py            # проверка качества и фильтрация
    ├── output_generator.py         # генерация JSON + Excel
    ├── pipeline.py                 # оркестрация одной заявки
    └── demo.py                     # демо-режим без API
```

---

## 12. Как устроено решение (коротко)

1. **Загрузка**: читается JSON-файл с заявками (массив или одна заявка).
2. **Извлечение контекста**: из каждой заявки аккуратно вытягиваются значимые блоки (описание, календарный план, целевые группы, ожидаемые результаты, команда, партнёры, бюджет) и собираются в структурированный текст для LLM.
3. **Два вызова LLM на заявку**:
   - промпт для **PR-календаря** с чёткими правилами включения/исключения;
   - промпт для **стратегического PR-брифа** с поиском скрытого медиапотенциала.
4. **Безопасное извлечение JSON**: парсер обрабатывает 4 варианта ответа модели — чистый JSON, markdown-обёртку, текст вокруг JSON, trailing commas.
5. **Валидация через Pydantic**: проверка обязательных полей, типов, диапазонов (`pr_score` 1–10, `effort_level` в low/medium/high).
6. **Quality Layer**:
   - фильтр по PR Score (порог 5) — слабые инфоповоды отклоняются;
   - детектор внутренних процессов (планёрки, закупки, отчётность);
   - детектор расплывчатых формулировок;
   - маркировка статусом `accepted` / `review` / `rejected`.
7. **Устойчивость**: ошибка одной заявки не останавливает обработку остальных; retry LLM-вызовов с экспоненциальной задержкой (2s → 4s → 8s).
8. **Вывод**: JSON-файл + Excel с двумя листами и цветной подсветкой статусов.

---

## 13. Если что-то не работает

| Симптом | Причина | Решение |
|---|---|---|
| `command not found: python` | На macOS нет alias | Используй `python3` вместо `python` |
| `ModuleNotFoundError: No module named 'anthropic'` | Не установлены зависимости | `python3 -m pip install -r requirements.txt` |
| `CERTIFICATE_VERIFY_FAILED` | Python на macOS без сертификатов | Запусти `Install Certificates.command` (см. шаг 4) |
| `YANDEX_API_KEY not set` | Переменная окружения не задана | `export YANDEX_API_KEY="..."` в том же терминале |
| `Specified folder ID '...' does not match...` | Неверный folder_id | Возьми правильный ID из ошибки или URL консоли Yandex |
| `HTTP 401 Unauthorized` | Неверный или удалённый API-ключ | Создай новый ключ в Yandex Cloud AI Studio |
| `HTTP 403 Forbidden` | У сервисного аккаунта нет нужной роли | Добавь роль `ai.languageModels.user` |
| Скрипт висит долго на одной заявке | Проблема с сетью/таймаутом, идут retry | Дождись (до 3 попыток) или проверь интернет |

---

## 14. Контакты

Если остались вопросы — пиши.
