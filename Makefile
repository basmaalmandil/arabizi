PYTHON ?= python3

.PHONY: test demo bench
test:
	$(PYTHON) -m unittest discover -s tests -v
demo:
	$(PYTHON) demo.py
bench:
	$(PYTHON) benchmarks/run.py --repeats 9
