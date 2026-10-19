"""
DealKira – sitemap.xml automatisch erzeugen

Behält alle festen Seiten aus der bestehenden sitemap.xml und hängt
für jedes Produkt seine Detailseite an:
  produkte.json → artikel.html?id=…
  telefone.json → produkt.html?id=…
  tablets.json  → tablet-produkt.html?id=…
Wird vom Preis-Bot nach jedem Lauf aufgerufen, neue Produkte landen
also automatisch bei Google.
"""

import json
import re
import urllib.parse
from xml.sax.saxutils import escape

BASIS = "https://dealkira.com/"
DATEI = "sitemap.xml"
PRODUKTSEITEN = {
    "produkte.json": "artikel.html",
    "telefone.json": "produkt.html",
    "tablets.json": "tablet-produkt.html",
}


def main():
    alt = open(DATEI, encoding="utf-8").read()
    feste = [u for u in re.findall(r"<loc>(.*?)</loc>", alt) if "?id=" not in u]

    urls = list(dict.fromkeys(feste))
    for datei, seite in PRODUKTSEITEN.items():
        for produkt in json.load(open(datei, encoding="utf-8")):
            if produkt.get("id"):
                urls.append(BASIS + seite + "?id=" + urllib.parse.quote(produkt["id"]))

    zeilen = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    zeilen += [f"  <url><loc>{escape(u)}</loc></url>" for u in urls]
    zeilen.append("</urlset>")
    neu = "\n".join(zeilen) + "\n"

    if neu != alt:
        open(DATEI, "w", encoding="utf-8").write(neu)
    print(f"sitemap: {len(feste)} feste Seiten, {len(urls) - len(feste)} Produktseiten")


if __name__ == "__main__":
    main()
