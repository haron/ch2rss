import httpx
from bs4 import BeautifulSoup
from rfeed import Feed, Item
from datetime import datetime
from flask import Flask, make_response
from flask_caching import Cache
from cssutils import parseStyle
import os
import re
from textwrap import shorten
import sys
import asyncio


app = Flask(__name__)
app.config["CACHE_TYPE"] = os.environ.get("CACHE_TYPE", "SimpleCache")
cache = Cache(app)
cache_seconds = 3600


if app.config["CACHE_TYPE"] == "MemcachedCache":
    import pylibmc
    pylibmc.Client(["127.0.0.1"]).flush_all()


class ChannelNotFound(Exception):
    pass


@app.route("/<channel>")
@cache.cached(timeout=cache_seconds)
async def rss(channel):
    if not re.match(r"^\w{5,32}$", channel):
        return "Invalid channel name", 400

    try:
        resp = make_response(await channel_to_rss(channel))
        resp.headers["Content-type"] = "text/xml;charset=UTF-8"
        resp.headers["Cache-Control"] = f"max-age={cache_seconds}"
        return resp
    except ChannelNotFound:
        return "Channel not found", 404


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
        ret.append(re.sub(r'^url\((.+)\)$', r'\1', style.backgroundImage))
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


async def channel_to_rss(channel):
    url = f"https://t.me/s/{channel}"
    doc = await get_doc_from_url(url)
    if channel_not_found(doc):
        raise ChannelNotFound()
    feed = Feed(
        title=doc.title.text,
        link=url,
        description=doc.select("meta[content][property='og:description']")[0].attrs["content"],
        lastBuildDate=datetime.now(),
        items=[Item(**get_item_from_div(d)) for d in get_message_divs(doc)],
    )
    return feed.rss()


async def cli_main():
    print(await channel_to_rss(sys.argv[1]))


if __name__ == "__main__":
    asyncio.run(cli_main())
