.PHONY: test test-connections

test:
	python3 -m unittest discover -s tests

test-connections:
	tests/connections.sh
