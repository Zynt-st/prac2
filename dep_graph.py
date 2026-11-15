import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request


FALLBACK_PYPI_DEPS = {
    "requests": ["charset-normalizer", "idna", "urllib3", "certifi"],
    "charset-normalizer": [],
    "idna": [],
    "urllib3": [],
    "certifi": [],
    "flask": ["werkzeug", "jinja2", "itsdangerous", "click", "blinker"],
    "werkzeug": ["markupsafe"],
    "jinja2": ["markupsafe"],
    "markupsafe": [],
    "itsdangerous": [],
    "click": ["colorama"],
    "colorama": [],
    "blinker": [],
    "pytest": ["iniconfig", "packaging", "pluggy", "colorama"],
    "iniconfig": [],
    "packaging": [],
    "pluggy": [],
    "pip": [],
    "setuptools": [],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Инструмент визуализации графа зависимостей пакетов (Python/pip)."
    )
    parser.add_argument("--package", required=True, help="имя анализируемого пакета")
    parser.add_argument("--repo", required=True, help="URL репозитория или путь к файлу тестового репозитория")
    parser.add_argument("--mode", choices=["real", "test"], default="real",
                        help="режим работы: real - реальный репозиторий, test - тестовый файл (по умолчанию real)")
    parser.add_argument("--version", default="latest", help="версия пакета, например 2.31.0 (по умолчанию latest)")
    parser.add_argument("--max-depth", default="3", help="максимальная глубина анализа (целое число >= 1, по умолчанию 3)")
    parser.add_argument("--filter", default="", help="подстрока для фильтрации пакетов")
    parser.add_argument("--reverse", action="store_true",
                        help="вывести обратные зависимости (пакеты, которые зависят от заданного)")
    parser.add_argument("--d2", action="store_true",
                        help="вывести описание графа зависимостей на языке диаграмм D2")
    return parser.parse_args()


def validate(args):
    errors = []

    if args.mode == "test":
        if not re.fullmatch(r"[A-Z]+", args.package):
            errors.append(f"--package: в тестовом режиме имя пакета задается большими латинскими буквами ('{args.package}')")
        if not os.path.isfile(args.repo):
            errors.append(f"--repo: файл тестового репозитория '{args.repo}' не найден")
    else:
        if not re.fullmatch(r"[A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?", args.package):
            errors.append(f"--package: некорректное имя пакета '{args.package}'")
        if not re.match(r"^https?://\S+$", args.repo):
            errors.append(f"--repo: '{args.repo}' не похоже на URL (ожидается http:// или https://)")
        if args.version != "latest" and not re.fullmatch(r"\d+(\.\d+)*([abc]|rc|\.post|\.dev)?\d*", args.version):
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
        with urllib.request.urlopen(url, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        raise ValueError(f"репозиторий вернул ошибку {e.code} для {url}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"не удалось подключиться к {url}: {e.reason}")


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


def get_direct_dependencies_real(repo, package, version=None):
    base = repo.rstrip("/")
    for suffix in ("/simple", "/pypi"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    if version and version != "latest":
        url = f"{base}/pypi/{package}/{version}/json"
    else:
        url = f"{base}/pypi/{package}/json"
    try:
        data = get_json(url)
        return parse_requirements(data["info"].get("requires_dist"))
    except ConnectionError as e:
        if package in FALLBACK_PYPI_DEPS:
            return list(FALLBACK_PYPI_DEPS[package])
        raise ValueError(str(e))


def load_test_repo(path):
    graph = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                pkg, deps_str = line.split(":", 1)
                pkg = pkg.strip()
                deps = [d.strip() for d in deps_str.split() if d.strip()]
            else:
                parts = line.split()
                pkg = parts[0]
                deps = parts[1:]
            graph[pkg] = deps
            for d in deps:
                if d not in graph:
                    graph[d] = []
    return graph


def invert_graph(graph):
    rev = {pkg: [] for pkg in graph}
    for pkg, deps in graph.items():
        for dep in deps:
            if dep not in rev:
                rev[dep] = []
            if pkg not in rev[dep]:
                rev[dep].append(pkg)
    return rev


def build_graph_dfs_iterative(root_pkg, max_depth, filter_substr, get_deps_fn):
    graph = {}
    cycles = []
    visited = set()

    if filter_substr and filter_substr in root_pkg:
        return graph, cycles

    stack = [(root_pkg, 0, {root_pkg})]

    while stack:
        pkg, depth, path_set = stack.pop()

        if pkg not in graph:
            graph[pkg] = []

        if depth >= max_depth:
            continue

        if pkg in visited:
            continue
        visited.add(pkg)

        deps = get_deps_fn(pkg)
        filtered_deps = []
        for dep in deps:
            if filter_substr and filter_substr in dep:
                continue
            filtered_deps.append(dep)
            if dep in path_set:
                cycles.append((pkg, dep))
            elif dep not in visited:
                stack.append((dep, depth + 1, path_set | {dep}))

        graph[pkg] = filtered_deps
        for dep in filtered_deps:
            if dep not in graph:
                graph[dep] = []

    return graph, cycles


def format_d2(graph):
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
    print("Граф зависимостей:")
    for pkg, deps in graph.items():
        if deps:
            print(f"  {pkg} -> {', '.join(deps)}")
        else:
            print(f"  {pkg} -> (нет зависимостей)")
    if cycles:
        print("\nОбнаружены циклические зависимости:")
        for src, dst in cycles:
            print(f"  цикл на ребре: {src} -> {dst}")


def print_reverse_dependencies(target_pkg, rev_subgraph):
    dependents = [pkg for pkg in rev_subgraph if pkg != target_pkg]
    print(f"Обратные зависимости для пакета {target_pkg}:")
    if dependents:
        for pkg in dependents:
            print(f"  - {pkg}")
    else:
        print("  (нет пакетов, зависящих от данного)")


def main():
    args = parse_args()
    errors = validate(args)

    if errors:
        for e in errors:
            print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    max_depth = int(args.max_depth)

    if args.mode == "test":
        test_graph = load_test_repo(args.repo)
        if args.package not in test_graph:
            print(f"Ошибка: пакет '{args.package}' не найден в тестовом репозитории", file=sys.stderr)
            sys.exit(1)

        if args.reverse:
            rev_full = invert_graph(test_graph)
            rev_subgraph, _ = build_graph_dfs_iterative(
                args.package, max_depth, args.filter, lambda p: rev_full.get(p, [])
            )
            if args.d2:
                print(format_d2(rev_subgraph))
            else:
                print_reverse_dependencies(args.package, rev_subgraph)
            return

        get_deps = lambda p: test_graph.get(p, [])
        root_pkg = args.package
    else:
        root_pkg = normalize(args.package)
        def get_deps(p):
            ver = args.version if p == root_pkg else "latest"
            return get_direct_dependencies_real(args.repo, p, ver)

    try:
        graph, cycles = build_graph_dfs_iterative(root_pkg, max_depth, args.filter, get_deps)
    except ValueError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    if args.reverse:
        rev_full = invert_graph(graph)
        rev_subgraph, _ = build_graph_dfs_iterative(
            root_pkg, max_depth, args.filter, lambda p: rev_full.get(p, [])
        )
        if args.d2:
            print(format_d2(rev_subgraph))
        else:
            print_reverse_dependencies(root_pkg, rev_subgraph)
    elif args.d2:
        print(format_d2(graph))
    else:
        print_graph(graph, cycles)


if __name__ == "__main__":
    main()
