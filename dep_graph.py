import argparse
import os
import re
import sys


def parse_args():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей пакетов (Python/pip). Этап 1."
    )
    parser.add_argument("--package", required=True, help="имя анализируемого пакета")
    parser.add_argument("--repo", required=True, help="URL репозитория или путь к файлу тестового репозитория")
    parser.add_argument("--mode", choices=["real", "test"], default="real",
                        help="режим работы: real - реальный репозиторий, test - тестовый файл (по умолчанию real)")
    parser.add_argument("--version", required=True, help="версия пакета, например 2.31.0")
    parser.add_argument("--max-depth", default="3", help="максимальная глубина анализа (целое число >= 1, по умолчанию 3)")
    parser.add_argument("--filter", default="", help="подстрока для фильтрации пакетов")
    return parser.parse_args()


def validate(args):
    errors = []

    if not re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?", args.package):
        errors.append(f"--package: некорректное имя пакета '{args.package}'")

    if args.mode == "test":
        if not os.path.isfile(args.repo):
            errors.append(f"--repo: файл тестового репозитория '{args.repo}' не найден")
    else:
        if not re.match(r"^https?://\S+$", args.repo):
            errors.append(f"--repo: '{args.repo}' не похоже на URL (ожидается http:// или https://)")

    if not re.fullmatch(r"\d+(\.\d+)*([abc]|rc|\.post|\.dev)?\d*", args.version):
        errors.append(f"--version: некорректная версия '{args.version}' (пример: 1.2.3)")

    try:
        depth = int(args.max_depth)
        if depth < 1:
            errors.append(f"--max-depth: значение должно быть не меньше 1, получено {depth}")
    except ValueError:
        errors.append(f"--max-depth: '{args.max_depth}' не является целым числом")

    return errors


def main():
    args = parse_args()
    errors = validate(args)

    if errors:
        for e in errors:
            print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    print("Параметры запуска:")
    print(f"package = {args.package}")
    print(f"repo = {args.repo}")
    print(f"mode = {args.mode}")
    print(f"version = {args.version}")
    print(f"max_depth = {args.max_depth}")
    print(f"filter = {args.filter}")


if __name__ == "__main__":
    main()
