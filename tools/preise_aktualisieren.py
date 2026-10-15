"""
DealKira – Preise automatisch aktualisieren

Läuft jeden Tag über GitHub Actions (.github/workflows/preise.yml).
Lädt die Awin-Produktfeeds und aktualisiert in produkte.json
Preis, Bild und Link aller Shops, die ein "feed" + "feedId" haben.

Feeds werden als GitHub-Secrets hinterlegt (nie im Code!):
  AWIN_FEED_AOSU     → Download-Link des aosu-Feeds
  AWIN_FEED_ANTHBOT  → Download-Link des Anthbot-Feeds
Ein neuer Feed: Secret anlegen und unten in FEEDS eintragen.
"""

import csv
import gzip
import io
import json
import os
import sys
import urllib.request

FEEDS = {
    "aosu": "AWIN_FEED_AOSU",
    "anthbot": "AWIN_FEED_ANTHBOT",
}

DATEI = "produkte.json"


def preis_format(text):
    try:
        wert = float(text.split()[0])
    except (ValueError, IndexError):
        return ""
    if wert <= 0:
        return ""
    return f"{wert:.2f}".replace(".", ",") + " €"


def feed_laden(url):
    with urllib.request.urlopen(url, timeout=120) as antwort:
        daten = antwort.read()
    if daten[:2] == b"\x1f\x8b":
        daten = gzip.decompress(daten)
    text = daten.decode("utf-8-sig", errors="replace")
    return {zeile["id"]: zeile for zeile in csv.DictReader(io.StringIO(text))}


def main():
    produkte = json.load(open(DATEI, encoding="utf-8"))
    geaendert = 0

    for feed_name, secret in FEEDS.items():
        url = os.environ.get(secret, "").strip()
        if not url:
            print(f"{feed_name}: kein Feed-Link hinterlegt – übersprungen")
            continue
        try:
            feed = feed_laden(url)
        except Exception as fehler:
            print(f"{feed_name}: Feed konnte nicht geladen werden ({fehler})")
            continue
        print(f"{feed_name}: {len(feed)} Produkte im Feed")

        for produkt in produkte:
            for shop in produkt.get("shops", []):
                if shop.get("feed") != feed_name:
                    continue
                zeile = feed.get(shop.get("feedId", ""))
                if not zeile:
                    print(f"  nicht mehr im Feed: {produkt['name']}")
                    continue

                verfuegbar = zeile.get("availability") == "in_stock"
                preis = preis_format(zeile.get("sale_price") or zeile.get("price", ""))
                neu = {
                    "price": preis if verfuegbar else "",
                    "link": zeile.get("aw_deep_link") or shop.get("link", ""),
                }
                for feld, wert in neu.items():
                    if feld == "link" and not wert:
                        continue
                    if shop.get(feld) != wert:
                        print(f"  {produkt['name']}: {feld} {shop.get(feld)!r} → {wert!r}")
                        shop[feld] = wert
                        geaendert += 1

                bild = zeile.get("image_link", "")
                if bild and produkt.get("image") != bild:
                    produkt["image"] = bild
                    geaendert += 1

    if geaendert:
        with open(DATEI, "w", encoding="utf-8") as datei:
            datei.write(json.dumps(produkte, ensure_ascii=False, indent=2) + "\n")
    print(f"Fertig: {geaendert} Änderungen")


if __name__ == "__main__":
    sys.exit(main())
