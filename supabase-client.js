/* =====================================================
   DealKira – Supabase-Verbindung
   Wird auf allen Seiten mit Login/Favoriten geladen
   (nach der Supabase-Bibliothek, vor dem Seiten-Code).

   Der "publishable" Schlüssel darf öffentlich sein.
   Schutz der Daten passiert über Row Level Security
   in Supabase.
===================================================== */

const SUPABASE_URL =
  "https://zniknbouugmgvqkkoamo.supabase.co";

const SUPABASE_KEY =
  "sb_publishable_Jr7OQScG8lgIja_Hav5-mw_B_htFgzI";

const supabaseClient =
  window.supabase.createClient(
    SUPABASE_URL,
    SUPABASE_KEY
  );
