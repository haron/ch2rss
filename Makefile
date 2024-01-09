.DEFAULT_GOAL := all

all: safety linter

safety:
	safety --disable-optional-telemetry check -r requirements.txt --short-report

linter:
	flake8 --config ./.flake8 *.py
