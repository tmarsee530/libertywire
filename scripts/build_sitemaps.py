#!/usr/bin/env python3
"""Build the sitemap for the current Rally Point News product."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rallypointnews.com"


def iso_mtime(path: Path):
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def indent(tree):
    try: tree.indent(space="  ")
    except AttributeError: pass


def write_standard():
    # Keep the sitemap limited to durable pages that are part of the current
    # product. Retired Brief, topic, local, newsletter and game URLs stay out.
    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    entries = [(BASE + "/", iso_mtime(ROOT / "index.html"))]
    for route in ("about", "privacy"):
        page = ROOT / route / "index.html"
        if page.exists(): entries.append((BASE + f"/{route}/", iso_mtime(page)))
    for loc,lastmod in entries:
        u=SubElement(root,"url");SubElement(u,"loc").text=loc
        if lastmod:SubElement(u,"lastmod").text=lastmod
    tree=ElementTree(root);indent(tree);tree.write(ROOT/"sitemap.xml",encoding="utf-8",xml_declaration=True)


def write_news():
    # Rally Point currently aggregates/link-ranks publisher headlines rather than
    # publishing first-party news articles. An empty News sitemap is more accurate
    # than submitting retired Brief URLs as current Google News content.
    root=Element("urlset",xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    tree=ElementTree(root);indent(tree);tree.write(ROOT/"news-sitemap.xml",encoding="utf-8",xml_declaration=True)


if __name__=="__main__":
    write_standard();write_news();print("Built current-product sitemap: homepage + about + privacy; retired product URLs excluded")
