@echo off
chcp 65001 > nul
echo ======================================================
echo Этап 3.1: Обход тестового репозитория (DFS без рекурсии)
echo ======================================================
python dep_graph.py --package A --repo test_repo.txt --mode test --max-depth 3

echo.
echo ======================================================
echo Этап 3.2: Фильтрация пакетов с подстрокой E (--filter E)
echo ======================================================
python dep_graph.py --package A --repo test_repo.txt --mode test --max-depth 3 --filter E

echo.
echo ======================================================
echo Этап 3.3: Циклические зависимости (test_cycle.txt)
echo ======================================================
python dep_graph.py --package A --repo test_cycle.txt --mode test --max-depth 4

echo.
echo ======================================================
echo Этап 4: Обратные зависимости для пакета F (--reverse)
echo ======================================================
python dep_graph.py --package F --repo test_repo.txt --mode test --max-depth 3 --reverse

echo.
echo ======================================================
echo Этап 5: Описание графа на языке диаграмм D2 (--d2)
echo ======================================================
python dep_graph.py --package A --repo test_repo.txt --mode test --max-depth 3 --d2
pause
