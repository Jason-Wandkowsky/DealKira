"""
DealKira – eBay-Preise über die eBay Browse API

Wird von preise_aktualisieren.py aufgerufen. Sucht für jedes Produkt das
günstigste passende Angebot auf eBay.de:
  - nur Neuware, nur Sofort-Kaufen (keine Auktionen)
  - nur Artikel aus Deutschland, Preis inklusive Versand
  - Titel muss zum Produkt passen (Modellnummern, keine Hüllen/Zubehör,
    kein "Pro"/"Max"/"Ti", wenn das Produkt das nicht hat)
Gefundene Angebote kommen als Shop "eBay" (feed "ebay") ins Produkt,
der Link ist automatisch der eBay-Partnerlink. Ohne passendes Angebot
wird die eBay-Zeile wieder entfernt.

GitHub-Secrets (nie im Code!):
  EBAY_CLIENT_ID      → App ID (Client ID) vom eBay-Developer-Account
  EBAY_CLIENT_SECRET  → Cert ID (Client Secret)
Bilder werden NICHT von eBay übernommen (Händlerfotos).
"""

import base64
import json
import os
import re
import statistics
import urllib.parse
import urllib.request

CAMPAIGN_ID = "5339218072"   # eBay Partner Network – steht ohnehin in jedem Partnerlink
MARKTPLATZ = "EBAY_DE"
SHOP_NAME = "eBay"

# Erlaubte eBay-Kategorien je DealKira-Kategorie (IDs aus eBay.de; Oberkategorien zählen mit,
# weil eBay bei jedem Treffer auch die übergeordneten Kategorien mitliefert).
# Steht eine Kategorie hier nicht drin (Kabel, Zubehör …), wird nicht nach Kategorie gefiltert.
EBAY_KATEGORIEN = {
    "telefone": {"9355"},                       # Handys & Smartphones
    "tablets": {"171485"},                      # Tablets & eBook-Reader
    "laptops": {"175672"},                      # Notebooks & Netbooks
    "bildschirme": {"80053"},                   # Monitore
    "maeuse": {"23160"},
    "tastaturen": {"33963"},
    "headset": {"80183", "171821"},
    "mikrofon": {"116309", "29946"},
    "speicherplatten": {"182085"},              # Festplatten (HDD, SSD & NAS)
    "grafikkarten": {"27386"},
    "cpu": {"164"},
    "mainboards": {"1244"},
    "ram": {"170083"},
    "netzteile": {"42017"},
    "gehaeuse": {"42014"},
    "cpu-kuehler": {"131486"},
    "wasserkuehlung": {"131503"},
    "luefter": {"131487"},
    "webcams": {"4616"},
    "usb-hubs": {"44932"},
    "drucker": {"1245"},
    "outdoor-kameras": {"48638", "185053"},
    "indoor-kameras": {"48638", "185053"},
    "kamera-sets": {"48638", "185053"},
    "tuerklingeln": {"185055", "115975"},
    "maehroboter": {"260921"},
    "kuehlschraenke": {"71258"},
    "gefrierschraenke": {"71258"},
    "waschmaschinen": {"42231"},
    "trockner": {"42231"},
    "waschtrockner": {"42231"},
    "spuelmaschinen": {"260307"},
    "staubsauger": {"20614"},
    "ofen": {"71318"},
    "kochfelder": {"71246"},
    "abzugshauben": {"71253"},
    "klimaanlagen": {"185107"},
    "mobile-heizungen": {"20613"},
    "ventilatoren": {"20612"},
}
DATEI_KATEGORIE = {"telefone.json": "telefone", "tablets.json": "tablets"}

