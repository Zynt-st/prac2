# prac2 - визуализация графа зависимостей (Вариант 6)

CLI-инструмент для построения графа зависимостей пакетов Python (pip).
Сейчас реализован **Этап 1: минимальный прототип с конфигурацией**.

## Параметры командной строки

| Параметр | Описание |
| --- | --- |
| `--package` | имя анализируемого пакета (обязательный) |
| `--repo` | URL репозитория или путь к файлу тестового репозитория (обязательный) |
| `--mode` | режим работы: `real` или `test` (по умолчанию `real`) |
| `--version` | версия пакета (обязательный) |
| `--max-depth` | максимальная глубина анализа, целое число >= 1 (по умолчанию 3) |
| `--filter` | подстрока для фильтрации пакетов |

## Запуск

```bash
python dep_graph.py --package requests --repo https://pypi.org/simple --version 2.31.0 --max-depth 2 --filter test
```

Вывод:

```text
Параметры запуска:
package = requests
repo = https://pypi.org/simple
mode = real
version = 2.31.0
max_depth = 2
filter = test
```

## Примеры ошибок

```bash
python dep_graph.py --package "bad name!" --repo https://pypi.org --version 1.0
python dep_graph.py --package A --repo not_a_url --version 1.0
python dep_graph.py --package A --repo missing.txt --mode test --version 1.0
python dep_graph.py --package A --repo https://pypi.org --version abc
python dep_graph.py --package A --repo https://pypi.org --version 1.0 --max-depth 0
python dep_graph.py --package A --repo https://pypi.org --version 1.0 --max-depth x
```

При ошибке выводится сообщение `Ошибка: ...` и программа завершается с кодом 1.
