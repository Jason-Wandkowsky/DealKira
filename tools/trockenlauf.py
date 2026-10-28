"""Einmaliger Probelauf (speichert nichts): nbb-Import mit echtem Feed, Zählung je Kategorie."""
import collections, json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preise_aktualisieren as pa
import nbb_kategorien as nk

feed = pa.feed_laden(os.environ["AWIN_FEED_NOTEBOOKSBILLIGER"])
dateien = {f: json.load(open(f, encoding="utf-8")) for f in ["produkte.json", "telefone.json", "tablets.json"]}
pa.haendler_abgleich(dateien, "nbb", feed, "notebooksbilliger.de")
pa.haendler_import_aktualisieren(dateien, "nbb", feed, nk)
pa.haendler_import(dateien, "nbb", feed, "notebooksbilliger.de", nk)
nach = collections.defaultdict(list)
for f, liste in dateien.items():
    for p in liste:
        if p.get("importFeed"):
            nach[p.get("kategorie", "tablets")].append(p)
random.seed(1)
for k in sorted(nach):
    print(f"\n== {k}: {len(nach[k])}")
    for p in random.sample(nach[k], min(12, len(nach[k]))):
        print(f"   {p['name'][:60]:60} | {p['shops'][0]['price']:>12} | {p['shops'][0]['feedTitel'][:70]}")
# Was fällt raus?
raus = collections.Counter()
beispiele = collections.defaultdict(list)
for fid, z in feed.items():
    t, preis = pa.feed_titel(z), pa.feed_preis(z)
    if not pa.import_kategorie(nk, z, t, preis):
        raus[z.get("merchant_category")] += 1
        beispiele[z.get("merchant_category")].append(t)
print("\n== nicht übernommen je nbb-Kategorie:")
for k, n in raus.most_common():
    print(f"{n:6} {k}   z. B. {beispiele[k][0][:80]}")
print("\nGesamt importiert:", sum(len(v) for v in nach.values()))
print("produkte.json MB:", len(json.dumps(dateien["produkte.json"], ensure_ascii=False)) / 1e6)
