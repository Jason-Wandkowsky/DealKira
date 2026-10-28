"""
DealKira – Daten für die Website schreiben

produkte.json enthält mit dem notebooksbilliger-Feed viele Tausend Produkte. Die Seiten
laden deshalb nicht mehr die ganze Datei, sondern:
  daten/kategorie/<kategorie>.json  → alle Produkte einer Kategorie (Kategorie- und Artikelseite)
  daten/index.json                  → kurze Liste aller Produkte (Suche, Merkliste, Ratgeber)
In deals-auto.json kommen außerdem die Produkte der Deals ("produkte") und ein paar
Produkte für die Startseite ("beliebt"), damit Startseite und Deal-Seite klein bleiben.
"""

import datetime
import hashlib
import json
import os
import re

ORDNER = os.path.join("daten", "kategorie")
INDEX = os.path.join("daten", "index.json")


def preis_zahl(text):
    try:
        return float(str(text).replace("€", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def kurz(produkt):
    """Nur, was Karten, Suche und Merkliste brauchen: günstigste Shops mit Preis und Link."""
    shops = [s for s in produkt.get("shops", []) if s.get("link")]
    mit_preis = sorted((s for s in shops if preis_zahl(s.get("price"))),
                       key=lambda s: preis_zahl(s["price"]))
    gezeigt = mit_preis[:3] or shops[:1]
    eintrag = {"id": produkt["id"], "name": produkt.get("name", ""), "brand": produkt.get("brand", ""),
               "kategorie": produkt.get("kategorie", ""), "image": produkt.get("image", ""),
               "shops": [{"name": s.get("name", ""), "price": s.get("price", ""), "link": s["link"]}
                         for s in gezeigt]}
    for feld in ("statt",):
        if gezeigt and gezeigt[0].get(feld):
            eintrag["shops"][0][feld] = gezeigt[0][feld]
    return eintrag


def schreiben_wenn_anders(pfad, inhalt):
    try:
        if open(pfad, encoding="utf-8").read() == inhalt:
            return False
    except FileNotFoundError:
        pass
    with open(pfad, "w", encoding="utf-8") as datei:
        datei.write(inhalt)
    return True


def kompakt(daten):
    return json.dumps(daten, ensure_ascii=False, separators=(",", ":")) + "\n"


def schreiben(produkte, deals_pfad):
    """produkte: Liste aus produkte.json (Telefone und Tablets haben eigene Dateien)."""
    os.makedirs(ORDNER, exist_ok=True)
    nach_kategorie = {}
    for p in produkte:
        nach_kategorie.setdefault(p.get("kategorie") or "ohne", []).append(p)

    for kategorie, liste in nach_kategorie.items():
        if re.fullmatch(r"[a-z0-9-]+", kategorie):
            schreiben_wenn_anders(os.path.join(ORDNER, kategorie + ".json"), kompakt(liste))
    # Kategorien, die es nicht mehr gibt, aufräumen
    for datei in os.listdir(ORDNER):
        if datei.endswith(".json") and datei[:-5] not in nach_kategorie:
            os.remove(os.path.join(ORDNER, datei))

    schreiben_wenn_anders(INDEX, kompakt([kurz(p) for p in produkte]))

    # Deals: Produktdaten mitliefern
    try:
        deals = json.load(open(deals_pfad, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        deals = {}
    nach_id = {p["id"]: p for p in produkte}
    ids = [d["id"] for d in deals.get("deals", []) + deals.get("angebote", []) if d["id"] in nach_id]
    deals["produkte"] = {i: kurz(nach_id[i]) for i in dict.fromkeys(ids)}
    # Startseite ohne Deals: jeden Tag andere Produkte mit Bild und Preis
    tag = datetime.date.today().isoformat()
    kandidaten = sorted((p for p in produkte if p.get("image")
                         and any(preis_zahl(s.get("price")) for s in p.get("shops", []))),
                        key=lambda p: hashlib.md5((tag + p["id"]).encode()).hexdigest())
    deals["beliebt"] = [kurz(p) for p in kandidaten[:12]]
    with open(deals_pfad, "w", encoding="utf-8") as datei:
        datei.write(json.dumps(deals, ensure_ascii=False, indent=2) + "\n")
    print(f"daten: {len(nach_kategorie)} Kategorie-Dateien, {len(produkte)} Produkte im Index")
