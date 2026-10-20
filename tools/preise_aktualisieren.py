"""
DealKira – Preise automatisch aktualisieren

Läuft alle 6 Stunden über GitHub Actions (.github/workflows/preise.yml).
Lädt die Awin-Produktfeeds und aktualisiert in produkte.json
Preis, Bild und Link aller Shops, die ein "feed" + "feedId" haben.

Feeds werden als GitHub-Secrets hinterlegt (nie im Code!):
  AWIN_FEED_AOSU     → Download-Link des aosu-Feeds
  AWIN_FEED_ANTHBOT  → Download-Link des Anthbot-Feeds
  AWIN_FEED_IMOU     → Download-Link des Imou-Feeds
Ein neuer Feed: Secret anlegen und unten in FEEDS eintragen.

eBay (ebay_preise.py) braucht die Secrets EBAY_CLIENT_ID und EBAY_CLIENT_SECRET
und durchsucht zusätzlich telefone.json und tablets.json.
"""

import csv
import datetime
import gzip
import io
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ebay_preise  # noqa: E402

FEEDS = {
    "aosu": "AWIN_FEED_AOSU",
    "anthbot": "AWIN_FEED_ANTHBOT",
    "imou": "AWIN_FEED_IMOU",
    "narwal": "AWIN_FEED_NARWAL",
}

# Shops, deren Produkte automatisch neu angelegt werden, sobald sie im Feed auftauchen
# (Zubehör fällt über den Mindestpreis raus)
AUTO_IMPORT = {
    "narwal": {"shop": "Narwal", "marke": "Narwal", "kategorie": "staubsauger", "mindestpreis": 150},
}

DATEI = "produkte.json"
WEITERE_DATEIEN = ["telefone.json", "tablets.json"]   # nur für eBay
HISTORIE = "preise-historie.json"
DEALS = "deals-auto.json"

TAGE_BEHALTEN = 120     # so lange werden alte Preise gespeichert
VERGLEICH_TAGE = 30     # Preisangabenverordnung: niedrigster Preis der letzten 30 Tage
MIN_RABATT = 5          # erst ab 5 % gilt es als Deal


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
    # Zwei Awin-Formate: Google-Format ("id") und klassisches Format ("aw_product_id")
    feed = {}
    for zeile in csv.DictReader(io.StringIO(text)):
        schluessel = zeile.get("id") or zeile.get("aw_product_id")
        if schluessel:
            feed[schluessel] = zeile
    return feed


def slug(text):
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), ("+", " plus ")):
        text = text.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:60]


FARBEN = {"weiß", "weiss", "schwarz", "grau", "silber", "blau", "gold", "rot", "grün", "white", "black", "grey", "gray", "silver"}
BESCHREIBUNG = {"saugroboter", "wischroboter", "akku-staubsauger", "staubsauger", "mähroboter",
                "überwachungskamera", "kamera", "grundpaket", "deluxe", "paket"}


def modellname(titel, marke):
    """Macht aus Feed-Titeln einen sauberen Modellnamen:
    "NARWAL Freo 20 Saugroboter mit Wischfunktion" → "Narwal Freo 20"
    "Flow 2 mit Basisstation + Zubehörpaket für 1 Jahr" → "Narwal Flow 2"
    "Freo Z10 Ultra Silber" → "Narwal Freo Z10 Ultra" """
    rest = re.sub(r"^" + re.escape(marke) + r"\b", "", titel.strip(), flags=re.I).strip()
    rest = re.split(r"\s*(?::|\+|&|\(|\s[-–|,]\s|\smit\s|\sfür\s|\sinkl\.?\s)", rest)[0]
    woerter = []
    for wort in rest.split():
        if wort.lower() in FARBEN or wort.lower() in BESCHREIBUNG:
            break
        woerter.append(wort)
    return (marke + " " + " ".join(woerter)).strip() if woerter else ""


