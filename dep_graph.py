import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request


def parse_args():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей пакетов (Python/pip)."
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


def normalize(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def get_json(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        raise ValueError(f"репозиторий вернул ошибку {e.code} для {url}")
    except urllib.error.URLError as e:
        raise ValueError(f"не удалось подключиться к {url}: {e.reason}")


def parse_requirements(requires_dist):
    result = []
    for req in requires_dist or []:
        if ";" in req:
            req_part, marker = req.split(";", 1)
        else:
            req_part, marker = req, ""
        if re.search(r"extra\s*==", marker):
            continue
        m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", req_part)
        if m:
            name = normalize(m.group(1))
            if name not in result:
                result.append(name)
    return result


def get_direct_dependencies(repo, package, version):
    url = f"{repo.rstrip('/')}/{package}/{version}/json"
    data = get_json(url)
    return parse_requirements(data["info"].get("requires_dist"))


def main():
    args = parse_args()
    errors = validate(args)

    if errors:
        for e in errors:
            print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    if args.mode == "test":
        print("Ошибка: режим test будет реализован на следующих этапах", file=sys.stderr)
        sys.exit(1)

    package = normalize(args.package)
    try:
        deps = get_direct_dependencies(args.repo, package, args.version)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Прямые зависимости {package} {args.version}:")
    if deps:
        for d in deps:
            print(f"  - {d}")
    else:
        print("  (нет зависимостей)")


if __name__ == "__main__":
    main()
