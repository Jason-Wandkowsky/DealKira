/* =====================================================
   DealKira – Basis
   Kopfzeile, Burger-Menü und Fußzeile für ALLE Seiten.

   Auf jeder Seite steht nur noch:
     <site-header></site-header>   → Kopfzeile mit Menü
     <site-footer></site-footer>   → Fußzeile

   Einen Menüpunkt hinzufügen oder ändern?
   → Einfach unten in MENU_EINTRAEGE bearbeiten.
===================================================== */

const MENU_EINTRAEGE = [
  { link: "konto.html",         icon: "👤", text: "Konto / Anmelden" },
  "trennlinie",
  { link: "suche.html",         icon: "🔍", text: "Suche" },
  { link: "kategorien.html",    icon: "📂", text: "Kategorien" },
  { link: "ratgeber.html",      icon: "📖", text: "Ratgeber" },
  { link: "deals.html",         icon: "🔥", text: "Deals" },
  { link: "black-friday.html",  icon: "🛍️", text: "Black Friday 2026" },
  { link: "einstellungen.html", icon: "⚙️", text: "Einstellungen" }
];

const LOGO_BILD = "20879_nobg (1).png";


/* =========================
   KOPFZEILE
========================= */

class SiteHeader extends HTMLElement {

  connectedCallback() {

    const links = MENU_EINTRAEGE.map(function(eintrag) {

      if (eintrag === "trennlinie") {
        return '<div class="menu-divider"></div>';
      }

      return (
        '<a href="' + eintrag.link + '">' +
          '<span class="menu-icon">' + eintrag.icon + '</span>' +
          eintrag.text +
        '</a>'
      );

    }).join("");

    this.innerHTML =
      '<header>' +
        '<a href="index.html" class="logo">' +
          '<img src="' + LOGO_BILD + '" alt="DealKira">' +
        '</a>' +
        '<button class="menu-button" id="menuButton" type="button" ' +
          'aria-label="Menü öffnen" aria-expanded="false" aria-controls="menuPanel">' +
          '<span></span><span></span><span></span>' +
        '</button>' +
        '<nav class="menu-panel" id="menuPanel">' + links + '</nav>' +
      '</header>';

    this.querySelector("#menuButton")
      .addEventListener("click", toggleMenu);

  }

}


/* =========================
   FUSSZEILE
========================= */

class SiteFooter extends HTMLElement {

  connectedCallback() {

    this.innerHTML =
      '<footer>' +
        '<strong>DealKira</strong>' +
        '<p>Produkte entdecken. Deals finden. Preise vergleichen.</p>' +
        '<p>' +
          '<a href="impressum.html">Impressum</a> · ' +
          '<a href="datenschutz.html">Datenschutz</a> · ' +
          '<a href="support.html">Support</a>' +
        '</p>' +
        '<p class="footer-hinweis">* Partnerlink (Anzeige) – <a href="impressum.html#partnerlinks">mehr dazu</a></p>' +
        '<p>© 2026 DealKira</p>' +
      '</footer>';

  }

}


customElements.define("site-header", SiteHeader);
customElements.define("site-footer", SiteFooter);


/* =========================
   MENÜ ÖFFNEN / SCHLIESSEN
========================= */

function toggleMenu() {

  const menu = document.getElementById("menuPanel");
  const button = document.getElementById("menuButton");

  const isOpen = menu.classList.toggle("open");

  button.classList.toggle("active", isOpen);
  button.setAttribute("aria-expanded", isOpen);

}


function closeMenu() {

  const menu = document.getElementById("menuPanel");
  const button = document.getElementById("menuButton");

  if (!menu || !button) return;

  menu.classList.remove("open");
  button.classList.remove("active");
  button.setAttribute("aria-expanded", "false");

}


/* Klick außerhalb des Menüs schließt es */

document.addEventListener("click", function(event) {

  const menu = document.getElementById("menuPanel");
  const button = document.getElementById("menuButton");

  if (!menu || !button) return;

  if (
    !menu.contains(event.target) &&
    !button.contains(event.target)
  ) {
    closeMenu();
  }

});


/* ESC schließt das Menü */

document.addEventListener("keydown", function(event) {

  if (event.key === "Escape") {
    closeMenu();
  }

});


/* =========================
   FILTER-HINWEIS
   (Button "⚙️ Filter" auf Kategorie-Seiten)
========================= */

function toggleFilter() {

  const message = document.getElementById("filterMessage");

  if (message) {
    message.classList.toggle("show");
  }

}