def neue_produkte(produkte, feed_name, feed, regel):
    """Legt Produkte aus dem Feed an, die es noch nicht gibt (eine Karte pro Produktname,
    bei Farbvarianten die günstigste)."""
    bekannt_ids = {shop.get("feedId") for p in produkte for shop in p.get("shops", [])
                   if shop.get("feed") == feed_name}
    bekannt_namen = {p["name"].lower() for p in produkte}
    vorhandene_ids = {p["id"] for p in produkte}

    kandidaten = {}
    for feed_id, zeile in feed.items():
        if feed_id in bekannt_ids:
            continue
        if zeile.get("availability", "in_stock") not in ("in_stock", ""):
            continue
        titel = (zeile.get("title") or zeile.get("product_name") or "").strip()
        preis = preis_format(zeile.get("sale_price") or zeile.get("price") or zeile.get("search_price", ""))
        if not titel or not preis or (preis_zahl(preis) or 0) < regel["mindestpreis"]:
            continue
        name = modellname(titel, regel["marke"])
        if not name:
            continue
        if name.lower() in bekannt_namen:
            continue
        alt = kandidaten.get(name.lower())
        if alt and preis_zahl(alt[1]) <= preis_zahl(preis):
            continue
        kandidaten[name.lower()] = (name, preis, feed_id, zeile)

    for name, preis, feed_id, zeile in kandidaten.values():
        pid = slug(name)
        while pid in vorhandene_ids:
            pid += "-2"
        vorhandene_ids.add(pid)
        produkte.append({
            "id": pid,
            "name": name,
            "brand": regel["marke"],
            "kategorie": regel["kategorie"],
            "image": zeile.get("image_link") or zeile.get("merchant_image_url", ""),
            "shops": [{
                "name": regel["shop"],
                "price": preis,
                "link": zeile.get("aw_deep_link") or zeile.get("link", ""),
                "feed": feed_name,
                "feedId": feed_id,
            }],
        })
        print(f"  NEU: {name} ({preis})")
    return len(kandidaten)


def main():
    produkte = json.load(open(DATEI, encoding="utf-8"))
    geaendert = 0
    fehler_gesamt = 0

    for feed_name, secret in FEEDS.items():
        url = os.environ.get(secret, "").strip()
        if not url:
            print(f"{feed_name}: kein Feed-Link hinterlegt – übersprungen")
            continue
        try:
            feed = feed_laden(url)
        except Exception as fehler:
            print(f"::error::{feed_name}: Feed konnte nicht geladen werden ({fehler})")
            fehler_gesamt += 1
            continue
        print(f"{feed_name}: {len(feed)} Produkte im Feed")
        if feed_name in AUTO_IMPORT:
            geaendert += neue_produkte(produkte, feed_name, feed, AUTO_IMPORT[feed_name])

        for produkt in produkte:
            for shop in produkt.get("shops", []):
                if shop.get("feed") != feed_name:
                    continue
                zeile = feed.get(shop.get("feedId", ""))
                if not zeile:
                    print(f"  nicht mehr im Feed: {produkt['name']}")
                    continue

                verfuegbar = zeile.get("availability", "in_stock") in ("in_stock", "")
                preis = preis_format(
                    zeile.get("sale_price") or zeile.get("price") or zeile.get("search_price", "")
                )
                # Streichpreis des Shops: Google-Format "price" (wenn "sale_price" gesetzt),
                # klassisches Format "product_price_old" bzw. "rrp_price" (UVP)
                if zeile.get("sale_price"):
                    statt, statt_art = preis_format(zeile.get("price", "")), "shop"
                elif preis_format(zeile.get("product_price_old", "")):
                    statt, statt_art = preis_format(zeile.get("product_price_old", "")), "shop"
                else:
                    statt, statt_art = preis_format(zeile.get("rrp_price", "")), "uvp"
                if not verfuegbar or not statt or (preis_zahl(statt) or 0) <= (preis_zahl(preis) or 0):
                    statt, statt_art = "", ""
                neu = {
                    "price": preis if verfuegbar else "",
                    "link": zeile.get("aw_deep_link") or shop.get("link", ""),
                    "statt": statt,
                    "stattArt": statt_art,
                }
                for feld, wert in neu.items():
                    if feld == "link" and not wert:
                        continue
                    if feld in ("statt", "stattArt") and not wert:
                        if feld in shop:
                            del shop[feld]
                            geaendert += 1
                        continue
                    if shop.get(feld) != wert:
                        print(f"  {produkt['name']}: {feld} {shop.get(feld)!r} → {wert!r}")
                        shop[feld] = wert
                        geaendert += 1

                bild = zeile.get("image_link") or zeile.get("merchant_image_url", "")
                if bild and produkt.get("image") != bild:
                    produkt["image"] = bild
                    geaendert += 1

    # eBay: alle drei Produktdateien
    dateien = {DATEI: produkte}
    for name in WEITERE_DATEIEN:
        dateien[name] = json.load(open(name, encoding="utf-8"))
    ebay_aenderungen, ebay_fehler = ebay_preise.aktualisieren(dateien)
    fehler_gesamt += ebay_fehler

    if geaendert or ebay_aenderungen:
        for name, liste in dateien.items():
            with open(name, "w", encoding="utf-8") as datei:
                datei.write(json.dumps(liste, ensure_ascii=False, indent=2) + "\n")
    geaendert += ebay_aenderungen

    historie_und_deals(produkte)
    print(f"Fertig: {geaendert} Änderungen")
    # Rotes ✗ bei GitHub, wenn ein hinterlegter Feed nicht geladen werden konnte
    return 1 if fehler_gesamt else 0


