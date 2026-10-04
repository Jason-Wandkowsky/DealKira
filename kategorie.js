/* =====================================================
   DealKira – Kategorie-Seiten
   Zeigt auf jeder Unterkategorie die passenden Produkte
   aus produkte.json an.

   So funktioniert's:
   - Auf der Seite steht <div class="products" data-kategorie="maeuse">
   - Hier werden alle Produkte mit "kategorie": "maeuse" angezeigt.
   - Gibt es keine, bleibt der Hinweis "Noch keine Produkte" stehen.

   Neues Produkt? → Nur in produkte.json eintragen.
===================================================== */

(function() {

  const KATEGORIE_ICONS = {
    laptops: "💻",
    bildschirme: "🖥️",
    maeuse: "🖱️",
    tastaturen: "⌨️",
    headset: "🎧",
    mikrofon: "🎙️",
    webcams: "📷",
    "usb-hubs": "🔌",
    drucker: "🖨️",
    speicherplatten: "💾",
    grafikkarten: "🎮",
    ram: "🧠",
    cpu: "⚙️"
  };

  function iconFor(kategorie) {
    return KATEGORIE_ICONS[kategorie] || "📦";
  }

  /* =========================
     PRODUKTKARTE
  ========================= */

  function createCard(product) {

    const shop =
      (product.shops || []).find(function(s) {
        return s.link;
      }) || {};

    const card =
      document.createElement("article");

    card.className =
      "product-card";

    card.dataset.brand =
      product.brand || "";

    /* Bild oder Platzhalter */

    const imageBox =
      document.createElement("div");

    imageBox.className =
      "product-card-image";

    function showNoImage() {

      imageBox.innerHTML = "";

      const box =
        document.createElement("div");

      box.className =
        "no-image";

      box.setAttribute("role", "img");

      box.setAttribute(
        "aria-label",
        (product.name || "Produkt") + ": kein Produktbild"
      );

      box.textContent =
        iconFor(product.kategorie);

      const label =
        document.createElement("span");

      label.textContent =
        "Kein Produktbild";

      box.appendChild(label);

      imageBox.appendChild(box);

    }

    if (product.image) {

      const img =
        document.createElement("img");

      img.src = product.image;
      img.alt = product.name || "";
      img.loading = "lazy";
      img.onerror = showNoImage;

      imageBox.appendChild(img);

    } else {

      showNoImage();

    }

    /* Text */

    const body =
      document.createElement("div");

    body.className =
      "product-card-body";

    if (product.brand) {

      const brand =
        document.createElement("div");

      brand.className =
        "product-card-brand";

      brand.textContent =
        product.brand;

      body.appendChild(brand);

    }

    const title =
      document.createElement("h2");

    title.textContent =
      product.name || "Produkt";

    body.appendChild(title);

    if (shop.price) {

      const price =
        document.createElement("div");

      price.className =
        "product-card-price";

      price.textContent =
        shop.price;

      body.appendChild(price);

    }

    if (shop.link) {

      const button =
        document.createElement("a");

      button.className =
        "product-card-button";

      button.href =
        shop.link;

      button.target =
        "_blank";

      button.rel =
        "nofollow sponsored noopener noreferrer";

      button.textContent =
        "Zum Deal bei " + (shop.name || "Shop");

      const mark =
        document.createElement("span");

      mark.className =
        "ad-mark";

      mark.textContent =
        "*";

      button.appendChild(mark);

      body.appendChild(button);

    }

    card.appendChild(imageBox);
    card.appendChild(body);

    return card;

  }

  /* =========================
     MARKEN-FILTER
  ========================= */

  function buildFilter(products, container) {

    const message =
      document.getElementById("filterMessage");

    if (!message) {
      return;
    }

    const brands =
      Array.from(
        new Set(
          products
            .map(function(p) { return p.brand; })
            .filter(Boolean)
        )
      ).sort(function(a, b) {
        return a.localeCompare(b, "de");
      });

    message.innerHTML = "";

    message.classList.add("brand-filter");

    const label =
      document.createElement("div");

    label.className =
      "brand-filter-label";

    label.textContent =
      "Nach Marke filtern";

    message.appendChild(label);

    const chips =
      document.createElement("div");

    chips.className =
      "brand-chips";

    function makeChip(text, value) {

      const chip =
        document.createElement("button");

      chip.type =
        "button";

      chip.className =
        "brand-chip";

      chip.textContent =
        text;

      chip.dataset.value =
        value;

      chip.addEventListener("click", function() {

        chips
          .querySelectorAll(".brand-chip")
          .forEach(function(c) {
            c.classList.toggle("active", c === chip);
          });

        container
          .querySelectorAll(".product-card")
          .forEach(function(card) {
            card.hidden =
              value !== "" && card.dataset.brand !== value;
          });

      });

      chips.appendChild(chip);

      return chip;

    }

    makeChip("Alle", "").classList.add("active");

    brands.forEach(function(brand) {
      makeChip(brand, brand);
    });

    message.appendChild(chips);

  }

  /* =========================
     START
  ========================= */

  async function loadCategory() {

    const container =
      document.querySelector(".products[data-kategorie]");

    if (!container) {
      return;
    }

    const kategorie =
      container.dataset.kategorie;

    try {

      const response =
        await fetch("produkte.json");

      if (!response.ok) {
        throw new Error("produkte.json konnte nicht geladen werden.");
      }

      const all =
        await response.json();

      const products =
        all.filter(function(p) {
          return p.kategorie === kategorie;
        });

      if (!products.length) {
        return;
      }

      container.replaceChildren(
        ...products.map(createCard)
      );

      const note =
        document.createElement("p");

      note.className =
        "affiliate-note";

      note.textContent =
        "* Partnerlink (Anzeige): Kaufst du über einen solchen Link, erhält DealKira eine Provision. Für dich ändert sich am Preis nichts.";

      container.after(note);

      buildFilter(products, container);

    }

    catch (error) {

      console.error("Kategorie:", error);

    }

  }

  document.addEventListener(
    "DOMContentLoaded",
    loadCategory
  );

})();
