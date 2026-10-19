/* =====================================================
   DealKira – Automatische und manuelle Deals
   - deals-auto.json     → vom Preis-Bot: "deals" (echte Preissenkungen,
                           verglichen mit dem Tiefstpreis der letzten 30 Tage)
                           und "angebote" (Streichpreis/UVP aus dem Shop-Feed)
   - manuelle-deals.json → von Hand, z. B. Amazon-Angebote mit Ablaufdatum
     Format: [{ "id": "produkt-id", "preis": "49,99 €", "bis": "2026-11-30",
               "hinweis": "Black Friday", "vorher": "69,99 €" (optional) }]
===================================================== */

(function() {

  async function laden(datei) {
    try {
      const antwort = await fetch(datei + "?t=" + Date.now(), { cache: "no-store" });
      return antwort.ok ? await antwort.json() : null;
    } catch (fehler) {
      return null;
    }
  }

  function datumText(iso) {
    const [j, m, t] = iso.split("-");
    return t + "." + m + "." + j;
  }

  function karte(p, info) {
    const card = document.createElement("article");
    card.className = "deal-card deal-card-preis";

    if (info.badge) {
      const badge = document.createElement("div");
      badge.className = "deal-badge";
      badge.textContent = info.badge;
      card.appendChild(badge);
    }

    const bild = document.createElement("div");
    bild.className = "deal-image";
    if (p.image) {
      const img = document.createElement("img");
      img.src = p.image;
      img.alt = p.name;
      img.loading = "lazy";
      img.onerror = function() { bild.replaceChildren(dkPlatzhalter(p)); };
      bild.appendChild(img);
    } else {
      bild.appendChild(dkPlatzhalter(p));
    }
    card.appendChild(bild);

    const inhalt = document.createElement("div");
    inhalt.className = "deal-content";

    const titel = document.createElement("h2");
    titel.textContent = p.name;
    inhalt.appendChild(titel);

    const preis = document.createElement("div");
    preis.className = "deal-preis";
    preis.innerHTML =
      (info.vorher ? '<s>' + info.vorher + '</s> ' : '') +
      '<strong>' + info.preis + '</strong>' +
      (info.shop ? ' <span>bei ' + info.shop + '</span>' : '');
    inhalt.appendChild(preis);

    if (info.notiz) {
      const notiz = document.createElement("div");
      notiz.className = "deal-notiz";
      notiz.textContent = info.notiz;
      inhalt.appendChild(notiz);
    }

    const knopf = document.createElement("a");
    knopf.className = "deal-button";
    knopf.href = "artikel.html?id=" + encodeURIComponent(p.id);
    knopf.textContent = "Zum Deal";
    inhalt.appendChild(knopf);

    card.appendChild(inhalt);
    if (window.dkFavButton) card.appendChild(dkFavButton(dkFavInfo(p)));
    return card;
  }

  /* Alle aktuellen Deals als Liste: [{ p, info, art }] – auch für die Startseite */
  async function dealsLaden() {
    const [produkte, auto, manuell] = await Promise.all([
      laden("produkte.json"), laden("deals-auto.json"), laden("manuelle-deals.json")
    ]);
    if (!produkte) return null;

    const nachId = {};
    produkte.forEach(function(p) { nachId[p.id] = p; });
    const heute = new Date().toISOString().slice(0, 10);
    const stand = auto && auto.stand ? " · Stand " + datumText(auto.stand) : "";

    const gesenkt = ((auto && auto.deals) || [])
      .filter(function(d) { return nachId[d.id]; })
      .map(function(d) {
        return { art: "auto", p: nachId[d.id], info: {
          badge: "−" + d.rabatt + " %",
          preis: d.preis,
          vorher: d.vorher,
          shop: d.shop,
          notiz: "Vergleich: niedrigster Preis der letzten 30 Tage" + stand
        }};
      });

    const angebote = ((auto && auto.angebote) || [])
      .filter(function(d) { return nachId[d.id]; })
      .map(function(d) {
        const uvp = d.art === "uvp";
        return { art: "angebote", p: nachId[d.id], info: {
          badge: "−" + d.rabatt + " %",
          preis: d.preis,
          vorher: (uvp ? "UVP " : "") + d.statt,
          shop: d.shop,
          notiz: (uvp ? "Vergleich: unverbindliche Preisempfehlung des Herstellers"
                      : "Streichpreis laut " + d.shop) + stand
        }};
      });

    const aktionen = (manuell || [])
      .filter(function(d) { return nachId[d.id] && (!d.bis || d.bis >= heute); })
      .map(function(d) {
        return { art: "manuell", p: nachId[d.id], info: {
          badge: d.hinweis || "Angebot",
          preis: d.preis,
          vorher: d.vorher,
          shop: d.shop || "Amazon",
          notiz: d.bis ? "Angebot gültig bis " + datumText(d.bis) + " – Preis beim Shop prüfen" : ""
        }};
      });

    return gesenkt.concat(angebote, aktionen);
  }

  window.dkDealsLaden = dealsLaden;

  document.addEventListener("DOMContentLoaded", async function() {
    if (!document.getElementById("dealsAuto")) return;   // nur auf deals.html

    const alle = (await dealsLaden()) || [];
    const bereiche = { auto: "dealsAuto", angebote: "dealsAngebote", manuell: "dealsManuell" };

    Object.keys(bereiche).forEach(function(art) {
      const bereich = document.getElementById(bereiche[art]);
      const karten = alle
        .filter(function(d) { return d.art === art; })
        .map(function(d) { return karte(d.p, d.info); });
      if (!bereich || !karten.length) return;
      const ziel = bereich.querySelector(".deals");
      ziel.replaceChildren.apply(ziel, karten);
      bereich.hidden = false;
    });

    const leer = document.getElementById("dealsLeer");
    if (leer) leer.hidden = alle.length > 0;
  });

  window.dkDealKarte = karte;

})();
