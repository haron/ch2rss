import asyncio
import os
import re
import sys
from datetime import datetime
from textwrap import shorten

import httpx
from asgiref.wsgi import WsgiToAsgi
from bs4 import BeautifulSoup
from cssutils import parseStyle
from flask import Flask, make_response, request
from flask_caching import Cache
from rfeed import Feed, Item

app = Flask(__name__)
app.config["CACHE_TYPE"] = os.environ.get("CACHE_TYPE", "SimpleCache")
asgi_app = WsgiToAsgi(app)
cache = Cache(app)
cache_seconds = 3600


if app.config["CACHE_TYPE"] == "MemcachedCache":
    import pylibmc

    pylibmc.Client(["127.0.0.1"]).flush_all()


class ChannelNotFound(Exception):
    pass


def make_key(*args, **kwargs):
    return f"{request.path}?{request.query_string}"


@app.route("/<channel>")
@cache.cached(timeout=cache_seconds, make_cache_key=make_key)
async def rss(channel):
    if not re.match(r"^\w{5,32}$", channel):
        return "Invalid channel name", 400

    try:
        resp = make_response(
            await channel_to_rss(
                channel,
                include=request.args.get("include"),
                exclude=request.args.get("exclude"),
            )
        )
        resp.headers["Content-type"] = "text/xml;charset=UTF-8"
        resp.headers["Cache-Control"] = f"max-age={cache_seconds}"
        return resp
    except ChannelNotFound:
        return f"Channel not found or it cannot be previewed at https://t.me/s/{channel}", 404


def get_message_divs(doc):
    return doc.select("div[class~='tgme_widget_message_bubble']")


def get_link_from_div(div):
    return div.select("a[href][class='tgme_widget_message_date']")[0].attrs["href"]


def get_text_from_div(div):
    elems = div.select("div[class~='tgme_widget_message_text']")
    if elems:
        return elems[0].get_text("\n", strip=True)
    else:
        return get_link_from_div(div)


def get_images_from_div(div):
    ret = []
    for elem in div.select("a[class~='tgme_widget_message_photo_wrap']"):
        style = parseStyle(elem["style"])
        ret.append(re.sub(r"^url\((.+)\)$", r"\1", style.backgroundImage))
    return ret


def get_item_from_div(div):
    return {
        "link": get_link_from_div(div),
        "title": shorten(get_text_from_div(div), width=250, placeholder="..."),
        "description": get_text_from_div(div),
        "pubDate": datetime.fromisoformat(div.select("time[class='time']")[0].attrs["datetime"]),
    }


async def get_doc_from_url(url):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            res.raise_for_status()
        return BeautifulSoup(res.content, "lxml")
    except httpx.HTTPStatusError as e:
        if "Redirect response" in str(e):
            raise ChannelNotFound()


def channel_not_found(doc):
    elems = doc.select("div[class='tgme_page_description']")
    if elems and elems[0].text.strip().startswith("If you have Telegram, you can contact @"):
        return True


async def channel_to_rss(channel, include=None, exclude=None):
    url = f"https://t.me/s/{channel}"
    doc = await get_doc_from_url(url)
    if channel_not_found(doc):
        raise ChannelNotFound()
    items = [Item(**get_item_from_div(d)) for d in get_message_divs(doc)]
    if exclude:
        items = [i for i in items if exclude.lower() not in i.description.lower()]
    if include:
        items = [i for i in items if include.lower() in i.description.lower()]
    feed = Feed(
        title=doc.title.text,
        link=url,
        description=doc.select("meta[content][property='og:description']")[0].attrs["content"],
        lastBuildDate=datetime.now(),
        items=items,
    )
    return feed.rss()


async def cli_main():
    include = None
    if len(sys.argv) > 2:
        include = sys.argv[2]
    print(await channel_to_rss(sys.argv[1], include=include))


if __name__ == "__main__":
    asyncio.run(cli_main())
