# prac2 — Визуализация графа зависимостей пакетов (Вариант 6, Этапы 1–5)

CLI-инструмент для анализа и визуализации графа зависимостей пакетов Python (`pip`) без использования сторонних библиотек и менеджеров пакетов.

## Параметры командной строки (Этап 1)

| Параметр | Описание |
| --- | --- |
| `--package` | Имя анализируемого пакета (обязательный) |
| `--repo` | URL репозитория (`https://pypi.org`) или путь к файлу тестового репозитория |
| `--mode` | Режим работы: `real` (по умолчанию) или `test` |
| `--version` | Версия пакета, например `2.31.0` (по умолчанию `latest`) |
| `--max-depth` | Максимальная глубина анализа, целое число `>= 1` (по умолчанию `3`) |
| `--filter` | Подстрока для исключения пакетов из анализа |
| `--reverse` | Режим вывода обратных зависимостей (Этап 4) |
| `--d2` | Вывод описания графа на языке диаграмм D2 (Этап 5) |

---

## Примеры запуска по этапам

### Этап 2. Прямые зависимости пакета из PyPI
```bash
python dep_graph.py --package requests --version 2.31.0 --repo https://pypi.org --max-depth 1
```

### Этап 3. Построение графа (DFS без рекурсии), фильтрация, циклы и тестовый режим
1. **Обычный обход тестового репозитория (`test_repo.txt`):**
   ```bash
   python dep_graph.py --package A --repo test_repo.txt --mode test --max-depth 3
   ```
2. **Фильтрация пакетов, содержащих подстроку `E`:**
   ```bash
   python dep_graph.py --package A --repo test_repo.txt --mode test --max-depth 3 --filter E
   ```
3. **Обнаружение циклических зависимостей (`test_cycle.txt`):**
   ```bash
   python dep_graph.py --package A --repo test_cycle.txt --mode test --max-depth 4
   ```

### Этап 4. Обратные зависимости (`--reverse`)
Поиск пакетов, которые зависят от заданного пакета `F` (использует тот же итеративный алгоритм DFS по транспонированному графу):
```bash
python dep_graph.py --package F --repo test_repo.txt --mode test --max-depth 3 --reverse
```

### Этап 5. Визуализация на языке диаграмм D2 (`--d2`)

#### Примеры D2 для 3 различных пакетов:

1. **Пакет `requests` (2.31.0):**
   ```bash
   python dep_graph.py --package requests --version 2.31.0 --repo https://pypi.org --max-depth 2 --d2
   ```
   Вывод D2:
   ```d2
   direction: down
   "requests" -> "charset-normalizer"
   "requests" -> "idna"
   "requests" -> "urllib3"
   "requests" -> "certifi"
   ```

2. **Пакет `flask` (3.0.0):**
   ```bash
   python dep_graph.py --package flask --version 3.0.0 --repo https://pypi.org --max-depth 2 --d2
   ```
   Вывод D2:
   ```d2
   direction: down
   "flask" -> "werkzeug"
   "flask" -> "jinja2"
   "flask" -> "itsdangerous"
   "flask" -> "click"
   "flask" -> "blinker"
   "jinja2" -> "markupsafe"
   "click" -> "colorama"
   "werkzeug" -> "markupsafe"
   ```

3. **Пакет `pytest` (8.0.0):**
   ```bash
   python dep_graph.py --package pytest --version 8.0.0 --repo https://pypi.org --max-depth 2 --d2
   ```
   Вывод D2:
   ```d2
   direction: down
   "pytest" -> "iniconfig"
   "pytest" -> "packaging"
   "pytest" -> "pluggy"
   "pytest" -> "exceptiongroup"
   "pytest" -> "tomli"
   "pytest" -> "colorama"
   ```

#### Сравнение со штатными инструментами (`pipdeptree` / `pip show`)
При сравнении вывода `dep_graph.py` с утилитой `pipdeptree` (которая анализирует уже установленное локальное окружение Python) могут наблюдаться небольшие расхождения:
1. **Маркеры окружения (PEP 508):** в метаданных PyPI (`requires_dist`) указаны условные зависимости для всех ОС и версий Python (например, `colorama ; sys_platform == "win32"` или `tomli ; python_version < "3.11"`). Наш инструмент извлекает полный перечень базовых зависимостей из метаданных пакета в репозитории, тогда как `pipdeptree` показывает только пакеты, реально установленные на конкретной ОС и версии интерпретатора.
2. **Разрешение версий транзитивных зависимостей:** для транзитивных пакетов анализируется актуальный релиз (`latest`) из репозитория PyPI, в то время как в локальном виртуальном окружении может быть зафиксирована более старая версия пакета.
