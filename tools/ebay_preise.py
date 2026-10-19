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

# Wörter, die auf ein anderes Modell hindeuten, wenn sie nicht im Produktnamen stehen
VARIANTEN = {
    "pro", "max", "plus", "ultra", "mini", "lite", "ti", "xt", "xtx", "super",
    "fe", "se", "air", "neo", "edge", "fold", "flip",
}
# Wörter, die auf Zubehör, Ersatzteile oder Ware mit Mängeln hindeuten
ZUBEHOER = {
    "hülle", "huelle", "case", "cover", "folie", "schutzfolie", "panzerglas",
    "schutzglas", "displayschutz", "tasche", "bumper", "ersatzteil", "ersatz",
    "defekt", "attrappe", "dummy", "halterung", "aufkleber", "skin", "sticker",
    "gebraucht", "refurbished", "generalüberholt", "bware",
    "leerkarton", "kaputt", "bastler",
}
# "Hülle FÜR iPhone 17": steht so ein Wort VOR der Modellnummer, ist es Zubehör.
# ("Mähroboter M5 für 500 m²" ist dagegen in Ordnung.)
PASSEND_FUER = {"für", "fuer", "for", "kompatibel", "compatible", "passend"}
EINHEITEN = {"g", "gb", "tb", "w", "mah", "hz", "mm", "cm", "m", "zoll", "l", "v", "a", "kg"}
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

    zahlen = [w for w in name_w if w.isdigit()]
    if any(z not in titel_w for z in zahlen):
        return False

    # Kurze Zusätze direkt hinter einer Zahl gehören zum Modell (14400F, S23+, 9070 XT)
    for i in range(1, len(name_w)):
        wort = name_w[i]
        if name_w[i - 1].isdigit() and not wort.isdigit() and wort not in EINHEITEN \
                and (len(wort) <= 3 or wort in VARIANTEN) and wort not in titel_w:
            return False

    if zahlen:
        erste_zahl = min(titel_liste.index(z) for z in zahlen)
        if any(w in PASSEND_FUER and w not in name_set for w in titel_liste[:erste_zahl]):
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


def suchen(token, suchtext):
    parameter = urllib.parse.urlencode({
        "q": suchtext[:100],
        "limit": "50",
        "filter": "buyingOptions:{FIXED_PRICE},conditions:{NEW},"
                  "itemLocationCountry:DE,deliveryCountry:DE,priceCurrency:EUR",
    })
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


def bestes_angebot(name, artikel_liste):
    kandidaten = []
    for artikel in artikel_liste:
        titel = artikel.get("title", "")
        if not passt(name, titel):
            continue
        preis = gesamtpreis(artikel)
        link = artikel.get("itemAffiliateWebUrl") or ""
        if not preis or not link:
            continue
        kandidaten.append((preis, link, artikel.get("itemId", ""), titel))
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

            try:
                angebot = bestes_angebot(name, suchen(token, suchtext))
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
            preis, link, item_id, titel = angebot
            neu = {"name": SHOP_NAME, "price": preis_text(preis), "link": link,
                   "feed": "ebay", "ebayItem": item_id, "ebayTitel": titel[:120]}
            if alt != neu:
                if alt:
                    shops[shops.index(alt)] = neu
                else:
                    shops.append(neu)
                aenderungen += 1

        print(f"ebay: {dateiname} durchsucht")

    print(f"ebay: {gefunden} Produkte mit passendem Angebot, {aenderungen} Änderungen")
    return aenderungen, 0
