"""
DealKira – Preise automatisch aktualisieren

Läuft alle 6 Stunden über GitHub Actions (.github/workflows/preise.yml).
Lädt die Awin-Produktfeeds und aktualisiert in produkte.json
Preis, Bild und Link aller Shops, die ein "feed" + "feedId" haben.

Feeds werden als GitHub-Secrets hinterlegt (nie im Code!):
  AWIN_FEED_AOSU     → Download-Link des aosu-Feeds
  AWIN_FEED_ANTHBOT  → Download-Link des Anthbot-Feeds
  AWIN_FEED_IMOU     → Download-Link des Imou-Feeds
  AWIN_FEED_NARWAL   → Download-Link des Narwal-Feeds
  AWIN_FEED_NOTEBOOKSBILLIGER → Download-Link des notebooksbilliger-Feeds
Ein neuer Marken-Feed: Secret anlegen und unten in FEEDS eintragen.

Händler-Feeds (HAENDLER_FEEDS, z. B. notebooksbilliger): Dort gibt es keine
feedId pro Produkt. Jedes Produkt aus produkte.json, telefone.json und
tablets.json wird automatisch über den Namen zugeordnet (gleiche strenge
Prüfung wie bei eBay: kein Zubehör, keine falschen Varianten). Fehlt einem
Produkt das Bild, wird das Händlerbild aus dem Feed übernommen.

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

# Wörter, die bei Händler-Feeds auf Zubehör oder etwas anderes als das Gerät hindeuten
# (zusätzlich zu den eBay-Regeln). Steht so ein Wort im Produktnamen selbst, ist es erlaubt.
HAENDLER_ZUBEHOER = {
    # Fremdzubehör fällt schon über die Marken-Regel raus; hier nur, was auch die Marke selbst
    # als Zubehör verkauft. Nicht "netzteil"/"glass"/"pen": stehen oft in Handy-Titeln
    # ("ohne Netzteil", "Gorilla Glass", "mit S Pen").
    "camglass", "glasschutzfolie", "schutzfolie", "displayschutzfolie", "displayschutz",
    "protector", "stylus", "earbuds", "kopfhörerkissen", "ohrpolster",
    "pc", "komplettsystem", "workstation", "barebone", "keyboard-case", "tastaturhülle",
    "dockingstation", "rucksack", "sleeve", "wallet", "flip-case", "bookcover", "schutzhülle",
    "linsenschutz",
}
# Preis muss zum Preis der anderen Shops passen (z. B. eBay), sonst ist es ein falscher Treffer
PREIS_SPANNE = (0.5, 2.0)

# Händler mit vielen Marken: Zuordnung automatisch über den Produktnamen
HAENDLER_FEEDS = {
    "nbb": {"secret": "AWIN_FEED_NOTEBOOKSBILLIGER", "shop": "notebooksbilliger.de"},
}

# Neue Produkte aus Händler-Feeds: Feed-Kategorie (merchant_category) → DealKira-Kategorie
# mit Mindestpreis (Zubehör fällt so raus). Pro Kategorie höchstens HAENDLER_IMPORT_ANZAHL
# importierte Produkte, höchstens 2 pro Marke. Importierte Produkte haben "importFeed"
# und werden danach über ihre feedId aktualisiert (nicht über den Namen).
HAENDLER_IMPORT = {
    "nbb": {
        "Notebooks": ("laptops", 300), "Displays": ("bildschirme", 100),
        "Headset": ("headset", 30), "Tastaturen": ("tastaturen", 30),
        "Mäuse": ("maeuse", 25), "Webcams": ("webcams", 30),
        "USB-Hubs": ("usb-hubs", 20), "Drucker": ("drucker", 80),
        "Solid-State-Drive": ("speicherplatten", 50), "Grafikkarten": ("grafikkarten", 200),
        "Prozessoren": ("cpu", 80), "Mainboards": ("mainboards", 80),
        "Arbeitsspeicher": ("ram", 40), "PC Netzteile": ("netzteile", 50),
        "Gehäuse": ("gehaeuse", 50), "Saugroboter": ("staubsauger", 150),
        # Smart Home: Kategorie hängt vom Titel ab (siehe smart_home_kategorie)
        "Netzwerk-Kamera": ("kamera", 30), "Heimautomatisierung": ("smarthome", 15),
    },
}
HAENDLER_IMPORT_ANZAHL = 6
HAENDLER_IMPORT_ANZAHL_KATEGORIE = {"heimautomatisierung": 12}

TUERKLINGEL = re.compile(r"türklingel|tuerklingel|doorbell|türsprechanlage", re.I)
KAMERA = re.compile(r"kamera|camera|\bcam\b|überwachung", re.I)
OUTDOOR = re.compile(r"outdoor|außen|aussen|wetterfest|\bip6[4-7]\b|bullet|flutlicht|floodlight|solar", re.I)


def smart_home_kategorie(art, titel):
    """Netzwerk-Kameras und Heimautomatisierung auf die Smart-Home-Unterseiten verteilen."""
    if TUERKLINGEL.search(titel):
        return "tuerklingeln"
    if art == "kamera" or KAMERA.search(titel):
        return "outdoor-kameras" if OUTDOOR.search(titel) else "indoor-kameras"
    return "heimautomatisierung"

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


def verfuegbar(zeile):
    """Google-Format: availability = in_stock; klassisches Format: in_stock = 1/0."""
    if "availability" in zeile:
        return zeile["availability"] in ("in_stock", "")
    if "in_stock" in zeile:
        return str(zeile["in_stock"]).strip().lower() in ("1", "yes", "true", "")
    return True


def ist_neuware(zeile):
    zustand = (zeile.get("condition") or "new").strip().lower()
    return zustand in ("new", "neu", "")


def feed_titel(zeile):
    return (zeile.get("title") or zeile.get("product_name") or "").strip()


def feed_preis(zeile):
    return preis_format(zeile.get("sale_price") or zeile.get("price") or zeile.get("search_price", ""))


def feed_bild(zeile):
    return (zeile.get("image_link") or zeile.get("merchant_image_url")
            or zeile.get("aw_image_url") or "").strip()


def streichpreis(zeile, preis):
    """Streichpreis des Shops: Google-Format "price" (wenn "sale_price" gesetzt),
    klassisches Format "product_price_old" bzw. "rrp_price" (UVP)."""
    if zeile.get("sale_price"):
        statt, art = preis_format(zeile.get("price", "")), "shop"
    elif preis_format(zeile.get("product_price_old", "")):
        statt, art = preis_format(zeile.get("product_price_old", "")), "shop"
    else:
        statt, art = preis_format(zeile.get("rrp_price", "")), "uvp"
    if not preis or not statt or (preis_zahl(statt) or 0) <= (preis_zahl(preis) or 0):
        return "", ""
    return statt, art


# Wörter, die eine andere Ausführung bedeuten – müssen in Name UND Titel stehen oder in keinem
HAENDLER_AUSFUEHRUNG = {"wifi", "ax", "rgb", "gre", "wireless"}

# Marke in unseren Dateien → Marke im Händler-Feed ("iPhone" heißt dort "Apple")
MARKEN_ALIAS = {"iphone": "apple", "google pixel": "google", "redmi": "xiaomi",
                "poco": "xiaomi", "cmf": "nothing"}

# Display-Angaben im Händler-Titel sind keine Modell-Varianten:
# "FHD+ Display" ≠ "Plus", "Super Retina XDR" ≠ "Super"
DISPLAY_ANGABEN = re.compile(r"\b((?:W?Q?X?GA|WUXGA|[FQWU]?HD|[0-9.,]+K))\+|\bsuper(?=[\s-]+(?:retina|amoled))",
                             re.I)


def ohne_display(titel):
    return DISPLAY_ANGABEN.sub(lambda t: t.group(1) or "", titel)


def feed_marke_passt(marke, feed_marke):
    marke = marke.lower()
    marke = MARKEN_ALIAS.get(marke, marke)
    return not marke or not feed_marke or marke in feed_marke or feed_marke in marke


# Handy-Titel im Händler-Feed, die keinem Handy zugeordnet wurden, kommen ins Log
# (der Feed selbst ist nur über das Secret erreichbar)
HANDY_ANFANG = re.compile(r"^(apple iphone|iphone|samsung galaxy (?!tab|watch|buds|book)|google pixel (?!watch|buds|tablet)"
                          r"|xiaomi|redmi|poco|motorola|oneplus (?!pad|buds|watch)|nothing phone|cmf phone|huawei (?:pura|nova|mate|p\d))",
                          re.I)


def haendler_passt(name, titel):
    """Zusätzliche Prüfungen für Händler-Feeds (strenger als eBay, weil dort
    jede Variante als eigenes Produkt im Feed steht)."""
    w = ebay_preise.woerter
    titel_l = w(titel)
    titel_s = set(titel_l)
    paare = set(zip(titel_l, titel_l[1:]))

    # Generation in Klammern: "iPad mini (6. Generation)" ≠ "7.Gen"
    gen = re.search(r"\((\d+)\.\s*gen", name, re.I)
    if gen:
        nr = gen.group(1)
        gefunden = set(re.findall(r"(\d+)\s*\.\s*gen", titel, re.I))
        if nr not in gefunden:
            return False
    name_l = w(ebay_preise.ohne_zusatz(name))
    name_s = set(w(name))

    # Steht es im Namen, muss es im Titel stehen. Steht es nur im Titel, zählt es erst,
    # wenn es vorne beim Modellnamen steht ("Vengeance RGB …", nicht "… 8-Zonen-RGB")
    for wort in HAENDLER_AUSFUEHRUNG:
        if wort in name_s and wort not in titel_s:
            return False
        if wort not in name_s and wort in titel_l[:6]:
            return False

    # Varianten-Zusatz muss direkt hinter demselben Wort stehen: "S10 FE+" ≠ "S10 FE … FE/+"
    for i in range(1, len(name_l)):
        if name_l[i] in ebay_preise.VARIANTEN and (name_l[i - 1].isdigit()
                                                    or name_l[i - 1] in ebay_preise.VARIANTEN) \
                and (name_l[i - 1], name_l[i]) not in paare:
            return False

    # "Gen 2" im Titel, aber nicht im Namen (außer "PCIe Gen4") → Nachfolgemodell
    for j in range(1, len(titel_l)):
        if titel_l[j - 1] == "gen" and titel_l[j].isdigit() and len(titel_l[j]) <= 2 \
                and "pcie" not in titel_l[max(0, j - 5):j] and "gen" not in name_s and not gen:
            return False

    for i, wort in enumerate(name_l):
        if not wort.isdigit() or i == 0:
            continue
        davor = name_l[i - 1]
        danach = name_l[i + 1] if i + 1 < len(name_l) else ""
        # Buchstaben-Zusatz hinter "Modell+Zahl" im Titel: V3 ≠ V3X, V4 ≠ V4 X
        if davor.isalpha():
            for j in range(1, len(titel_l) - 1):
                if (titel_l[j - 1], titel_l[j]) == (davor, wort):
                    zusatz = titel_l[j + 1]
                    if zusatz.isalpha() and len(zusatz) <= 2 and zusatz not in name_s \
                            and zusatz not in ebay_preise.MASS_EINHEITEN:
                        return False

        # Mengenangaben (2 TB, 65 W, 32 GB) und Marke + Zahl ("Samsung 990") zählen hier nicht
        if i == 1 or davor in ebay_preise.EINHEITEN or danach in ebay_preise.EINHEITEN:
            continue
        # "OmniBook 5" ≠ "OmniBook 3 … Ryzen 5": steht das Modellwort im Titel mit einer
        # ANDEREN Zahl dahinter, ist es ein anderes Modell
        if davor.isalpha() and davor not in ebay_preise.FUELLWOERTER and (davor, wort) not in paare \
                and any(a == davor and b.isdigit() and b != wort for a, b in paare):
            return False
    # Einzelbuchstaben hinter einer Modellnummer: B760M-A ≠ B760M-P
    for i, wort in enumerate(name_l):
        if len(wort) == 1 and wort.isalpha() and i >= 1 and (
                name_l[i - 1].isdigit()
                or (len(name_l[i - 1]) == 1 and i >= 2 and name_l[i - 2].isdigit())):
            if wort not in titel_s:
                return False

    # Modellwörter ab 4 Buchstaben müssen im Titel stehen (Dual Drive ≠ Typ-A)
    for wort in name_l[1:]:
        if len(wort) >= 4 and wort.isalpha() and wort not in ebay_preise.FUELLWOERTER \
                and wort not in titel_s and wort + "s" not in titel_s \
                and wort not in {"generation", "gaming", "edition"}:
            return False
    return True


# Hier endet der Modellname in Händler-Titeln: "ASUS Vivobook 15 X1504VA / 15,6\" FHD / …"
NAME_ENDE = re.compile(r"\s+[-–|/]\s|/\s|,|\(|\s\d+(?:[.,]\d+)?\s*(?:\"|zoll|cm\b)"
                       r"|\s(?:grafikkarte|gaming-monitor|monitor|notebook|laptop|prozessor|mainboard|"
                       r"arbeitsspeicher|netzteil|gehäuse|tastatur|maus|headset|webcam|drucker|"
                       r"saugroboter|saug-|interne|externe|ssd\b|(?:wlan-|wifi-)?(?:überwachungs)?kamera\b|camera\b)", re.I)


def haendler_modellname(titel):
    """"MSI GeForce RTX 5070 Ti 16G Gaming Trio OC Grafikkarte, PCIe 5.0" → "MSI GeForce RTX 5070 Ti 16G Gaming Trio OC" """
    name = NAME_ENDE.split(titel.strip(), maxsplit=1)[0].strip(" -–")
    woerter = name.split()[:8]
    while woerter and woerter[-1].lower() in {"gaming", "-"}:
        woerter.pop()
    return " ".join(woerter) if len(woerter) >= 2 else ""


def haendler_marke(titel):
    marke = titel.split()[0] if titel.split() else ""
    # "SAMSUNG" → "Samsung", Abkürzungen wie "ASUS", "MSI", "LG" bleiben
    return marke.capitalize() if marke.isupper() and len(marke) > 4 else marke


def haendler_import(produkte, feed_name, feed, shop_name, regeln):
    """Legt pro Kategorie ein paar neue Produkte aus dem Händler-Feed an (mit Bild)."""
    vorhandene_ids = {p["id"] for p in produkte}
    importiert = {}
    for p in produkte:
        if p.get("importFeed") == feed_name:
            importiert[p.get("kategorie")] = importiert.get(p.get("kategorie"), 0) + 1
    bekannte_ids = {s.get("feedId") for p in produkte for s in p.get("shops", [])
                    if s.get("feed") == feed_name}

    kandidaten = {}
    for feed_id, zeile in feed.items():
        regel = regeln.get((zeile.get("merchant_category") or "").strip())
        if not regel or feed_id in bekannte_ids or not verfuegbar(zeile) or not ist_neuware(zeile):
            continue
        titel, preis, bild = feed_titel(zeile), feed_preis(zeile), feed_bild(zeile)
        link = zeile.get("aw_deep_link") or zeile.get("link") or ""
        if not titel or not preis or not bild or not link or (preis_zahl(preis) or 0) < regel[1]:
            continue
        titel_w = set(ebay_preise.woerter(titel)) | set(re.findall(r"[a-zäöüß-]+", titel.lower()))
        if titel_w & (HAENDLER_ZUBEHOER | ebay_preise.ZUBEHOER):
            continue
        name = haendler_modellname(titel)
        if not name:
            continue
        kategorie = regel[0]
        if kategorie in ("kamera", "smarthome"):
            kategorie = smart_home_kategorie(kategorie, titel)
        kandidaten.setdefault(kategorie, []).append((name, titel, preis, bild, link, feed_id, zeile))

    neu = 0
    for kategorie, liste in sorted(kandidaten.items()):
        frei = HAENDLER_IMPORT_ANZAHL_KATEGORIE.get(kategorie, HAENDLER_IMPORT_ANZAHL) \
            - importiert.get(kategorie, 0)
        if frei <= 0:
            continue
        vorhanden = [p for p in produkte if p.get("kategorie") == kategorie]
        namen = {p["name"].lower() for p in vorhanden}
        marken_anzahl = {}
        for p in vorhanden:
            if p.get("importFeed") == feed_name:
                marken_anzahl[p.get("brand", "").lower()] = marken_anzahl.get(p.get("brand", "").lower(), 0) + 1
        # Marken, die im Feed oft vorkommen, zuerst; je Marke ein Gerät aus der Preismitte
        haeufig = {}
        for eintrag in liste:
            haeufig[haendler_marke(eintrag[1]).lower()] = haeufig.get(haendler_marke(eintrag[1]).lower(), 0) + 1
        preise = sorted(preis_zahl(e[2]) for e in liste)
        mitte = preise[len(preise) // 2]
        liste.sort(key=lambda e: (-haeufig[haendler_marke(e[1]).lower()], abs(preis_zahl(e[2]) - mitte), e[5]))
        for name, titel, preis, bild, link, feed_id, zeile in liste:
            if frei <= 0:
                break
            marke = haendler_marke(titel)
            if name.lower() in namen or marken_anzahl.get(marke.lower(), 0) >= 2:
                continue
            # gibt es das Gerät schon (z. B. mit anderem Namen)?
            if any(ebay_preise.passt(p["name"], titel) for p in vorhanden):
                continue
            pid = slug(name)
            while pid in vorhandene_ids:
                pid += "-2"
            vorhandene_ids.add(pid)
            shop = {"name": shop_name, "price": preis, "link": link,
                    "feed": feed_name, "feedId": feed_id, "feedTitel": titel[:120]}
            statt, statt_art = streichpreis(zeile, preis)
            if statt:
                shop["statt"], shop["stattArt"] = statt, statt_art
            name = re.sub(r"^\S+", marke, name)
            produkt = {"id": pid, "name": name, "brand": marke, "kategorie": kategorie,
                       "image": bild, "imageFeed": feed_name, "importFeed": feed_name, "shops": [shop]}
            produkte.append(produkt)
            vorhanden.append(produkt)
            namen.add(name.lower())
            marken_anzahl[marke.lower()] = marken_anzahl.get(marke.lower(), 0) + 1
            frei -= 1
            neu += 1
            print(f"  {feed_name}: NEU angelegt in {kategorie}: {name} ({preis})")
    print(f"{feed_name}: {neu} neue Produkte angelegt")
    return neu


def haendler_import_aktualisieren(produkte, feed_name, feed):
    """Importierte Produkte über ihre feedId aktualisieren; nicht mehr im Feed → entfernen."""
    aenderungen = 0
    for produkt in list(produkte):
        if produkt.get("importFeed") != feed_name:
            continue
        shop = next((s for s in produkt.get("shops", []) if s.get("feed") == feed_name), None)
        zeile = feed.get(shop.get("feedId", "")) if shop else None
        if not zeile:
            produkte.remove(produkt)
            print(f"  {feed_name}: nicht mehr im Feed, entfernt: {produkt['name']}")
            aenderungen += 1
            continue
        preis = feed_preis(zeile) if verfuegbar(zeile) else ""
        statt, statt_art = streichpreis(zeile, preis)
        neu = dict(shop, price=preis, link=zeile.get("aw_deep_link") or shop.get("link", ""))
        neu.pop("statt", None)
        neu.pop("stattArt", None)
        if statt:
            neu["statt"], neu["stattArt"] = statt, statt_art
        if neu != shop:
            produkt["shops"][produkt["shops"].index(shop)] = neu
            aenderungen += 1
        bild = feed_bild(zeile)
        if bild and produkt.get("image") != bild:
            produkt["image"] = bild
            aenderungen += 1
    return aenderungen


def haendler_abgleich(dateien, feed_name, feed, shop_name):
    """Ordnet die Produkte aller Dateien einem Händler-Feed zu (über den Namen).
    Pro Produkt gewinnt das günstigste passende, lieferbare Neuware-Angebot."""
    # Index: Wort → Feed-Zeilen, damit nicht jedes Produkt den ganzen Feed prüfen muss
    zeilen = []
    index = {}
    for feed_id, zeile in feed.items():
        if not verfuegbar(zeile) or not ist_neuware(zeile):
            continue
        titel = feed_titel(zeile)
        preis = feed_preis(zeile)
        link = zeile.get("aw_deep_link") or zeile.get("link") or ""
        if not titel or not preis or not link:
            continue
        nr = len(zeilen)
        marke = (zeile.get("brand_name") or zeile.get("brand") or "").strip().lower()
        zeilen.append((feed_id, zeile, titel, preis, link, marke))
        for wort in set(ebay_preise.woerter(titel)):
            index.setdefault(wort, []).append(nr)

    aenderungen = 0
    gefunden = 0
    benutzt = set()
    for produkte in dateien.values():
        for produkt in produkte:
            name = produkt.get("name", "")
            marke = produkt.get("brand", "")
            if not name or produkt.get("importFeed") == feed_name:
                continue
            voller_name = name if marke.lower() in name.lower() else f"{marke} {name}".strip()
            # seltenstes Wort des Namens als Vorfilter (Marke zählt nicht: "Nvidia" steht
            # bei Grafikkarten oft nicht im Titel, dafür "MSI GeForce …")
            name_woerter = [w for w in ebay_preise.woerter(ebay_preise.ohne_zusatz(name))
                            if w not in ebay_preise.FUELLWOERTER]
            listen = [index.get(w, []) for w in name_woerter]
            kandidaten_nr = min(listen, key=len) if name_woerter and all(listen) else []

            name_set = set(ebay_preise.woerter(voller_name))
            # Marke oder erstes Wort des Namens (z. B. "GeForce") muss ganz vorne im Titel stehen:
            # "DISPLEX Schutzglas für Samsung Galaxy S25" ist kein Samsung-Handy
            vorne_erlaubt = set(ebay_preise.woerter(marke)[:1]) | set(ebay_preise.woerter(name)[:1])
            # Vergleichspreis der anderen Shops (ohne diesen Händler)
            andere = [preis_zahl(s.get("price", "")) for s in produkt.get("shops", [])
                      if s.get("feed") != feed_name]
            andere = [x for x in andere if x]
            referenz = min(andere) if andere else None

            bestes = None
            for nr in kandidaten_nr:
                feed_id, zeile, titel, preis, link, feed_marke = zeilen[nr]
                if not feed_marke_passt(marke, feed_marke):
                    continue
                titel_w = ebay_preise.woerter(titel)
                if not vorne_erlaubt & set(titel_w[:3]):
                    continue
                if any(w in HAENDLER_ZUBEHOER and w not in name_set for w in titel_w) \
                        or any(w in HAENDLER_ZUBEHOER and w not in name_set
                               for w in re.findall(r"[a-zäöüß-]+", titel.lower())):
                    continue
                if referenz and not (PREIS_SPANNE[0] * referenz <= preis_zahl(preis)
                                     <= PREIS_SPANNE[1] * referenz):
                    continue
                pruef_titel = ohne_display(titel)
                if not ebay_preise.passt(name, pruef_titel) or not haendler_passt(name, pruef_titel):
                    continue
                if bestes is None or preis_zahl(preis) < preis_zahl(bestes[3]):
                    bestes = zeilen[nr]

            shops = produkt.setdefault("shops", [])
            alt = next((s for s in shops if s.get("feed") == feed_name), None)
            if not bestes:
                if alt:
                    shops.remove(alt)
                    print(f"  {feed_name}: nicht mehr gefunden: {name}")
                    aenderungen += 1
                # Bild stammte von diesem Händler → mit entfernen
                if produkt.get("imageFeed") == feed_name:
                    produkt["image"] = ""
                    del produkt["imageFeed"]
                    aenderungen += 1
                continue

            gefunden += 1
            feed_id, zeile, titel, preis, link, _ = bestes
            benutzt.add(feed_id)
            statt, statt_art = streichpreis(zeile, preis)
            neu = {"name": shop_name, "price": preis, "link": link,
                   "feed": feed_name, "feedId": feed_id, "feedTitel": titel[:120]}
            if statt:
                neu["statt"], neu["stattArt"] = statt, statt_art
            if alt != neu:
                if alt:
                    shops[shops.index(alt)] = neu
                else:
                    shops.append(neu)
                    print(f"  {feed_name}: NEU zugeordnet: {name} → {titel[:70]} ({preis})")
                aenderungen += 1

            # Händlerbild nur, wenn das Produkt kein eigenes Bild hat (oder es schon von hier kam)
            bild = feed_bild(zeile)
            if bild and (not produkt.get("image") or produkt.get("imageFeed") == feed_name) \
                    and produkt.get("image") != bild:
                produkt["image"] = bild
                produkt["imageFeed"] = feed_name
                aenderungen += 1

    print(f"{feed_name}: {gefunden} Produkte mit passendem Angebot, {aenderungen} Änderungen")
    handys = sorted({titel for feed_id, _, titel, preis, _, _ in zeilen
                     if feed_id not in benutzt and HANDY_ANFANG.match(titel)
                     and (preis_zahl(preis) or 0) >= 100})
    if handys:
        print(f"{feed_name}: {len(handys)} Handy-Titel ohne Zuordnung, z. B.:")
        for titel in handys[:60]:
            print(f"    {titel[:140]}")
    return aenderungen


def main():
    produkte = json.load(open(DATEI, encoding="utf-8"))
    dateien = {DATEI: produkte}
    for name in WEITERE_DATEIEN:
        dateien[name] = json.load(open(name, encoding="utf-8"))
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

    # Händler-Feeds (z. B. notebooksbilliger): alle drei Produktdateien, Zuordnung über den Namen
    for feed_name, info in HAENDLER_FEEDS.items():
        url = os.environ.get(info["secret"], "").strip()
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
        geaendert += haendler_abgleich(dateien, feed_name, feed, info["shop"])
        geaendert += haendler_import_aktualisieren(produkte, feed_name, feed)
        if feed_name in HAENDLER_IMPORT:
            geaendert += haendler_import(produkte, feed_name, feed, info["shop"], HAENDLER_IMPORT[feed_name])

    # eBay: alle drei Produktdateien
    ebay_aenderungen, ebay_fehler = ebay_preise.aktualisieren(dateien)
    fehler_gesamt += ebay_fehler

    geaendert_vor_ebay = geaendert
    if geaendert_vor_ebay or ebay_aenderungen:
        for name, liste in dateien.items():
            with open(name, "w", encoding="utf-8") as datei:
                datei.write(json.dumps(liste, ensure_ascii=False, indent=2) + "\n")
    geaendert += ebay_aenderungen

    historie_und_deals([p for liste in dateien.values() for p in liste])
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
            if shop.get("feed") in HAENDLER_FEEDS:
                # automatisch zugeordnet: wechselt das Angebot (z. B. andere Speichergröße),
                # beginnt ein neuer Preisverlauf – sonst entstünden falsche Deals
                schluessel += "|" + shop.get("feedId", "")
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
