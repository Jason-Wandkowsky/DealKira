"""
DealKira – notebooksbilliger-Feed in DealKira-Kategorien einsortieren

Der nbb-Feed hat eine Spalte "merchant_category" (z. B. "Notebooks", "Kühlung",
"Kabel"). Hier steht, in welche DealKira-Kategorie ein Produkt kommt. Wo eine
nbb-Kategorie mehrere DealKira-Kategorien abdeckt (Kühlung → CPU-Kühler, Lüfter,
Wasserkühlung), entscheiden Wörter im Produkttitel.

Kategorie "tablets" landet in tablets.json, alles andere in produkte.json.
"""

import re


def _r(muster):
    return re.compile(muster, re.I)


TUERKLINGEL = _r(r"türklingel|tuerklingel|doorbell|türsprechanlage")
KAMERA = _r(r"kamera|camera|\bcam\b|überwachung")
OUTDOOR = _r(r"outdoor|außen|aussen|wetterfest|\bip6[4-7]\b|bullet|flutlicht|floodlight|solar")


def smart_home(titel, ist_kamera=False):
    if TUERKLINGEL.search(titel):
        return "tuerklingeln"
    if ist_kamera or KAMERA.search(titel):
        return "outdoor-kameras" if OUTDOOR.search(titel) else "indoor-kameras"
    return "heimautomatisierung"


HANDY = _r(r"iphone|galaxy [asz]\d|galaxy z|pixel \d|smartphone|handy")
WASSER = _r(r"\baio\b|wasserkühl|wasserkuehl|liquid|flüssigkeitsk|radiator|pumpe|reservoir|"
            r"ausgleichsbehälter|kühlblock|waterblock|wasserblock|fitting|schlauch|kühlflüssig")
CPU_KUEHLER = _r(r"cpu|prozessor|kühler|cooler|wärmeleit|waermeleit|thermal|paste|pad\b")
LUEFTER = _r(r"lüfter|luefter|\bfans?\b|ventilator")
KABEL_NETZWERK = _r(r"\bcat\s?\.?\d|patch|\blan\b|netzwerk|rj-?45|ethernet|glasfaser|\blwl\b")
KABEL_KOMPONENTEN = _r(r"\bsata\b|molex|pcie|pci-e|\batx\b|\beps\b|12vhpwr|12v-2x6|sleeve|riser|"
                       r"\bargb\b|\brgb\b|lüfter|\bfan\b|header|y-kabel|splitter|strimer|cable kit")
KABEL_MANAGEMENT = _r(r"kabelbinder|kabelkanal|kabelschlauch|kabelclip|klett|kabelführung|"
                      r"kabelmanagement|kabel-management|kabelorganizer|kabelwanne|kabelspirale")
LAPTOP_LADEN = _r(r"notebook|laptop|ladegerät|ladekabel.*(?:notebook|laptop)|netzteil")
PC_NETZTEIL = _r(r"\batx\b|\bsfx\b|80\s?\+|80 plus|80plus|modular|be quiet|seasonic|corsair r[mx]|"
                 r"\b\d{3,4}\s?w(?:att)?\b.*(?:netzteil|psu)|pc-netzteil")
PC_NETZTEIL_KABEL = _r(r"kabel|cable|strimer|verlängerung|adapter|sleeve")
GEHAEUSE_SPEICHER = _r(r"festplattengehäuse|enclosure|wechselrahmen|backplane|einschub|"
                       r"m\.2.{0,10}gehäuse|ssd.{0,10}gehäuse|hdd.{0,10}gehäuse|icy ?box|docking")
RISER = _r(r"riser")
MAUSPAD = _r(r"mauspad|mousepad|mouse pad|goliathus|desk ?mat|schreibtischunterlage|gaming-?pad")
TABLET_ZUBEHOER = _r(r"hülle|huelle|case|cover|folie|tastatur|keyboard|stift|\bpen\b|ständer|"
                     r"halterung|ladegerät|kabel|tasche|sleeve|schutz")