/* =========================
   PRODUKT-PLATZHALTER
   Wird angezeigt, wenn ein Produkt (noch) kein Bild hat:
   Kategorie-Symbol + Markenname statt "Kein Produktbild".

   dkPlatzhalter({ name, brand, kategorie })     → HTML-Element
   dkPlatzhalterHTML({ name, brand, kategorie }) → HTML-Text
   <div data-dk-ph data-name=".." data-brand=".." data-kat=".."></div>
     → wird beim Laden automatisch ersetzt
========================= */

const DK_ICONS = {
  chip:     '<rect x="6" y="6" width="12" height="12" rx="1.5"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3"/>',
  gpu:      '<rect x="2.5" y="6" width="19" height="11" rx="1.5"/><circle cx="8.5" cy="11.5" r="3"/><circle cx="15.5" cy="11.5" r="3"/><path d="M5 17v2.5M9 17v2.5"/>',
  board:    '<rect x="3" y="3" width="18" height="18" rx="1.5"/><rect x="7" y="7" width="5" height="5"/><path d="M15 7h3M15 10h3M7 15h11M7 18h6"/>',
  ram:      '<rect x="2.5" y="7" width="19" height="9" rx="1"/><path d="M6 10v3M9.5 10v3M13 10v3M16.5 10v3M5 16v2.5M19 16v2.5"/>',
  laptop:   '<rect x="4.5" y="5" width="15" height="10" rx="1"/><path d="M2.5 18.5h19"/>',
  monitor:  '<rect x="2.5" y="4" width="19" height="12" rx="1"/><path d="M12 16v4M8 20h8"/>',
  mouse:    '<rect x="7" y="3" width="10" height="18" rx="5"/><path d="M12 7v3"/>',
  keyboard: '<rect x="2.5" y="7" width="19" height="10" rx="1.5"/><path d="M6 10.5h.01M9.5 10.5h.01M13 10.5h.01M16.5 10.5h.01M7.5 14h9"/>',
  headset:  '<path d="M4 15v-3a8 8 0 0 1 16 0v3"/><rect x="3" y="14" width="4" height="6" rx="1.5"/><rect x="17" y="14" width="4" height="6" rx="1.5"/>',
  mic:      '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>',
  camera:   '<rect x="3" y="7" width="18" height="12" rx="2"/><circle cx="12" cy="13" r="3.5"/><path d="M8.5 7l1.5-2.5h4L15.5 7"/>',
  plug:     '<path d="M9 3v4M15 3v4M7 7h10v4a5 5 0 0 1-10 0V7zM12 16v5"/>',
  printer:  '<path d="M7 9V3.5h10V9"/><rect x="3" y="9" width="18" height="8" rx="1.5"/><rect x="7" y="14" width="10" height="6.5"/>',
  drive:    '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 14h.01M10.5 14h6.5"/>',
  battery:  '<rect x="2.5" y="7" width="17" height="10" rx="2"/><path d="M21.5 10.5v3M6 10v4M9.5 10v4"/>',
  fan:      '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="1.5"/><path d="M12 10.5C11 7 12.5 5 15 5.5M13.5 12.5c3.5-.5 5 1.5 3.5 3.5M10.5 12.8C8 15.5 6 15 5.5 12.5"/>',
  tower:    '<rect x="6" y="2.5" width="12" height="19" rx="1.5"/><circle cx="12" cy="14" r="3"/><path d="M9 6h6"/>',
  phone:    '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18.5h2"/>',
  tablet:   '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M11 18h2"/>',
  gamepad:  '<path d="M6.5 7h11a4 4 0 0 1 3.9 4.8l-.9 4.4a2.5 2.5 0 0 1-4.3 1.2L14.5 15h-5l-1.7 2.4a2.5 2.5 0 0 1-4.3-1.2l-.9-4.4A4 4 0 0 1 6.5 7z"/><path d="M8 10v3M6.5 11.5h3M15.5 11h.01M17 12.5h.01"/>',
  fridge:   '<rect x="5.5" y="2.5" width="13" height="19" rx="1.5"/><path d="M5.5 9.5h13M8.5 5.5v2M8.5 12v3"/>',
  washer:   '<rect x="4" y="2.5" width="16" height="19" rx="1.5"/><circle cx="12" cy="13.5" r="4.5"/><path d="M7 5.5h3"/>',
  stove:    '<rect x="3" y="4" width="18" height="16" rx="1.5"/><circle cx="8.5" cy="10" r="2.5"/><circle cx="15.5" cy="10" r="2.5"/><path d="M6 16h12"/>',
  hood:     '<path d="M9 3h6v6l5 6H4l5-6V3zM4 15v2.5h16V15"/>',
  vacuum:   '<path d="M14 3l-4 13"/><path d="M5 16.5h9a2 2 0 0 1 2 2v1.5H3v-1.5a2 2 0 0 1 2-2z"/>',
  heater:   '<rect x="3" y="5" width="18" height="12" rx="1.5"/><path d="M7 8.5v5M10.5 8.5v5M14 8.5v5M17.5 8.5v5M6 17v2.5M18 17v2.5"/>',
  snow:     '<path d="M12 2.5v19M3.8 7.2l16.4 9.6M3.8 16.8l16.4-9.6M9.5 4l2.5 2.5L14.5 4M9.5 20l2.5-2.5 2.5 2.5"/>',
  bell:     '<rect x="6" y="2.5" width="12" height="19" rx="3"/><circle cx="12" cy="8.5" r="2.5"/><circle cx="12" cy="16" r="1.5"/>',
  mower:    '<path d="M3 15.5l2-6h11l3 6z"/><circle cx="7" cy="17.5" r="2"/><circle cx="17" cy="17.5" r="2"/><path d="M9 9.5V7h5v2.5M3 20.5h18"/>',
  solar:    '<path d="M3 18l3-11h12l3 11z"/><path d="M4.5 12.5h15M9 7l-1 11M15 7l1 11M12 18v3"/>',
  box:      '<path d="M3.5 7.5L12 3l8.5 4.5v9L12 21l-8.5-4.5z"/><path d="M3.5 7.5L12 12l8.5-4.5M12 12v9"/>'
};

