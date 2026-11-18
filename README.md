# prac2 - визуализация графа зависимостей (Вариант 6)

CLI-инструмент для анализа и визуализации графа зависимостей пакетов
Python (pip) без менеджеров пакетов и сторонних библиотек.

## Структура проекта

```text
prac2/
├── src/
│   └── dep_graph.py        # исходный код
├── tests/
│   ├── data/
│   │   ├── test_repo.txt   # тестовый репозиторий (A..F)
│   │   └── test_cycle.txt  # тестовый репозиторий с циклами
│   └── test_dep_graph.py   # модульные тесты (unittest)
├── run.bat                 # скрипт запуска (Windows)
├── run.sh                  # скрипт запуска (Linux/macOS)
├── README.md
└── .gitignore
```

## Параметры командной строки

| Параметр | Описание |
| --- | --- |
| `--package` | имя анализируемого пакета (обязательный) |
| `--repo` | URL репозитория или путь к файлу тестового репозитория |
| `--mode` | режим работы: `real` (по умолчанию) или `test` |
| `--version` | версия пакета (по умолчанию `latest`) |
| `--max-depth` | максимальная глубина анализа, >= 1 (по умолчанию 3) |
| `--filter` | подстрока для исключения пакетов |
| `--reverse` | вывести обратные зависимости |
| `--d2` | вывести граф на языке диаграмм D2 |

## Запуск

```bash
run.bat --package requests --repo https://pypi.org --version 2.31.0
./run.sh --package requests --repo https://pypi.org --version 2.31.0
```

## Тесты

```bash
run.bat test
./run.sh test
```

## Примеры по этапам

```bash
# Этап 1: обработка ошибок
run.bat --package "bad name!" --repo not_url --version abc --max-depth 0

# Этап 2: прямые зависимости
run.bat --package requests --repo https://pypi.org --version 2.31.0 --max-depth 1

# Этап 3: граф, глубина, фильтр, циклы
run.bat --package A --repo tests/data/test_repo.txt --mode test
run.bat --package A --repo tests/data/test_repo.txt --mode test --filter E
run.bat --package A --repo tests/data/test_cycle.txt --mode test --max-depth 4

# Этап 4: обратные зависимости
run.bat --package F --repo tests/data/test_repo.txt --mode test --reverse

# Этап 5: D2 для трёх пакетов
run.bat --package requests --repo https://pypi.org --version 2.31.0 --d2
run.bat --package flask --repo https://pypi.org --version 3.0.0 --d2
run.bat --package pytest --repo https://pypi.org --version 8.0.0 --d2
```

## Сравнение со штатными инструментами

Результат можно сравнить с `pipdeptree` или `pip show`. Расхождения
возникают по двум причинам:

1. Маркеры окружения (PEP 508). В метаданных PyPI указаны зависимости
   для всех платформ (например, `colorama; sys_platform == "win32"`),
   а `pipdeptree` показывает только то, что реально установлено.
2. Версии транзитивных пакетов. Инструмент берёт последний релиз из
   PyPI, а в локальном окружении может стоять более старая версия.
