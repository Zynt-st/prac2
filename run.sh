#!/bin/sh
if [ "$1" = "test" ]; then
    PYTHONPATH=. python3 -m unittest discover -s tests -v
else
    python3 src/dep_graph.py "$@"
fi