def preis_zahl(text):
    try:
        return float(text.replace("€", "").replace(".", "").replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def historie_und_deals(produkte):
    """Speichert die heutigen Preise und erkennt echte Preissenkungen.

    Ein Deal braucht mindestens 30 Tage Preisverlauf. Verglichen wird mit dem
    niedrigsten Preis der 30 Tage vor heute (§ 11 Preisangabenverordnung)."""
    heute = datetime.date.today()
    heute_text = heute.isoformat()

    try:
        historie = json.load(open(HISTORIE, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        historie = {}

    grenze = (heute - datetime.timedelta(days=TAGE_BEHALTEN)).isoformat()
    deals = []

    for produkt in produkte:
        for shop in produkt.get("shops", []):
            # eBay zählt nicht: dort wechselt der günstigste Händler ständig,
            # das ist keine Preissenkung eines Shops im Sinne der PAngV
            if not shop.get("feed") or shop.get("feed") == "ebay":
                continue
            schluessel = produkt["id"] + "|" + shop["name"]
            verlauf = [e for e in historie.get(schluessel, []) if e[0] >= grenze and e[0] != heute_text]
            preis = preis_zahl(shop.get("price", ""))
            if preis:
                verlauf.append([heute_text, preis])
            historie[schluessel] = verlauf
            if not preis or not verlauf:
                continue

            start = (heute - datetime.timedelta(days=VERGLEICH_TAGE)).isoformat()
            if verlauf[0][0] > start:
                continue  # noch keine 30 Tage Preisverlauf
            vorher = [p for d, p in verlauf if start <= d < heute_text]
            if not vorher:
                continue
            tiefst = min(vorher)
            if preis >= tiefst:
                continue
            rabatt = round((1 - preis / tiefst) * 100)
            if rabatt < MIN_RABATT:
                continue
            deals.append({
                "id": produkt["id"],
                "shop": shop["name"],
                "preis": shop["price"],
                "vorher": f"{tiefst:.2f}".replace(".", ",") + " €",
                "rabatt": rabatt,
            })

    deals.sort(key=lambda d: -d["rabatt"])

    # Angebote der Shops: aktueller Preis liegt unter dem Streichpreis bzw. der UVP aus dem Feed
    angebote = []
    schon_deal = {(d["id"], d["shop"]) for d in deals}
    for produkt in produkte:
        for shop in produkt.get("shops", []):
            if not shop.get("statt") or (produkt["id"], shop["name"]) in schon_deal:
                continue
            preis, statt = preis_zahl(shop.get("price", "")), preis_zahl(shop["statt"])
            if not preis or not statt or preis >= statt:
                continue
            rabatt = round((1 - preis / statt) * 100)
            if rabatt < MIN_RABATT:
                continue
            angebote.append({
                "id": produkt["id"],
                "shop": shop["name"],
                "preis": shop["price"],
                "statt": shop["statt"],
                "art": shop.get("stattArt", "shop"),
                "rabatt": rabatt,
            })
    angebote.sort(key=lambda d: -d["rabatt"])
    with open(HISTORIE, "w", encoding="utf-8") as datei:
        datei.write(json.dumps(historie, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n")
    with open(DEALS, "w", encoding="utf-8") as datei:
        datei.write(json.dumps({"stand": heute_text, "deals": deals, "angebote": angebote}, ensure_ascii=False, indent=2) + "\n")
    print(f"Preisverlauf: {len(historie)} Einträge, {len(deals)} automatische Deals")


if __name__ == "__main__":
    sys.exit(main())