# Wörter, die auf ein anderes Modell hindeuten, wenn sie nicht im Produktnamen stehen
VARIANTEN = {
    "pro", "max", "plus", "ultra", "mini", "lite", "ti", "xt", "xtx", "super",
    "fe", "se", "air", "neo", "edge", "fold", "flip", "note", "redmi", "poco", "kids",
    "xl", "fusion", "nord", "loq",
}
# Wörter, die auf Zubehör, Ersatzteile oder Ware mit Mängeln hindeuten
ZUBEHOER = {
    "hülle", "huelle", "case", "cover", "folie", "schutzfolie", "panzerglas",
    "schutzglas", "displayschutz", "tasche", "bumper", "ersatzteil", "ersatz",
    "defekt", "attrappe", "dummy", "halterung", "aufkleber", "skin", "sticker",
    "gebraucht", "refurbished", "generalüberholt", "bware",
    "leerkarton", "kaputt", "bastler", "ghosting", "reparatur", "repair", "mod",
    "mikrofonarm", "popschutz", "ständer", "staender",
}
# "Hülle FÜR iPhone 17": steht so ein Wort VOR der Modellnummer, ist es Zubehör.
# ("Mähroboter M5 für 500 m²" ist dagegen in Ordnung.)
PASSEND_FUER = {"für", "fuer", "for", "kompatibel", "compatible", "passend"}
EINHEITEN = {"g", "gb", "tb", "w", "mah", "hz", "mm", "cm", "m", "zoll", "l", "v", "a", "kg"}
SPEICHER = {"g", "gb", "tb"}
# Einheiten, die direkt hinter einer Zahl stehen dürfen (ohne a/m/v/l: das sind oft Modell-Zusätze)
MASS_EINHEITEN = {"g", "gb", "tb", "w", "mah", "hz", "mm", "cm", "kg"}
OHNE_PFLICHT = {
    "apple", "samsung", "google", "xiaomi", "geforce", "radeon", "nvidia", "intel",
    "galaxy", "iphone", "generation", "kabel", "kameras", "karte", "speicherkarte",
    "schnellladegerät", "ladegerät", "netzteil", "powerbank", "power", "bank", "drive",
    "solarpanel", "microsdxc", "microsd", "extreme", "portable", "mobile", "solarcam",
}
FUELLWOERTER = {"und", "mit", "der", "die", "das", "von", "in", "the", "and", "with", "-", "/"}


def woerter(text):
    """Kleinbuchstaben, '+' → plus, Buchstaben/Zahlen trennen (rtx5070 → rtx 5070)."""
    text = text.lower().replace("+", " plus ")
    text = re.sub(r"[^0-9a-zäöüß]+", " ", text)
    text = re.sub(r"(?<=[a-zäöüß])(?=\d)|(?<=\d)(?=[a-zäöüß])", " ", text)
    return [w for w in text.split() if w]