const DK_KATEGORIE_ICON = {
  cpu: "chip", ram: "ram", mainboards: "board", grafikkarten: "gpu",
  netzteile: "plug", gehaeuse: "tower", "cpu-kuehler": "fan",
  wasserkuehlung: "fan", luefter: "fan", speicherplatten: "drive",
  laptops: "laptop", bildschirme: "monitor", maeuse: "mouse",
  tastaturen: "keyboard", headset: "headset", mikrofon: "mic",
  webcams: "camera", "usb-hubs": "plug", drucker: "printer",
  "computer-setup-kabel": "plug", "komponenten-kabel": "plug",
  "kabel-management": "plug",
  telefon: "phone", tablet: "tablet",
  "telefon-audio": "headset", "telefon-auto": "phone",
  "telefon-foto-video": "camera", "telefon-gaming": "gamepad",
  "telefon-kabel": "plug", "telefon-netzteile-adapter": "plug",
  "telefon-powerbanks": "battery", "telefon-schutz": "phone",
  "telefon-speicher": "drive",
  kuehlschraenke: "fridge", gefrierschraenke: "fridge",
  waschmaschinen: "washer", trockner: "washer", waschtrockner: "washer",
  spuelmaschinen: "washer", staubsauger: "vacuum", ofen: "stove",
  kochfelder: "stove", abzugshauben: "hood", klimaanlagen: "snow",
  ventilatoren: "fan", "mobile-heizungen": "heater",
  konsole: "gamepad", tv: "monitor",
  "outdoor-kameras": "camera", "indoor-kameras": "camera",
  "kamera-sets": "camera", "kamera-zubehoer": "solar", tuerklingeln: "bell", heimautomatisierung: "plug", maehroboter: "mower",
  "fertig-pcs": "tower", "software": "box", "laptop-taschen": "laptop", "dockingstations": "plug", "laptop-netzteile": "battery", "displayschutz": "monitor", "router": "plug", "switches": "plug", "nas": "drive", "netzwerk-adapter": "plug", "powerline": "plug", "netzwerk-zubehoer": "plug", "kopfhoerer": "headset", "lautsprecher": "headset", "mauspads": "mouse", "gaming-controller": "gamepad", "monitor-zubehoer": "monitor", "projektoren": "monitor", "druckerzubehoer": "printer", "grafiktabletts": "tablet", "wearables": "phone"
};

