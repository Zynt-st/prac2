@echo off
chcp 65001 > nul
if "%1"=="test" (
    set PYTHONPATH=.
    python -m unittest discover -s tests -v
) else (
    python src\dep_graph.py %*
)
