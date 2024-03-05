.DEFAULT_GOAL := all

all: safety linter

safety:
	safety --disable-optional-telemetry check -r requirements.txt --short-report

linter:
	flake8 --config ./.flake8 *.py

favicon:
	convert favicon-src.png -fill transparent -fuzz 25% -resize 64x64 -draw 'color 0,0 floodfill' -adaptive-sharpen 0x2 favicon.png
	optipng -o7 -zm1-9 -strip all favicon.png
	pngquant --quality 5-10 --strip -f -v --speed 1 --posterize 1 favicon.png
	mv favicon-fs8.png public/favicon.png
	rm -f favicon.png
