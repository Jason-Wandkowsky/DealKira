/* =====================================================
   DealKira – Produkte in Ratgeber-Artikeln
   <div class="ratgeber-produkte" data-ids="id1,id2,id3"></div>
   → zeigt diese Produkte aus produkte.json als Karten an.
===================================================== */

(function() {

  function karte(p) {
    const shop = (p.shops || []).find(function(s) { return s.price; }) ||
                 (p.shops || [])[0] || {};

    const card = document.createElement("article");
    card.className = "product-card";

    const bild = document.createElement("div");
    bild.className = "product-card-image";

    if (p.image) {
      const img = document.createElement("img");
      img.src = p.image;
      img.alt = p.name || "";
      img.loading = "lazy";
      img.onerror = function() { bild.replaceChildren(dkPlatzhalter(p)); };
      bild.appendChild(img);
    } else {
      bild.appendChild(dkPlatzhalter(p));
    }

    const body = document.createElement("div");
    body.className = "product-card-body";

    if (p.brand) {
      const marke = document.createElement("div");
      marke.className = "product-card-brand";
      marke.textContent = p.brand;
      body.appendChild(marke);
    }

    const titel = document.createElement("h2");
    titel.textContent = p.name || "Produkt";
    body.appendChild(titel);

    if (shop.price) {
      const preis = document.createElement("div");
      preis.className = "product-card-price";
      preis.textContent = shop.price + (shop.name ? " bei " + shop.name : "");
      body.appendChild(preis);
    }

    const knopf = document.createElement("a");
    knopf.className = "product-card-button";
    knopf.href = dkArtikelLink(p);
    knopf.textContent = "Zum Deal";
    body.appendChild(knopf);

    card.appendChild(bild);
    card.appendChild(body);
    if (window.dkFavButton) card.appendChild(dkFavButton(dkFavInfo(p)));
    return card;
  }

  document.addEventListener("DOMContentLoaded", async function() {
    const boxen = document.querySelectorAll(".ratgeber-produkte[data-ids]");
    if (!boxen.length) return;

    try {
      const alle = await dkIndexLaden();
      const nachId = {};
      alle.forEach(function(p) { nachId[p.id] = p; });

      boxen.forEach(function(box) {
        const karten = box.dataset.ids.split(",")
          .map(function(id) { return nachId[id.trim()]; })
          .filter(Boolean)
          .map(karte);
        box.replaceChildren.apply(box, karten);
      });
    } catch (fehler) {
      console.error("Ratgeber-Produkte:", fehler);
    }
  });

})();
