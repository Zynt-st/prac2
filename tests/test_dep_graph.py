"""Модульные тесты для инструмента графа зависимостей."""

import argparse
import os
import unittest

from src import dep_graph

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_FILE = os.path.join(TESTS_DIR, "data", "test_repo.txt")
CYCLE_FILE = os.path.join(TESTS_DIR, "data", "test_cycle.txt")


def make_args(**overrides):
    """Создаёт Namespace с параметрами по умолчанию для тестов."""
    params = {
        "package": "A", "repo": REPO_FILE, "mode": "test",
        "version": "latest", "max_depth": "3", "filter": "",
        "reverse": False, "d2": False,
    }
    params.update(overrides)
    return argparse.Namespace(**params)


def build_from_file(path, root, depth, filter_substr=""):
    """Строит граф из тестового файла репозитория."""
    graph = dep_graph.load_test_repo(path)
    source = dep_graph.make_dict_source(graph)
    return dep_graph.build_graph(root, depth, filter_substr, source)


class ValidationTests(unittest.TestCase):
    """Проверка обработки ошибок параметров."""

    def test_valid_params(self):
        """Корректные параметры не дают ошибок."""
        self.assertEqual(dep_graph.validate(make_args()), [])

    def test_bad_test_package_name(self):
        """В режиме test имя должно состоять из больших букв."""
        self.assertTrue(dep_graph.validate(make_args(package="abc")))

    def test_missing_repo_file(self):
        """Отсутствующий файл репозитория является ошибкой."""
        self.assertTrue(dep_graph.validate(make_args(repo="nope.txt")))

    def test_bad_depth(self):
        """Глубина должна быть целым числом не меньше 1."""
        self.assertTrue(dep_graph.validate_depth("0"))
        self.assertTrue(dep_graph.validate_depth("x"))

    def test_real_mode_errors(self):
        """Некорректные имя, URL и версия в режиме real."""
        args = make_args(mode="real", package="bad name!",
                         repo="not_url", version="abc")
        self.assertEqual(len(dep_graph.validate(args)), 3)


class ParsingTests(unittest.TestCase):
    """Разбор метаданных пакетов PyPI."""

    def test_skip_extras(self):
        """Опциональные зависимости extra пропускаются."""
        reqs = ["idna (<4,>=2.5)", "PySocks; extra == 'socks'"]
        self.assertEqual(dep_graph.parse_requirements(reqs), ["idna"])

    def test_normalize_name(self):
        """Имена приводятся к каноническому виду."""
        self.assertEqual(dep_graph.normalize("Charset_Normalizer"),
                         "charset-normalizer")

    def test_build_url(self):
        """Суффикс simple в адресе репозитория отбрасывается."""
        url = dep_graph.build_pypi_url("https://pypi.org/simple",
                                       "requests", "2.31.0")
        self.assertEqual(url, "https://pypi.org/pypi/requests/2.31.0/json")


class GraphTests(unittest.TestCase):
    """Построение графа, глубина, фильтр и циклы."""

    def test_full_graph(self):
        """Обход находит все достижимые пакеты."""
        graph, _ = build_from_file(REPO_FILE, "A", 3)
        self.assertEqual(set(graph), {"A", "B", "C", "D", "E", "F"})

    def test_depth_limit(self):
        """Глубина 1 оставляет только прямые зависимости."""
        graph, _ = build_from_file(REPO_FILE, "A", 1)
        self.assertEqual(set(graph), {"A", "B", "C"})

    def test_filter(self):
        """Пакеты с подстрокой фильтра исключаются."""
        graph, _ = build_from_file(REPO_FILE, "A", 3, "E")
        self.assertNotIn("E", graph)

    def test_cycles(self):
        """Циклические зависимости обнаруживаются без зацикливания."""
        _, cycles = build_from_file(CYCLE_FILE, "A", 4)
        self.assertTrue(cycles)


class ReverseAndD2Tests(unittest.TestCase):
    """Обратные зависимости и вывод на языке D2."""

    def test_reverse(self):
        """От пакета F зависят A, B, C и E."""
        graph = dep_graph.load_test_repo(REPO_FILE)
        source = dep_graph.make_dict_source(dep_graph.invert_graph(graph))
        rev, _ = dep_graph.build_graph("F", 3, "", source)
        self.assertEqual(set(rev) - {"F"}, {"A", "B", "C", "E"})

    def test_d2(self):
        """Описание D2 содержит рёбра графа."""
        text = dep_graph.format_d2({"A": ["B"], "B": []})
        self.assertIn('"A" -> "B"', text)


if __name__ == "__main__":
    unittest.main()
