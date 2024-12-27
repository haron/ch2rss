SHELL := /usr/bin/env -S bash -O globstar # makes work globs like **/*.py
.DEFAULT_GOAL := deploy

deploy: linter
	uv lock
	ansible-playbook deploy.yml --skip-tags=full

full-deploy: linter
	uv lock
	ansible-playbook deploy.yml

safety:
	uv tool run safety scan -o bare

init: clean
	uv venv -q
	uv lock

clean:
	rm -rf .venv

githooks:
	git config --local core.hooksPath .githooks

linter: githooks
	python -m py_compile **/*.py
	uvx isort -q **/*.py
	uvx ruff format -q --line-length 140 **/*.py
	uvx ruff check -q --ignore F401 **/*.py

favicon:
	convert favicon-src.png -fill transparent -fuzz 25% -resize 64x64 -draw 'color 0,0 floodfill' -adaptive-sharpen 0x2 favicon.png
	optipng -o7 -zm1-9 -strip all favicon.png
	pngquant --quality 5-10 --strip -f -v --speed 1 --posterize 1 favicon.png
	mv favicon-fs8.png public/favicon.png
	rm -f favicon.png