function dkEscape(value) {
  return String(value || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function dkPlatzhalterHTML(info) {
  info = info || {};
  const icon = DK_ICONS[DK_KATEGORIE_ICON[info.kategorie]] || DK_ICONS.box;
  const brand = info.brand ? '<span class="dk-ph-brand">' + dkEscape(info.brand) + '</span>' : "";
  return '<div class="dk-ph" role="img" aria-label="' + dkEscape(info.name || "Produkt") + '">' +
    '<span class="dk-ph-icon"><svg viewBox="0 0 24 24" aria-hidden="true">' + icon + '</svg></span>' +
    brand + '</div>';
}

function dkPlatzhalter(info) {
  const wrap = document.createElement("div");
  wrap.innerHTML = dkPlatzhalterHTML(info);
  return wrap.firstChild;
}

document.addEventListener("DOMContentLoaded", function() {
  document.querySelectorAll("[data-dk-ph]").forEach(function(el) {
    el.replaceWith(dkPlatzhalter({
      name: el.dataset.name, brand: el.dataset.brand, kategorie: el.dataset.kat
    }));
  });
});


/* =====================================================
   DealKira – Favoriten auf allen Seiten
   Wird automatisch von basis.js geladen.

   dkFavButton({ id, name, image, price, shop, link })
     → fertiger ♡-Button, der sich selbst um Login,
       Speichern und Entfernen kümmert.

   Gespeichert wird in der Supabase-Tabelle "favoriten"
   (dieselbe wie auf den Telefon-/Tablet-Seiten und im Konto).
===================================================== */

(function() {

  const SUPABASE_CDN = "https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2";

  let client = null;
  let user = null;
  let favoriten = new Set();

  function skriptLaden(src) {
    return new Promise(function(fertig, fehler) {
      const s = document.createElement("script");
      s.src = src;
      s.onload = fertig;
      s.onerror = fehler;
      document.head.appendChild(s);
    });
  }

  function anzeigen(button) {
    const aktiv = favoriten.has(button.dataset.favId);
    button.classList.toggle("active", aktiv);
    button.textContent = aktiv ? "♥" : "♡";
    button.setAttribute("aria-label",
      (button.dataset.favName || "Produkt") + (aktiv ? " aus Favoriten entfernen" : " zu Favoriten hinzufügen"));
    button.setAttribute("aria-pressed", aktiv ? "true" : "false");
  }

  function alleAnzeigen() {
    document.querySelectorAll(".dk-fav").forEach(anzeigen);
  }

  async function verbinden() {
    try {
      if (typeof supabaseClient === "undefined") {
        if (!window.supabase) await skriptLaden(SUPABASE_CDN);
        if (typeof supabaseClient === "undefined") await skriptLaden("supabase-client.js");
      }
      client = supabaseClient;
      const { data } = await client.auth.getSession();
      user = (data && data.session && data.session.user) || null;
      if (user) {
        const { data: liste, error } = await client
          .from("favoriten").select("produkt_id").eq("user_id", user.id);
        if (!error && liste) favoriten = new Set(liste.map(function(f) { return f.produkt_id; }));
      }
      alleAnzeigen();
    } catch (fehler) {
      console.error("Favoriten konnten nicht geladen werden:", fehler);
    }
  }

  const bereit = new Promise(function(fertig) {
    function start() { verbinden().then(fertig); }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", start);
    } else {
      start();
    }
  });

  async function umschalten(button, info) {
    button.disabled = true;
    try {
      await bereit;
      if (!client || !user) {
        alert("Bitte melde dich zuerst an, um Produkte zu deinen Favoriten hinzuzufügen.");
        window.location.href = "konto.html";
        return;
      }
      if (favoriten.has(info.id)) {
        const { error } = await client.from("favoriten")
          .delete().eq("user_id", user.id).eq("produkt_id", info.id);
        if (error) throw error;
        favoriten.delete(info.id);
      } else {
        const { error } = await client.from("favoriten").insert({
          user_id: user.id,
          produkt_id: info.id,
          produkt_name: info.name || "",
          produkt_bild: info.image || "",
          produkt_preis: info.price || "",
          produkt_shop: info.shop || "",
          produkt_link: info.link || ""
        });
        if (error) throw error;
        favoriten.add(info.id);
      }
      alleAnzeigen();
    } catch (fehler) {
      console.error("Favoriten-Fehler:", fehler);
      alert("Favorit konnte nicht gespeichert werden. Bitte versuch es noch einmal.");
    } finally {
      button.disabled = false;
    }
  }

  /* Infos aus einem Produkt aus produkte.json / telefone.json / tablets.json */
  window.dkFavInfo = function(p, detailSeite) {
    const shop = (p.shops || []).find(function(s) { return s.price; }) || (p.shops || [])[0] || {};
    return {
      id: p.id,
      name: p.name,
      image: p.image || "",
      price: shop.price || "",
      shop: shop.name || "",
      link: "https://dealkira.com/" + (detailSeite || "artikel.html") + "?id=" + encodeURIComponent(p.id)
    };
  };

  window.dkFavButton = function(info, extraKlasse) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "favorite-button dk-fav" + (extraKlasse ? " " + extraKlasse : "");
    button.dataset.favId = info.id;
    button.dataset.favName = info.name || "";
    anzeigen(button);
    button.addEventListener("click", function(e) {
      e.preventDefault();
      e.stopPropagation();
      umschalten(button, info);
    });
    return button;
  };

})();


