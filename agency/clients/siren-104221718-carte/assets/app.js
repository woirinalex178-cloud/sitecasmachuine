/* La Casa Demir — carte interactive. JS vanilla, aucune dependance.
   Genere le 2026-11-06 par Studio Cas Machuine.

   Source des donnees : assets/../menu.json (modifiable par le client).
   Si la page est ouverte en file:// (double-clic), fetch est bloque par le
   navigateur : on retombe alors sur la copie integree dans #menu-inline,
   ecrite par le generateur a chaque build. Les deux sont toujours identiques.
*/
(function () {
  "use strict";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var norm = function (s) {
    return String(s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  /* ==================== 1. entete + horaires ==================== */
  var entete = $("#entete");
  if (entete) {
    var majEntete = function () { entete.classList.toggle("colle", window.scrollY > 8); };
    majEntete();
    window.addEventListener("scroll", majEntete, { passive: true });
  }

  (function horaires() {
    var JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
    var lignes = $$("#liste-horaires li");
    if (!lignes.length) return;
    var mn = function (h) { var p = h.split(":"); return (+p[0]) * 60 + (+(p[1] || 0)); };
    var hhmm = function (m) {
      var h = Math.floor(m / 60), mi = m % 60;
      return h + "h" + (mi ? ("0" + mi).slice(-2) : "");
    };
    var creneaux = function (li) {
      var b = (li.getAttribute("data-creneaux") || "").trim();
      return b ? b.split(",").map(function (c) { var p = c.split("-"); return { d: mn(p[0]), f: mn(p[1]) }; }) : [];
    };
    var now = new Date(), jjs = now.getDay(), jiso = jjs === 0 ? 7 : jjs;
    var mnt = now.getHours() * 60 + now.getMinutes(), duJour = null;

    lignes.forEach(function (li) {
      if (+li.getAttribute("data-jour") === jiso) { li.classList.add("aujourdhui"); duJour = li; }
    });

    var etat = "ferme", txt = "Fermé aujourd’hui";
    if (duJour) {
      var cr = creneaux(duJour);
      var ouvert = cr.filter(function (c) { return mnt >= c.d && mnt < c.f; })[0];
      if (ouvert) { etat = "ouvert"; txt = "Ouvert · service jusqu’à " + hhmm(ouvert.f); }
      else {
        var suivant = cr.filter(function (c) { return c.d > mnt; })[0];
        if (suivant) txt = "Fermé — service à " + hhmm(suivant.d);
        else for (var i = 1; i <= 7; i++) {
          var cible = ((jiso - 1 + i) % 7) + 1;
          var li2 = lignes.filter(function (l) { return +l.getAttribute("data-jour") === cible; })[0];
          if (li2 && creneaux(li2).length) {
            txt = "Fermé — ouvre " + (i === 1 ? "demain" : JOURS[cible % 7]) + " à " + hhmm(creneaux(li2)[0].d);
            break;
          }
        }
      }
    }
    var badge = $("#statut-ouvert");
    if (badge) { badge.setAttribute("data-etat", etat); $("#statut-texte").textContent = txt; }
    var dd = $("#horaire-jour");
    if (dd) {
      var h = duJour ? ($(".heures", duJour) || {}).textContent : null;
      dd.textContent = (h || "Fermé").trim();
    }
  })();

  /* ==================== 2. chargement du menu ==================== */
  var cible = $("#menu-cible");
  if (!cible) return;

  var lireInline = function () {
    var el = $("#menu-inline");
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  };

  var charger = function (suite) {
    if (location.protocol === "file:") { suite(lireInline()); return; }
    fetch("menu.json", { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(suite)
      .catch(function () { suite(lireInline()); });
  };

  /* ==================== 3. rendu + filtres ==================== */
  var etat = { q: "", cat: "tout", vege: false, sansAllerg: "" };
  var MENU = null, LIB = {};

  var prix = function (v, devise) {
    if (v == null || v === "") return "";
    var n = Number(v);
    if (isNaN(n)) return esc(v);
    var e = Math.floor(n), c = Math.round((n - e) * 100);
    var d = esc(devise || "€");
    return c ? e + "," + '<span class="cents">' + ("0" + c).slice(-2) + "</span> " + d
             : e + " " + d;
  };

  var surligne = function (texte, q) {
    var t = esc(texte);
    if (!q) return t;
    var nq = norm(q), nt = norm(texte), i = nt.indexOf(nq);
    if (i < 0) return t;
    // on resegmente sur le texte brut puis on echappe chaque morceau
    return esc(texte.slice(0, i)) + "<mark>" + esc(texte.slice(i, i + q.length)) + "</mark>" + esc(texte.slice(i + q.length));
  };

  var correspond = function (p) {
    if (etat.cat !== "tout" && p.categorie !== etat.cat) return false;
    if (etat.vege && !p.vegetarien) return false;
    if (etat.sansAllerg && (p.allergenes || []).indexOf(etat.sansAllerg) !== -1) return false;
    if (etat.q) {
      var q = norm(etat.q);
      var foin = norm([p.nom, p.description, (p.allergenes || []).join(" "), LIB[p.categorie] || ""].join(" "));
      if (foin.indexOf(q) < 0) return false;
    }
    return true;
  };

  var ICO_VEGE = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20c0-6 3.6-10 8-10.6C19.4 15 16 20 12 20Z"/><path d="M12 20C7.6 19.4 4 15 4 9.4 8.4 10 12 14 12 20Z"/></svg>';
  var ICO_SIGN = '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="m12 4.8 2.3 4.8 5.2.7-3.8 3.6.9 5.1L12 16.6l-4.6 2.4.9-5.1L4.5 10.3l5.2-.7Z"/></svg>';

  var platHTML = function (p) {
    var et = [];
    if (p.signature) et.push('<span class="etiq etiq-sign">' + ICO_SIGN + "Signature</span>");
    if (p.vegetarien) et.push('<span class="etiq etiq-vege">' + ICO_VEGE + "Végétarien</span>");
    var allerg = (p.allergenes || []).map(function (a) {
      return esc((MENU.allergenes && MENU.allergenes[a]) || a);
    });
    return '<li class="plat' + (p.signature ? " signature" : "") + '">'
      + '<div class="plat-haut">'
      + '<h3 class="plat-nom">' + surligne(p.nom, etat.q) + "</h3>"
      + '<p class="plat-prix">' + prix(p.prix, MENU.devise) + "</p>"
      + "</div>"
      + (p.description ? '<p class="plat-desc">' + surligne(p.description, etat.q) + "</p>" : "")
      + (et.length ? '<p class="plat-bas">' + et.join("") + "</p>" : "")
      + (allerg.length ? '<p class="plat-allerg"><span>Contient</span>' + allerg.join(" · ") + "</p>" : "")
      + "</li>";
  };

  var dessiner = function () {
    var cats = MENU.categories || [];
    var html = "", visibles = 0;

    cats.forEach(function (c) {
      var plats = (MENU.plats || []).filter(function (p) { return p.categorie === c.id; }).filter(correspond);
      if (!plats.length) return;
      visibles += plats.length;
      html += '<section class="cat" id="cat-' + esc(c.id) + '" aria-labelledby="t-' + esc(c.id) + '">'
        + '<header class="cat-tete"><h2 id="t-' + esc(c.id) + '">' + esc(c.nom) + "</h2>"
        + '<span class="cat-n">' + plats.length + " plat" + (plats.length > 1 ? "s" : "") + "</span></header>"
        + (c.description ? '<p class="cat-desc">' + esc(c.description) + "</p>" : "")
        + '<ul class="plats" role="list">' + plats.map(platHTML).join("") + "</ul>"
        + "</section>";
    });

    cible.innerHTML = html;
    $("#vide").hidden = visibles > 0;

    var total = (MENU.plats || []).length;
    var compte = $("#compte");
    if (compte) {
      var filtre = etat.q || etat.vege || etat.sansAllerg || etat.cat !== "tout";
      compte.textContent = filtre
        ? visibles + " plat" + (visibles > 1 ? "s" : "") + " sur " + total + " correspond" + (visibles > 1 ? "ent" : "") + " à votre recherche"
        : total + " plats à la carte";
    }
    var cp = $("#compte-plats");
    if (cp) cp.textContent = total + " plats · " + cats.length + " catégories";

    // compteurs des chips
    $$(".chip").forEach(function (ch) {
      var id = ch.getAttribute("data-cat"), n;
      var sauf = { q: etat.q, cat: "tout", vege: etat.vege, sansAllerg: etat.sansAllerg };
      var memo = etat; etat = sauf;
      n = id === "tout" ? (MENU.plats || []).filter(correspond).length
                        : (MENU.plats || []).filter(function (p) { return p.categorie === id; }).filter(correspond).length;
      etat = memo;
      var span = $(".n", ch);
      if (span) span.textContent = n;
      ch.disabled = n === 0 && id !== "tout" && etat.cat !== id;
      ch.style.opacity = ch.disabled ? ".45" : "";
    });
  };

  var construireFiltres = function () {
    // categories
    var chips = $("#chips");
    var items = [{ id: "tout", nom: "Tout" }].concat((MENU.categories || []).map(function (c) { return { id: c.id, nom: c.nom }; }));
    chips.innerHTML = items.map(function (c) {
      return '<button class="chip" type="button" role="tab" data-cat="' + esc(c.id) + '"'
        + ' aria-selected="' + (c.id === etat.cat) + '">' + esc(c.nom) + ' <span class="n"></span></button>';
    }).join("");
    chips.addEventListener("click", function (e) {
      var b = e.target.closest(".chip");
      if (!b) return;
      etat.cat = b.getAttribute("data-cat");
      $$(".chip", chips).forEach(function (c) { c.setAttribute("aria-selected", String(c === b)); });
      b.scrollIntoView({ inline: "center", block: "nearest", behavior: "smooth" });
      dessiner();
    });

    // allergenes reellement presents a la carte
    var sel = $("#f-allerg");
    var presents = {};
    (MENU.plats || []).forEach(function (p) { (p.allergenes || []).forEach(function (a) { presents[a] = true; }); });
    Object.keys(presents).sort().forEach(function (a) {
      var o = document.createElement("option");
      o.value = a;
      o.textContent = "Sans " + ((MENU.allergenes && MENU.allergenes[a]) || a).toLowerCase();
      sel.appendChild(o);
    });
    sel.addEventListener("change", function () { etat.sansAllerg = sel.value; dessiner(); });

    // recherche
    var q = $("#q"), vider = $("#vider-q"), minuteur = null;
    q.addEventListener("input", function () {
      vider.hidden = !q.value;
      clearTimeout(minuteur);
      minuteur = setTimeout(function () { etat.q = q.value.trim(); dessiner(); }, 120);
    });
    vider.addEventListener("click", function () { q.value = ""; vider.hidden = true; etat.q = ""; dessiner(); q.focus(); });

    // vegetarien
    $("#f-vege").addEventListener("change", function (e) { etat.vege = e.target.checked; dessiner(); });

    // reinitialisation
    $("#reinit").addEventListener("click", function () {
      etat = { q: "", cat: "tout", vege: false, sansAllerg: "" };
      q.value = ""; vider.hidden = true; $("#f-vege").checked = false; sel.value = "";
      $$(".chip").forEach(function (c) { c.setAttribute("aria-selected", String(c.getAttribute("data-cat") === "tout")); });
      dessiner();
      $("#q").focus();
    });
  };

  /* ==================== 4. QR code ==================== */
  var modale = $("#modale-qr");
  if (modale && window.QR) {
    var canvas = $("#qr-canvas"), champUrl = $("#qr-url"), champTable = $("#qr-table");
    var etatQr = $("#qr-etat"), sous = $("#qr-sous"), dernierFocus = null;

    var rendre = function () {
      var url = champUrl.value.trim();
      etatQr.removeAttribute("data-erreur");
      if (!url) { etatQr.textContent = "Indiquez l’adresse à encoder."; etatQr.setAttribute("data-erreur", "1"); return; }
      try {
        var m = window.QR.dessiner(canvas, url, { px: 460, marge: 4, sombre: "#10151f", clair: "#ffffff" });
        etatQr.textContent = "Version " + m.version + " · " + m.size + "×" + m.size + " modules · correction d’erreur M (15 %)";
        sous.textContent = champTable.value.trim() || "Scannez pour voir la carte";
      } catch (err) {
        etatQr.textContent = "Adresse trop longue pour un QR code lisible. Raccourcissez-la.";
        etatQr.setAttribute("data-erreur", "1");
      }
    };

    var ouvrir = function () {
      dernierFocus = document.activeElement;
      modale.hidden = false;
      document.body.classList.add("modale-ouverte");
      rendre();
      var premier = $(".modale-x", modale);
      if (premier) premier.focus();
    };
    var fermer = function () {
      modale.hidden = true;
      document.body.classList.remove("modale-ouverte");
      if (dernierFocus) dernierFocus.focus();
    };

    $("#ouvrir-qr").addEventListener("click", ouvrir);
    modale.addEventListener("click", function (e) { if (e.target.hasAttribute("data-fermer")) fermer(); });
    document.addEventListener("keydown", function (e) {
      if (modale.hidden) return;
      if (e.key === "Escape") { fermer(); return; }
      if (e.key !== "Tab") return;
      var f = $$('button, [href], input, select, textarea', modale).filter(function (el) { return !el.disabled && el.offsetParent !== null; });
      if (!f.length) return;
      var premier = f[0], dernier = f[f.length - 1];
      if (e.shiftKey && document.activeElement === premier) { e.preventDefault(); dernier.focus(); }
      else if (!e.shiftKey && document.activeElement === dernier) { e.preventDefault(); premier.focus(); }
    });

    champUrl.addEventListener("input", rendre);
    champTable.addEventListener("input", function () { sous.textContent = champTable.value.trim() || "Scannez pour voir la carte"; });

    $("#qr-png").addEventListener("click", function () {
      var a = document.createElement("a");
      a.download = "qr-la-casa-demir" + (champTable.value.trim() ? "-" + champTable.value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-") : "") + ".png";
      a.href = canvas.toDataURL("image/png");
      a.click();
    });
    $("#qr-print").addEventListener("click", function () {
      document.body.classList.add("impression-qr");
      window.print();
      setTimeout(function () { document.body.classList.remove("impression-qr"); }, 400);
    });
  }

  /* ==================== 5. demarrage ==================== */
  charger(function (menu) {
    if (!menu || !menu.plats) {
      cible.innerHTML = '<p class="vide"><strong>Carte momentanément indisponible.</strong>'
        + "<span>Le fichier menu.json n’a pas pu être lu.</span></p>";
      return;
    }
    MENU = menu;
    (MENU.categories || []).forEach(function (c) { LIB[c.id] = c.nom; });
    construireFiltres();
    dessiner();
  });
})();
