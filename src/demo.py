"""Demo mode: generates realistic pipeline output without LLM API calls.

Uses hardcoded but realistic analysis results to demonstrate
the full pipeline output format, validation, and quality layer.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .config import Config
from .data_extractor import get_project_id
from .output_generator import save_excel, save_json
from .quality_layer import run_quality_check
from .validators import (
    validate_brief_opportunities,
    validate_calendar_events,
)

logger = logging.getLogger(__name__)

# Realistic demo data per project
DEMO_CALENDAR: dict[str, list[dict]] = {
    "PROJ-2025-001": [
        {
            "date": "2025-09-20",
            "title": "Старт открытых мастер-классов ведущих театральных режиссёров",
            "event_type": "запуск",
            "pr_score": 7,
            "why_it_matters": "Мастер-классы с лауреатами «Золотой маски» открыты для всех — повод для региональных СМИ и театрального сообщества",
            "how_to_strengthen": "Организовать прямую трансляцию первого мастер-класса, пригласить местные телеканалы",
            "pr_format": "выезд на место / соцсети / локальные медиа",
        },
        {
            "date": "2025-11-15",
            "title": "Фестиваль-показ «Голоса Урала» — 8 новых спектаклей за 3 дня",
            "event_type": "фестиваль",
            "pr_score": 9,
            "why_it_matters": "Масштабный театральный фестиваль с 2000 зрителей, новые спектакли по документальным историям уральцев — сильный федеральный инфоповод",
            "how_to_strengthen": "Пригласить федеральных театральных критиков, организовать пресс-показ накануне",
            "pr_format": "выезд на место / федеральные СМИ / соцсети",
        },
        {
            "date": "2025-12-20",
            "title": "Выход сборника пьес участников лаборатории",
            "event_type": "выпуск продукта",
            "pr_score": 5,
            "why_it_matters": "Публикация сборника новых пьес — результат проекта, интересный театральному сообществу",
            "how_to_strengthen": "Провести презентацию в книжном магазине, пригласить авторов для автограф-сессии",
            "pr_format": "соцсети / локальные медиа",
        },
        {
            "date": "2025-07-01",
            "title": "Формирование экспертного совета проекта",
            "event_type": "внутренний",
            "pr_score": 2,
            "why_it_matters": "Отбор участников и внутреннее совещание по подготовке проекта",
            "how_to_strengthen": None,
            "pr_format": "внутренний процесс",
        },
    ],
    "PROJ-2025-002": [
        {
            "date": "2025-06-20",
            "title": "Старт волонтёрского лагеря на берегу Байкала",
            "event_type": "запуск",
            "pr_score": 8,
            "why_it_matters": "200 волонтёров строят экотропу на берегу Байкала — визуально сильный сюжет с экологической повесткой, интересный федеральным СМИ",
            "how_to_strengthen": "Пригласить экологических блогеров и региональное ТВ на открытие лагеря",
            "pr_format": "выезд на место / соцсети / федеральные СМИ",
        },
        {
            "date": "2025-08-23",
            "title": "Торжественное открытие экотропы «Байкальский меридиан»",
            "event_type": "открытие",
            "pr_score": 9,
            "why_it_matters": "Открытие 12-километровой экотропы с 3 смотровыми площадками при участии властей, экологов и жителей — главный инфоповод проекта",
            "how_to_strengthen": "Организовать первую экскурсию для СМИ, подготовить дрон-съёмку маршрута",
            "pr_format": "выезд на место / федеральные СМИ / соцсети",
        },
        {
            "date": "2025-09-15",
            "title": "Акция «Чистый берег Байкала» с участием жителей трёх посёлков",
            "event_type": "акция",
            "pr_score": 7,
            "why_it_matters": "Масштабная волонтёрская акция с экологической повесткой — привязка к теме защиты Байкала, визуально сильный контент",
            "how_to_strengthen": "Привлечь региональных экоблогеров, сделать челлендж в соцсетях",
            "pr_format": "соцсети / локальные медиа / выезд на место",
        },
        {
            "date": "2025-10-15",
            "title": "Запуск мобильного приложения-путеводителя по тропе",
            "event_type": "запуск",
            "pr_score": 6,
            "why_it_matters": "Технологичный продукт с AR-элементами для экотуризма — интересен IT- и travel-медиа",
            "how_to_strengthen": "Провести онлайн-презентацию, предложить обзор tech-блогерам",
            "pr_format": "удалённая работа / соцсети / специализированные медиа",
        },
        {
            "date": "2025-06-01",
            "title": "Закупка строительных материалов и навигационных элементов",
            "event_type": "закупка",
            "pr_score": 1,
            "why_it_matters": "Техническая закупка материалов без внешней ценности",
            "how_to_strengthen": None,
            "pr_format": "внутренний процесс",
        },
    ],
    "PROJ-2025-003": [
        {
            "date": "2025-08-20",
            "title": "Запуск горячей линии цифровой поддержки для пожилых",
            "event_type": "запуск",
            "pr_score": 7,
            "why_it_matters": "Бесплатная горячая линия для помощи пожилым с цифровыми вопросами — социально значимая тема, интересная широкой аудитории",
            "how_to_strengthen": "Подготовить короткий ролик с демонстрацией звонка, распространить через соцсети и местные СМИ",
            "pr_format": "удалённая работа / соцсети / локальные медиа",
        },
        {
            "date": "2025-10-01",
            "title": "Старт выездных занятий в сёлах Нижегородской области",
            "event_type": "запуск",
            "pr_score": 7,
            "why_it_matters": "Мобильные группы волонтёров едут учить пожилых людей в сёлах — визуально тёплая история, привязка к теме цифрового неравенства",
            "how_to_strengthen": "Снять репортаж с первого выезда, показать контраст «до и после»",
            "pr_format": "выезд на место / соцсети / локальные медиа",
        },
        {
            "date": "2025-12-05",
            "title": "Фестиваль «Онлайн без границ» — торжественный выпускной",
            "event_type": "фестиваль",
            "pr_score": 8,
            "why_it_matters": "600 выпускников получают сертификаты, конкурс «Лучший цифровой дедушка/бабушка» — эмоциональный инфоповод с мощным визуалом",
            "how_to_strengthen": "Пригласить регионального чиновника для вручения сертификатов, организовать стрим в соцсетях",
            "pr_format": "выезд на место / соцсети / локальные медиа / федеральные СМИ",
        },
        {
            "date": "2025-07-15",
            "title": "Набор и обучение волонтёров-наставников",
            "event_type": "набор",
            "pr_score": 4,
            "why_it_matters": "Набор студентов-волонтёров для обучения пожилых людей — подготовительный этап",
            "how_to_strengthen": "Разместить объявление в вузах и соцсетях",
            "pr_format": "соцсети",
        },
        {
            "date": "2025-12-15",
            "title": "Мониторинг результатов и подготовка отчётности",
            "event_type": "отчётность",
            "pr_score": 1,
            "why_it_matters": "Внутренний мониторинг и отчётность по проекту",
            "how_to_strengthen": None,
            "pr_format": "внутренний процесс",
        },
    ],
}

DEMO_BRIEF: dict[str, list[dict]] = {
    "PROJ-2025-001": [
        {
            "title": "История молодого режиссёра из малого уральского города",
            "category": "человеческая история",
            "media_potential": "Режиссёр из города с населением 30 тыс. человек получил шанс поставить спектакль на главной сцене Екатеринбурга — история преодоления и таланта",
            "timing": "Ноябрь 2025 — накануне фестиваля",
            "effort_level": "low",
            "media_formats": "интервью, короткое видео, соцсети",
            "recommendation": "Выбрать 2-3 участника с яркими биографиями, снять короткие видеопортреты заранее и выпустить серией перед фестивалем",
        },
        {
            "title": "Документальные истории Урала на сцене — жители узнают себя",
            "category": "тематический тренд",
            "media_potential": "Спектакли создаются на основе реальных историй жителей Урала — документальный театр в тренде, зрители узнают в героях себя и своих соседей",
            "timing": "Сентябрь–октябрь 2025, в период лабораторных сессий",
            "effort_level": "medium",
            "media_formats": "репортаж, кейс, соцсети",
            "recommendation": "Организовать встречу героев реальных историй с режиссёрами — снять процесс сбора историй как отдельный сюжет",
        },
        {
            "title": "Партнёрство с лауреатом «Золотой маски»",
            "category": "партнёрство",
            "media_potential": "Известный режиссёр-лауреат работает с молодыми авторами на Урале — звёздное имя привлекает федеральное внимание",
            "timing": "Сентябрь 2025 — начало мастер-классов",
            "effort_level": "low",
            "media_formats": "интервью, новость, соцсети",
            "recommendation": "Взять комментарий у художественного руководителя о проекте, предложить эксклюзивное интервью профильным изданиям",
        },
        {
            "title": "День театра (27 марта) как медиапривязка для анонса",
            "category": "сезонный инфоповод",
            "media_potential": "Международный день театра — идеальное окно для анонса набора в лабораторию и рассказа о проекте",
            "timing": "Март 2026 (если проект получит продолжение) или использовать ближайший День театра для анонса итогов",
            "effort_level": "low",
            "media_formats": "новость, соцсети",
            "recommendation": "Подготовить пресс-релиз к 27 марта с анонсом проекта или итогами фестиваля",
        },
    ],
    "PROJ-2025-002": [
        {
            "title": "Эколог 15 лет защищает Байкал — теперь строит тропу для всех",
            "category": "человеческая история",
            "media_potential": "Руководитель проекта — эколог с 15-летним стажем работы на Байкале. Его личная история даёт лицо проекту и эмоциональную привязку",
            "timing": "Июнь 2025 — перед стартом строительства",
            "effort_level": "low",
            "media_formats": "интервью, видеопортрет, соцсети",
            "recommendation": "Снять видеоинтервью на берегу Байкала, предложить экологическим и региональным изданиям",
        },
        {
            "title": "Визуально мощный контент: виды Байкала с 3 смотровых площадок",
            "category": "визуальный формат",
            "media_potential": "Смотровые площадки на западном берегу Байкала — дрон-съёмка даст сильнейший визуальный контент для соцсетей и медиа",
            "timing": "Август 2025 — после установки площадок",
            "effort_level": "medium",
            "media_formats": "короткое видео, фоторепортаж, соцсети",
            "recommendation": "Заказать профессиональную дрон-съёмку тропы и площадок, смонтировать ролик для соцсетей и пресс-кита",
        },
        {
            "title": "Мобильное приложение с AR — экотуризм нового формата",
            "category": "результат проекта",
            "media_potential": "AR-путеводитель по экотропе — пересечение экологии и технологий, интересно IT-медиа и travel-блогерам",
            "timing": "Октябрь 2025 — после запуска приложения",
            "effort_level": "low",
            "media_formats": "обзор, новость, соцсети",
            "recommendation": "Предложить обзор tech-блогерам и travel-изданиям, подготовить демо-ролик",
        },
        {
            "title": "Сотрудничество с заповедником «Заповедное Прибайкалье»",
            "category": "партнёрство",
            "media_potential": "Проект получил поддержку федерального заповедника — статусное партнёрство, добавляющее экспертный вес",
            "timing": "Апрель–май 2025, при старте проекта",
            "effort_level": "low",
            "media_formats": "новость, пресс-релиз",
            "recommendation": "Включить цитату представителя заповедника во все пресс-материалы",
        },
        {
            "title": "Школьники проводят экологические квесты на тропе",
            "category": "визуальный формат",
            "media_potential": "500 школьников проходят экоквесты на Байкале — эмоциональный контент с детьми на природе, тема экопросвещения",
            "timing": "Сентябрь–октябрь 2025 — начало учебного года",
            "effort_level": "medium",
            "media_formats": "репортаж, соцсети, короткое видео",
            "recommendation": "Снять серию коротких видео с реакциями школьников, привлечь образовательные медиа",
        },
    ],
    "PROJ-2025-003": [
        {
            "title": "Формат «Внук учит деда» — тёплая межпоколенческая история",
            "category": "человеческая история",
            "media_potential": "Молодые волонтёры обучают пожилых людей — эмоциональная межпоколенческая история, идеальная для соцсетей и ТВ-сюжетов",
            "timing": "Сентябрь–октябрь 2025, в разгар обучения",
            "effort_level": "low",
            "media_formats": "репортаж, короткое видео, соцсети",
            "recommendation": "Снять серию коротких роликов «Внук учит деда»: конкретные пары волонтёр-ученик, реальные эмоции и прогресс",
        },
        {
            "title": "День пожилого человека (1 октября) — медийное окно",
            "category": "сезонный инфоповод",
            "media_potential": "1 октября — готовая привязка для рассказа о проекте. СМИ ищут позитивные истории о пожилых людях — проект даёт идеальный контент",
            "timing": "1 октября 2025",
            "effort_level": "low",
            "media_formats": "новость, интервью, соцсети",
            "recommendation": "Подготовить пресс-релиз и 2-3 готовые истории участников к 1 октября, разослать в региональные и федеральные СМИ",
        },
        {
            "title": "Цифровое неравенство в сёлах — острая социальная тема",
            "category": "тематический тренд",
            "media_potential": "Выездные занятия в 10 сёлах Нижегородской области поднимают тему цифрового неравенства — актуальная социальная проблема, интересная федеральным СМИ",
            "timing": "Октябрь–ноябрь 2025, во время выездных сессий",
            "effort_level": "medium",
            "media_formats": "репортаж, кейс, интервью",
            "recommendation": "Организовать выезд журналиста в одно из сёл для создания полноценного репортажа «до и после»",
        },
        {
            "title": "Партнёрство с МТС — бизнес помогает старшему поколению",
            "category": "партнёрство",
            "media_potential": "Крупная телеком-компания предоставляет планшеты для обучения пожилых — пример корпоративной социальной ответственности",
            "timing": "Август 2025 — при запуске обучения",
            "effort_level": "low",
            "media_formats": "новость, пресс-релиз, соцсети",
            "recommendation": "Выпустить совместный пресс-релиз с МТС, организовать фотосессию передачи планшетов",
        },
        {
            "title": "Конкурс «Лучший цифровой дедушка/бабушка» — вирусный потенциал",
            "category": "результат проекта",
            "media_potential": "Конкурс среди выпускников — лёгкий, эмоциональный формат с вирусным потенциалом для соцсетей",
            "timing": "Декабрь 2025 — на выпускном фестивале",
            "effort_level": "low",
            "media_formats": "короткое видео, соцсети, новость",
            "recommendation": "Снять процесс конкурса на видео, подготовить нарезку для соцсетей, предложить ТВ-каналам эмоциональный сюжет",
        },
    ],
}


def run_demo_pipeline(
    applications: list[dict], config: Config
) -> None:
    """Run the full pipeline in demo mode with pre-generated data."""
    all_results = []
    all_calendar: list[dict] = []
    all_brief: list[dict] = []

    for app in applications:
        project_id = get_project_id(app)
        project_name = app.get("project_name", project_id)

        # Get demo data for this project (fallback to first project's data)
        raw_cal = DEMO_CALENDAR.get(project_id, list(DEMO_CALENDAR.values())[0])
        raw_brief = DEMO_BRIEF.get(project_id, list(DEMO_BRIEF.values())[0])

        # Validate
        valid_cal, invalid_cal = validate_calendar_events(raw_cal)
        valid_brief, invalid_brief = validate_brief_opportunities(raw_brief)

        # Quality check
        assessed_cal, assessed_brief = run_quality_check(valid_cal, valid_brief, config)

        for rec in assessed_cal:
            rec["project_id"] = project_id
        for rec in assessed_brief:
            rec["project_id"] = project_id

        all_calendar.extend(assessed_cal)
        all_brief.extend(assessed_brief)

        all_results.append({
            "project_id": project_id,
            "project_name": project_name,
            "status": "success",
            "error": None,
            "calendar_events": assessed_cal,
            "brief_opportunities": assessed_brief,
            "validation_errors": (
                [{"type": "calendar", **e} for e in invalid_cal]
                + [{"type": "brief", **e} for e in invalid_brief]
            ),
        })

        cal_acc = sum(1 for r in assessed_cal if r["quality_status"] == "accepted")
        cal_rej = sum(1 for r in assessed_cal if r["quality_status"] == "rejected")
        logger.info(
            "%s: %d cal events (%d accepted, %d rejected), %d brief opps",
            project_id, len(assessed_cal), cal_acc, cal_rej, len(assessed_brief),
        )

    # Summary
    cal_accepted = [r for r in all_calendar if r["quality_status"] == "accepted"]
    cal_review = [r for r in all_calendar if r["quality_status"] == "review"]
    cal_rejected = [r for r in all_calendar if r["quality_status"] == "rejected"]

    logger.info("=" * 60)
    logger.info("Demo pipeline complete:")
    logger.info("  Applications: %d", len(all_results))
    logger.info("  Calendar: %d total, %d accepted, %d review, %d rejected",
                len(all_calendar), len(cal_accepted), len(cal_review), len(cal_rejected))
    logger.info("  Brief opportunities: %d", len(all_brief))

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_data = {
        "summary": {
            "total_applications": len(applications),
            "processed": len(all_results),
            "errors": 0,
            "calendar_events_total": len(all_calendar),
            "calendar_accepted": len(cal_accepted),
            "calendar_review": len(cal_review),
            "calendar_rejected": len(cal_rejected),
            "brief_opportunities_total": len(all_brief),
        },
        "calendar": all_calendar,
        "brief": all_brief,
        "per_project": all_results,
        "errors": [],
    }

    json_path = str(output_dir / "results.json")
    save_json(output_data, json_path)
    logger.info("JSON saved to %s", json_path)

    excel_path = str(output_dir / "results.xlsx")
    save_excel(all_calendar, all_brief, excel_path)
    logger.info("Excel saved to %s", excel_path)
