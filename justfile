#!/usr/bin/env just --justfile
export PYTHONPATH := "."

test:
    pytest tests

gen:
    ./gen_refs.py

validate:
    cp generated_output/* expected_output/