/* =====================================================
   Bestpreis: günstigster Shop-Preis eines Produkts
   dkBestpreis(p)     → { preis: 489.13, text: "489,13 €", shop: "eBay", anzahl: 2 } oder null
   dkPreisElement(p)  → <div class="dk-preis">ab 489,13 € <small>bei eBay · 2 Shops</small></div>
===================================================== */
(function() {
  function zahl(text) {
    const z = parseFloat(String(text || "").replace(/[^0-9,]/g, "").replace(",", "."));
    return isNaN(z) || z <= 0 ? null : z;
  }

  window.dkBestpreis = function(p) {
    const shops = (p && p.shops) || [];
    let best = null;
    shops.forEach(function(s) {
      const z = zahl(s.price);
      if (z !== null && (!best || z < best.preis)) best = { preis: z, text: s.price, shop: s.name };
    });
    if (best) best.anzahl = new Set(shops.filter(function(s) { return s.link; })
      .map(function(s) { return s.name; })).size;
    return best;
  };

  window.dkPreisElement = function(p) {
    const best = window.dkBestpreis(p);
    const el = document.createElement("div");
    el.className = "dk-preis";
    if (!best) {
      const anzahl = new Set(((p && p.shops) || []).filter(function(s) { return s.link; })
        .map(function(s) { return s.name; })).size;
      el.classList.add("dk-preis-leer");
      el.textContent = anzahl > 1 ? anzahl + " Shops vergleichen" : "Preis beim Shop ansehen";
      return el;
    }
    el.append("ab ");
    const strong = document.createElement("strong");
    strong.textContent = best.text;
    el.appendChild(strong);
    // Mehrere Shops mit Preis (z. B. notebooksbilliger und eBay): Preisvergleich direkt auf der Karte
    const mitPreis = {};
    ((p && p.shops) || []).forEach(function(s) {
      const z = zahl(s.price);
      if (z !== null && (!(s.name in mitPreis) || z < mitPreis[s.name].preis)) {
        mitPreis[s.name] = { name: s.name, preis: z, text: s.price };
      }
    });
    const vergleich = Object.values(mitPreis).sort(function(a, b) { return a.preis - b.preis; });
    if (vergleich.length < 2) {
      const klein = document.createElement("small");
      klein.textContent = "bei " + best.shop + (best.anzahl > 1 ? " · " + best.anzahl + " Shops" : "");
      el.appendChild(klein);
      return el;
    }
    const liste = document.createElement("ul");
    liste.className = "dk-preis-vergleich";
    vergleich.slice(0, 3).forEach(function(s, i) {
      const zeile = document.createElement("li");
      if (i === 0) zeile.className = "dk-preis-bester";
      const name = document.createElement("span");
      name.textContent = s.name.replace(/\.de$/, "");
      const preis = document.createElement("span");
      preis.textContent = s.text;
      zeile.append(name, preis);
      liste.appendChild(zeile);
    });
    el.appendChild(liste);
    return el;
  };
})();


/* =====================================================
   Produktdaten (seit dem notebooksbilliger-Feed viele Tausend Produkte):
   dkKategorieLaden("laptops") → alle Produkte einer Kategorie (daten/kategorie/…)
   dkIndexLaden()              → kurze Liste aller Produkte (daten/index.json)
   dkArtikelLink(p)            → Link zur Produktseite (mit Kategorie, dann lädt sie schneller)
===================================================== */
(function() {
  async function json(url) {
    const antwort = await fetch(url, { cache: "no-cache" });
    if (!antwort.ok) throw new Error(url + " konnte nicht geladen werden.");
    return antwort.json();
  }
  let index = null;
  window.dkKategorieLaden = function(kategorie) {
    return json("daten/kategorie/" + encodeURIComponent(kategorie) + ".json").catch(function() { return []; });
  };
  window.dkIndexLaden = function() {
    if (!index) index = json("daten/index.json");
    return index;
  };
  window.dkArtikelLink = function(p) {
    return "artikel.html?id=" + encodeURIComponent(p.id || "") +
      (p.kategorie ? "&k=" + encodeURIComponent(p.kategorie) : "");
  };
})();
