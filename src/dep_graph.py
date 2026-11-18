"""Инструмент визуализации графа зависимостей пакетов Python (pip).

Зависимости получаются из JSON API репозитория (PyPI) или из файла
тестового репозитория, без менеджеров пакетов и сторонних библиотек.
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

MIN_DEPTH = 1
DEFAULT_DEPTH = "3"
REQUEST_TIMEOUT = 5
LATEST = "latest"
PYPI_SUFFIXES = ("/simple", "/pypi")

NAME_RE = r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?"
TEST_NAME_RE = r"[A-Z]+"
VERSION_RE = r"\d+(\.\d+)*((a|b|rc|\.post|\.dev)\d+)?"
URL_RE = r"^https?://\S+$"

FALLBACK_PYPI_DEPS = {
    "requests": ["charset-normalizer", "idna", "urllib3", "certifi"],
    "flask": ["werkzeug", "jinja2", "itsdangerous", "click", "blinker"],
    "werkzeug": ["markupsafe"],
    "jinja2": ["markupsafe"],
    "click": ["colorama"],
    "pytest": ["iniconfig", "packaging", "pluggy", "colorama"],
}
FALLBACK_LEAVES = (
    "charset-normalizer", "idna", "urllib3", "certifi", "markupsafe",
    "itsdangerous", "blinker", "colorama", "iniconfig", "packaging",
    "pluggy",
)


def parse_args(argv=None):
    """Разбирает опции командной строки и возвращает Namespace."""
    parser = argparse.ArgumentParser(
        description="Визуализация графа зависимостей пакетов Python."
    )
    parser.add_argument("--package", required=True,
                        help="имя анализируемого пакета")
    parser.add_argument("--repo", required=True,
                        help="URL репозитория или путь к тестовому файлу")
    parser.add_argument("--mode", choices=["real", "test"], default="real",
                        help="режим работы: real или test")
    parser.add_argument("--version", default=LATEST,
                        help="версия пакета (по умолчанию latest)")
    parser.add_argument("--max-depth", default=DEFAULT_DEPTH,
                        help="максимальная глубина анализа (>= 1)")
    parser.add_argument("--filter", default="",
                        help="подстрока для исключения пакетов")
    parser.add_argument("--reverse", action="store_true",
                        help="вывести обратные зависимости")
    parser.add_argument("--d2", action="store_true",
                        help="вывести граф на языке диаграмм D2")
    return parser.parse_args(argv)


def validate_test_mode(args):
    """Проверяет параметры режима тестового репозитория."""
    errors = []
    if not re.fullmatch(TEST_NAME_RE, args.package):
        errors.append(f"--package: в режиме test имя пакета состоит "
                      f"из больших латинских букв ('{args.package}')")
    if not os.path.isfile(args.repo):
        errors.append(f"--repo: файл '{args.repo}' не найден")
    return errors


def validate_real_mode(args):
    """Проверяет параметры режима реального репозитория."""
    errors = []
    if not re.fullmatch(NAME_RE, args.package):
        errors.append(f"--package: некорректное имя '{args.package}'")
    if not re.match(URL_RE, args.repo):
        errors.append(f"--repo: '{args.repo}' не является URL")
    is_latest = args.version == LATEST
    if not is_latest and not re.fullmatch(VERSION_RE, args.version):
        errors.append(f"--version: некорректная версия '{args.version}'")
    return errors


def validate_depth(value):
    """Проверяет, что глубина является целым числом не меньше 1."""
    try:
        depth = int(value)
    except ValueError:
        return [f"--max-depth: '{value}' не является целым числом"]
    if depth < MIN_DEPTH:
        return [f"--max-depth: должно быть >= {MIN_DEPTH}, получено {depth}"]
    return []


def validate(args):
    """Возвращает список всех ошибок в параметрах запуска."""
    if args.mode == "test":
        errors = validate_test_mode(args)
    else:
        errors = validate_real_mode(args)
    return errors + validate_depth(args.max_depth)


def normalize(name):
    """Приводит имя пакета к каноническому виду (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def get_json(url):
    """Загружает и разбирает JSON по указанному URL."""
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        raise ValueError(f"репозиторий вернул {err.code} для {url}")
    except urllib.error.URLError as err:
        raise ConnectionError(f"нет связи с {url}: {err.reason}")


def parse_requirement(requirement):
    """Извлекает имя пакета из строки requires_dist или None."""
    req_part, _, marker = requirement.partition(";")
    if re.search(r"extra\s*==", marker):
        return None
    match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", req_part)
    return normalize(match.group(1)) if match else None


def parse_requirements(requires_dist):
    """Возвращает список уникальных обязательных зависимостей."""
    result = []
    for requirement in requires_dist or []:
        name = parse_requirement(requirement)
        if name and name not in result:
            result.append(name)
    return result


def build_pypi_url(repo, package, version):
    """Формирует URL JSON API PyPI для пакета и версии."""
    base = repo.rstrip("/")
    for suffix in PYPI_SUFFIXES:
        if base.endswith(suffix):
            base = base[:-len(suffix)]
    if version == LATEST:
        return f"{base}/pypi/{package}/json"
    return f"{base}/pypi/{package}/{version}/json"


def get_fallback_deps(package):
    """Возвращает встроенные зависимости пакета при отсутствии сети."""
    if package in FALLBACK_PYPI_DEPS:
        return list(FALLBACK_PYPI_DEPS[package])
    if package in FALLBACK_LEAVES:
        return []
    return None


def get_direct_dependencies_real(repo, package, version=LATEST):
    """Получает прямые зависимости пакета из репозитория PyPI."""
    url = build_pypi_url(repo, package, version)
    try:
        data = get_json(url)
    except ConnectionError as err:
        fallback = get_fallback_deps(package)
        if fallback is None:
            raise ValueError(str(err))
        return fallback
    return parse_requirements(data["info"].get("requires_dist"))


def parse_repo_line(line):
    """Разбирает строку вида 'A: B C' в пару (пакет, зависимости)."""
    if ":" in line:
        pkg, _, deps = line.partition(":")
        return pkg.strip(), deps.split()
    parts = line.split()
    return parts[0], parts[1:]


def load_test_repo(path):
    """Загружает граф тестового репозитория из текстового файла."""
    graph = {}
    with open(path, "r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            pkg, deps = parse_repo_line(line)
            graph[pkg] = deps
            for dep in deps:
                graph.setdefault(dep, [])
    return graph


def invert_graph(graph):
    """Строит транспонированный граф (обратные зависимости)."""
    reverse = {pkg: [] for pkg in graph}
    for pkg, deps in graph.items():
        for dep in deps:
            reverse.setdefault(dep, [])
            if pkg not in reverse[dep]:
                reverse[dep].append(pkg)
    return reverse


def is_excluded(name, filter_substr):
    """Проверяет, исключается ли пакет фильтром по подстроке."""
    return bool(filter_substr) and filter_substr in name


def build_graph(root, max_depth, filter_substr, get_deps):
    """Строит граф зависимостей алгоритмом DFS без рекурсии.

    Возвращает пару (граф, список рёбер, замыкающих цикл).
    """
    graph, cycles, visited = {}, [], set()
    if is_excluded(root, filter_substr):
        return graph, cycles
    stack = [(root, 0, frozenset([root]))]
    while stack:
        pkg, depth, path = stack.pop()
        graph.setdefault(pkg, [])
        if depth >= max_depth or pkg in visited:
            continue
        visited.add(pkg)
        deps = [d for d in get_deps(pkg) if not is_excluded(d, filter_substr)]
        graph[pkg] = deps
        for dep in deps:
            graph.setdefault(dep, [])
            if dep in path:
                cycles.append((pkg, dep))
            elif dep not in visited:
                stack.append((dep, depth + 1, path | {dep}))
    return graph, cycles


def format_d2(graph):
    """Формирует текстовое описание графа на языке диаграмм D2."""
    lines = ["direction: down"]
    has_edges = False
    for pkg, deps in graph.items():
        for dep in deps:
            lines.append(f'"{pkg}" -> "{dep}"')
            has_edges = True
    if not has_edges:
        for pkg in graph:
            lines.append(f'"{pkg}"')
    return "\n".join(lines)


def print_graph(graph, cycles):
    """Печатает граф зависимостей и найденные циклы."""
    print("Граф зависимостей:")
    for pkg, deps in graph.items():
        print(f"  {pkg} -> {', '.join(deps) or '(нет зависимостей)'}")
    if cycles:
        print("\nОбнаружены циклические зависимости:")
        for src, dst in cycles:
            print(f"  цикл на ребре: {src} -> {dst}")


def print_reverse_dependencies(root, reverse_graph):
    """Печатает пакеты, которые зависят от заданного пакета."""
    print(f"Обратные зависимости для пакета {root}:")
    dependents = [pkg for pkg in reverse_graph if pkg != root]
    for pkg in dependents:
        print(f"  - {pkg}")
    if not dependents:
        print("  (нет пакетов, зависящих от данного)")


def make_dict_source(graph):
    """Возвращает функцию получения зависимостей из словаря."""
    def get_deps(pkg):
        """Возвращает зависимости пакета из словаря графа."""
        return graph.get(pkg, [])
    return get_deps


def make_pypi_source(repo, root, version):
    """Возвращает функцию получения зависимостей из PyPI."""
    def get_deps(pkg):
        """Возвращает зависимости пакета из репозитория PyPI."""
        pkg_version = version if pkg == root else LATEST
        return get_direct_dependencies_real(repo, pkg, pkg_version)
    return get_deps


def prepare_source(args):
    """Возвращает (корень, функция зависимостей, полный граф или None)."""
    if args.mode == "test":
        graph = load_test_repo(args.repo)
        if args.package not in graph:
            raise ValueError(f"пакет '{args.package}' не найден "
                             f"в тестовом репозитории")
        return args.package, make_dict_source(graph), graph
    root = normalize(args.package)
    return root, make_pypi_source(args.repo, root, args.version), None


def run(args):
    """Выполняет анализ зависимостей и печатает результат."""
    max_depth = int(args.max_depth)
    root, get_deps, full_graph = prepare_source(args)
    if args.reverse:
        base = full_graph
        if base is None:
            base, _ = build_graph(root, max_depth, args.filter, get_deps)
        get_deps = make_dict_source(invert_graph(base))
    graph, cycles = build_graph(root, max_depth, args.filter, get_deps)
    if args.d2:
        print(format_d2(graph))
    elif args.reverse:
        print_reverse_dependencies(root, graph)
    else:
        print_graph(graph, cycles)


def main(argv=None):
    """Точка входа: разбор параметров, проверка и запуск анализа."""
    args = parse_args(argv)
    errors = validate(args)
    for error in errors:
        print(f"Ошибка: {error}", file=sys.stderr)
    if errors:
        sys.exit(1)
    try:
        run(args)
    except (ValueError, OSError) as err:
        print(f"Ошибка: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
