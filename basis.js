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
  { link: "deals.html",         icon: "🔥", text: "Deals" },
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
        '<p>© 2026 DealKira · <a href="support.html">Support</a></p>' +
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