def passt(name, titel):
    """Prüft, ob ein eBay-Titel wirklich zum Produktnamen gehört."""
    name_w = woerter(name)
    titel_liste = woerter(titel)
    titel_w = set(titel_liste)
    name_set = set(name_w)

    for wort in titel_w:
        if wort in ZUBEHOER and wort not in name_set:
            return False
        if wort in VARIANTEN and wort not in name_set:
            return False

    # Varianten aus dem Namen müssen auch im Titel stehen (Phone 3a Pro ≠ Phone 3a)
    for wort in name_set:
        if wort in VARIANTEN and wort not in titel_w:
            return False

    zahlen = [w for w in name_w if w.isdigit()]

    modellzahlen = {name_w[k] for k in range(1, len(name_w))
                    if name_w[k].isdigit() and name_w[k - 1].isalpha()
                    and name_w[k - 1] not in EINHEITEN}

    def zahl_im_titel(z):
        # Modellnummer zählt nicht, wenn sie im Titel nur als "16 GB" vorkommt (iPhone 6s Plus 16GB)
        speicher_im_namen = {name_w[k + 1] for k in range(len(name_w) - 1) if name_w[k] == z} & SPEICHER
        if speicher_im_namen:
            # Speichergröße muss als Speichergröße im Titel stehen (2 TB ≠ "M.2")
            return any(titel_liste[j] == z and j + 1 < len(titel_liste) and titel_liste[j + 1] in SPEICHER
                       for j in range(len(titel_liste)))
        if z not in modellzahlen:
            return z in titel_w
        einheit_im_namen = {name_w[k + 1] for k in range(len(name_w) - 1) if name_w[k] == z}
        for j, w in enumerate(titel_liste):
            if w != z:
                continue
            danach = titel_liste[j + 1] if j + 1 < len(titel_liste) else ""
            if danach not in SPEICHER or einheit_im_namen & SPEICHER:
                return True
        return False

    if any(not zahl_im_titel(z) for z in zahlen):
        return False



    # Kurze Zusätze direkt hinter einer Zahl gehören zum Modell (14400F, S23+, 9070 XT)
    for i in range(1, len(name_w)):
        wort = name_w[i]
        if name_w[i - 1].isdigit() and not wort.isdigit() and wort not in MASS_EINHEITEN \
                and (len(wort) <= 3 or wort in VARIANTEN) and wort not in titel_w:
            return False

    for i, wort in enumerate(name_w):
        if not wort.isdigit() or i == 0:
            continue
        davor = name_w[i - 1]
        # Kurzes Modell-Kürzel vor der Zahl muss im Titel direkt davor stehen
        # (Flip 6 ≠ Flip 3, Pad 8 ≠ Pad 7, S 25 …)
        danach = name_w[i + 1] if i + 1 < len(name_w) else ""
        davor2 = name_w[i - 2] if i >= 2 else ""
        if davor.isalpha() and len(davor) <= 4 and davor not in FUELLWOERTER \
                and davor not in EINHEITEN and danach not in EINHEITEN and not davor2.isdigit():
            paare = {(titel_liste[j - 1], titel_liste[j]) for j in range(1, len(titel_liste))}
            if (davor, wort) not in paare:
                return False

    # Buchstaben-Zusatz direkt hinter einer Modellzahl, der im Namen fehlt:
    # iPhone 16 ≠ 16e, Pixel 10 ≠ 10a, B650 ≠ B650M, Xiaomi 15 ≠ 15T
    for j in range(len(titel_liste) - 1):
        zahl, zusatz = titel_liste[j], titel_liste[j + 1]
        if zahl in modellzahlen and zusatz.isalpha() and len(zusatz) <= 2 \
                and zusatz not in name_set and zusatz not in MASS_EINHEITEN:
            nach_name = [name_w[k + 1] for k in range(len(name_w) - 1) if name_w[k] == zahl]
            if zusatz not in nach_name:
                return False

    # "Hülle FÜR iPhone 17", "Adapter für DJI Mic Mini": steht so ein Wort vor dem
    # Produkt (erste Modellzahl bzw. erstes Wort des Namens), ist es Zubehör.
    positionen = [titel_liste.index(z) for z in zahlen if z in titel_liste]
    if not positionen:
        positionen = [titel_liste.index(w) for w in name_w if w in titel_liste]
    if positionen:
        if any(w in PASSEND_FUER and w not in name_set for w in titel_liste[:min(positionen)]):
            return False

    # Längere Modellwörter müssen alle im Titel stehen (Straight Power ≠ Dark Power).
    # Ausgenommen: Herstellernamen, Allerweltswörter und Zusätze in Klammern.
    kern = woerter(re.sub(r"\(.*?\)", " ", name))
    if any(len(w) >= 5 and w.isalpha() and w not in titel_w and w not in OHNE_PFLICHT
           for w in kern[1:]):
        return False

    rest = [w for w in name_w if not w.isdigit() and w not in FUELLWOERTER and len(w) > 1]
    if rest:
        treffer = sum(1 for w in rest if w in titel_w)
        # mit Modellnummer reicht die Hälfte der übrigen Wörter, sonst 80 %
        noetig = 0.5 if zahlen else 0.8
        if treffer / len(rest) < noetig:
            return False
    return True


