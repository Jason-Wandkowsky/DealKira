# DealKira

Deals entdecken und Preise vergleichen – https://dealkira.com

## Aufbau

| Datei | Wofür |
|---|---|
| `basis.css` | Design für **alle** Seiten: Kopfzeile, Burger-Menü, Fußzeile |
| `basis.js` | Baut Kopfzeile, Menü und Fußzeile auf jeder Seite ein. **Menüpunkte hier ändern** (`MENU_EINTRAEGE`). |
| `bausteine.css` | Gemeinsames Design der Kategorie-Seiten (Hero, Filter-Button, Produkt-Grid, „Noch keine Produkte“) |
| `supabase-client.js` | Supabase-Verbindung (URL + öffentlicher Schlüssel) für Login und Favoriten |
| `telefone.json`, `tablets.json` | Produktdaten |

Jede Seite enthält nur noch:

```html
<site-header></site-header>   <!-- Kopfzeile + Menü -->
...Inhalt der Seite...
<site-footer></site-footer>   <!-- Fußzeile -->
```

Seitenspezifisches Design steht weiterhin im `<style>` der jeweiligen Seite.