def einsortieren(nbb_kategorie, titel):
    """Gibt die DealKira-Kategorie zurück oder None (nicht übernehmen)."""
    k = (nbb_kategorie or "").strip()
    t = titel

    feste = {
        "Notebooks": "laptops", "Displays": "bildschirme", "PC": "fertig-pcs",
        "Headset": "headset", "Kopfhörer": "kopfhoerer", "Tastaturen": "tastaturen",
        "Webcams": "webcams", "USB-Hubs": "usb-hubs", "Drucker": "drucker",
        "Druckertinte": "druckerzubehoer", "Solid-State-Drive": "speicherplatten",
        "Festplatten": "speicherplatten", "USB Sticks": "speicherplatten",
        "Laufwerke": "speicherplatten", "Arbeitsspeicher": "ram", "Prozessoren": "cpu",
        "Mauspad": "mauspads", "Game Controller": "gaming-controller",
        "Wearables": "wearables", "Projektoren": "projektoren",
        "Projektor Halterung": "projektoren", "Projektorzubehör": "projektoren",
        "Lautsprecher": "lautsprecher", "Tragbare Lautsprecher": "lautsprecher",
        "Soundbar & Soundbase": "lautsprecher", "Netzwerk-Switch": "switches",
        "Router/WLAN": "router", "Netzwerk-Router": "router", "NAS": "nas",
        "Netzwerk-Adapter": "netzwerk-adapter", "Netzwerk-Module": "netzwerk-adapter",
        "Powerline": "powerline", "Netzwerk-Zubehör": "netzwerk-zubehoer",
        "Dockingstation": "dockingstations", "Taschen": "laptop-taschen",
        "Displayzubehör": "monitor-zubehoer", "Eingabestifte": "grafiktabletts",
        "Grafiktabletts": "grafiktabletts", "Software-Download": "software",
        "Software": "software", "Saugroboter": "staubsauger",
        "Adapter/Konverter": "computer-setup-kabel",
    }

    if k == "Mäuse":
        return "mauspads" if MAUSPAD.search(t) else "maeuse"
    if k == "Kühlung":
        if WASSER.search(t):
            return "wasserkuehlung"
        if CPU_KUEHLER.search(t):
            return "cpu-kuehler"
        return "luefter"
    if k == "Kabel":
        if KABEL_MANAGEMENT.search(t):
            return "kabel-management"
        if KABEL_NETZWERK.search(t):
            return "netzwerk-zubehoer"
        if KABEL_KOMPONENTEN.search(t):
            return "komponenten-kabel"
        if re.search(r"notebook|laptop", t, re.I):
            return "laptop-netzteile"
        return "computer-setup-kabel"
    if k in ("Netzteile", "Netzteile/Kabel"):
        if PC_NETZTEIL.search(t) and not PC_NETZTEIL_KABEL.search(t):
            return "netzteile"
        return "laptop-netzteile" if LAPTOP_LADEN.search(t) else "computer-setup-kabel"
    if k == "PC Netzteile":
        return "komponenten-kabel" if PC_NETZTEIL_KABEL.search(t) else "netzteile"
    if k == "Gehäuse":
        if RISER.search(t):
            return "komponenten-kabel"
        if GEHAEUSE_SPEICHER.search(t):
            return "speicherplatten"
        return "gehaeuse"
    if k == "Grafikkarten":
        return "komponenten-kabel" if RISER.search(t) else "grafikkarten"
    if k == "Mainboards":
        return "mainboards"
    if k == "Displayfolien":
        return "telefon-schutz" if HANDY.search(t) else "displayschutz"
    if k == "Tablet":
        return None if TABLET_ZUBEHOER.search(t) else "tablets"
    if k == "Netzwerk-Kamera":
        return smart_home(t, ist_kamera=True)
    if k == "Heimautomatisierung":
        return smart_home(t)
    return feste.get(k)


# Mindestpreis je Kategorie: Geräte darunter sind fast immer Ersatzteile oder Fehlangaben
MINDESTPREIS = {
    "laptops": 150, "bildschirme": 60, "fertig-pcs": 150, "tablets": 60,
    "grafikkarten": 80, "cpu": 40, "mainboards": 50, "ram": 15, "netzteile": 30,
    "gehaeuse": 25, "drucker": 40, "staubsauger": 80, "nas": 80, "projektoren": 30,
    "router": 15, "switches": 10, "wearables": 20,
}
STANDARD_MINDESTPREIS = 3

# In diesen Kategorien zählen Hüllen, Folien usw. als Fehltreffer (bei Zubehör-Kategorien nicht)
GERAETE = {"laptops", "bildschirme", "fertig-pcs", "tablets", "grafikkarten", "cpu",
           "mainboards", "ram", "drucker", "staubsauger", "wearables", "projektoren"}
GERAET_ZUBEHOER = _r(r"\bhülle\b|\bhuelle\b|\btasche\b|schutzfolie|displayschutz|panzerglas|"
                     r"ersatzteil|ersatz-|\bakku für\b|netzteil für|ladegerät für")
GEBRAUCHT = _r(r"refurbished|generalüberholt|gebraucht|\bb-?ware\b|\bused\b|renewed")