def token_holen(client_id, client_secret):
    daten = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }).encode()
    login = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    anfrage = urllib.request.Request(
        "https://api.ebay.com/identity/v1/oauth2/token",
        data=daten,
        headers={
            "Authorization": "Basic " + login,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        return json.load(antwort)["access_token"]


def suchen(token, suchtext, kategorien=None):
    werte = {
        "q": suchtext[:100],
        "limit": "50",
        "filter": "buyingOptions:{FIXED_PRICE},conditions:{NEW},"
                  "itemLocationCountry:DE,deliveryCountry:DE,priceCurrency:EUR",
    }
    if kategorien and len(kategorien) == 1:
        werte["category_ids"] = next(iter(kategorien))
    parameter = urllib.parse.urlencode(werte)
    anfrage = urllib.request.Request(
        "https://api.ebay.com/buy/browse/v1/item_summary/search?" + parameter,
        headers={
            "Authorization": "Bearer " + token,
            "X-EBAY-C-MARKETPLACE-ID": MARKTPLATZ,
            "X-EBAY-C-ENDUSERCTX":
                f"affiliateCampaignId={CAMPAIGN_ID},contextualLocation=country%3DDE",
            "Accept-Language": "de-DE",
        },
    )
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        return json.load(antwort).get("itemSummaries", [])


def gesamtpreis(artikel):
    try:
        preis = float(artikel["price"]["value"])
    except (KeyError, TypeError, ValueError):
        return None
    versand = 0.0
    optionen = artikel.get("shippingOptions") or []
    if optionen:
        try:
            versand = float(optionen[0].get("shippingCost", {}).get("value", 0) or 0)
        except (TypeError, ValueError):
            versand = 0.0
    return preis + versand


def bestes_angebot(name, artikel_liste, kategorien=None):
    kandidaten = []
    for artikel in artikel_liste:
        titel = artikel.get("title", "")
        if not passt(name, titel):
            continue
        if kategorien:
            ids = {str(k.get("categoryId")) for k in artikel.get("categories") or []}
            if not ids & kategorien:
                continue
        preis = gesamtpreis(artikel)
        link = artikel.get("itemAffiliateWebUrl") or ""
        if not preis or not link:
            continue
        kat = ",".join(f'{k.get("categoryId")}:{k.get("categoryName","")}' for k in artikel.get("categories") or [])
        kandidaten.append((preis, link, artikel.get("itemId", ""), titel, kat))
    if not kandidaten:
        return None
    # Ausreißer nach unten (Lockangebote, falsch eingestellte Artikel) aussortieren
    mitte = statistics.median(k[0] for k in kandidaten)
    kandidaten = [k for k in kandidaten if k[0] >= mitte * 0.6]
    return min(kandidaten)


def preis_text(wert):
    return f"{wert:.2f}".replace(".", ",") + " €"


def aktualisieren(dateien):
    """dateien: {Dateiname: Produktliste}. Gibt (Änderungen, Fehler) zurück."""
    client_id = os.environ.get("EBAY_CLIENT_ID", "").strip()
    client_secret = os.environ.get("EBAY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        print("ebay: keine API-Schlüssel hinterlegt – übersprungen")
        return 0, 0

    try:
        token = token_holen(client_id, client_secret)
    except Exception as fehler:
        details = ""
        if hasattr(fehler, "read"):
            try:
                details = " – " + fehler.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
        # "::error::" macht die Meldung bei GitHub direkt in der Übersicht sichtbar
        print(f"::error::ebay: Anmeldung fehlgeschlagen ({fehler}){details}")
        return 0, 1

    aenderungen = 0
    gefunden = 0
    fehler_anzahl = 0

    for dateiname, produkte in dateien.items():
        for produkt in produkte:
            name = produkt.get("name", "")
            if not name:
                continue
            marke = produkt.get("brand", "")
            suchtext = name if marke.lower() in name.lower() else f"{marke} {name}".strip()

            kategorien = EBAY_KATEGORIEN.get(
                DATEI_KATEGORIE.get(dateiname) or produkt.get("kategorie", ""))
            try:
                angebot = bestes_angebot(name, suchen(token, suchtext, kategorien), kategorien)
            except Exception as fehler:
                fehler_anzahl += 1
                print(f"  ebay-Fehler bei {name}: {fehler}")
                if fehler_anzahl >= 20:
                    print("ebay: zu viele Fehler – Abbruch")
                    return aenderungen, 1
                continue

            shops = produkt.setdefault("shops", [])
            alt = next((s for s in shops if s.get("feed") == "ebay"), None)

            if not angebot:
                if alt:
                    shops.remove(alt)
                    aenderungen += 1
                continue

            gefunden += 1
            preis, link, item_id, titel, kat = angebot
            neu = {"name": SHOP_NAME, "price": preis_text(preis), "link": link,
                   "feed": "ebay", "ebayItem": item_id, "ebayTitel": titel[:120], "ebayKat": kat[:200]}
            if alt != neu:
                if alt:
                    shops[shops.index(alt)] = neu
                else:
                    shops.append(neu)
                aenderungen += 1

        print(f"ebay: {dateiname} durchsucht")

    print(f"ebay: {gefunden} Produkte mit passendem Angebot, {aenderungen} Änderungen")
    return aenderungen, 0
