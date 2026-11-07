/* La Casa Demir — comportements de page. JS vanilla, aucune dependance.
   Genere le 2026-11-06 par Studio Cas Machuine.
   Les horaires sont lus dans le HTML (data-jour / data-creneaux) : une seule source de verite. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- 1. menu mobile ---------- */
  var burger = $("#burger"), nav = $("#nav-principal");
  if (burger && nav) {
    var basculer = function (ouvrir) {
      var o = typeof ouvrir === "boolean" ? ouvrir : burger.getAttribute("aria-expanded") !== "true";
      burger.setAttribute("aria-expanded", String(o));
      nav.classList.toggle("ouvert", o);
      $(".sr", burger).textContent = o ? "Fermer le menu" : "Ouvrir le menu";
    };
    burger.addEventListener("click", function () { basculer(); });
    nav.addEventListener("click", function (e) { if (e.target.closest("a")) basculer(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") basculer(false); });
    window.addEventListener("resize", function () { if (window.innerWidth >= 860) basculer(false); });
  }

  /* ---------- 2. ombre d'entete au defilement ---------- */
  var entete = $("#entete");
  if (entete) {
    var majEntete = function () { entete.classList.toggle("colle", window.scrollY > 8); };
    majEntete();
    window.addEventListener("scroll", majEntete, { passive: true });
  }

  /* ---------- 3. apparition progressive ---------- */
  var cibles = $$(".bloc-tete, .carte, .fiche, .citation, .chiffres, .panneau, .form, .apropos-txt");
  if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
    cibles.forEach(function (el, i) {
      el.classList.add("reveal");
      el.style.transitionDelay = Math.min(i % 3, 2) * 70 + "ms";
    });
    var obs = new IntersectionObserver(function (entrees) {
      entrees.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("vu"); obs.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    cibles.forEach(function (el) { obs.observe(el); });
  }

  /* ---------- 4. horaires : jour en cours + ouvert/ferme ---------- */
  var JOURS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
  var lignes = $$("#liste-horaires li");

  var minutes = function (hhmm) {
    var p = hhmm.split(":");
    return parseInt(p[0], 10) * 60 + parseInt(p[1] || "0", 10);
  };
  var creneaux = function (li) {
    var brut = (li.getAttribute("data-creneaux") || "").trim();
    if (!brut) return [];
    return brut.split(",").map(function (c) {
      var b = c.split("-");
      return { d: minutes(b[0]), f: minutes(b[1]) };
    });
  };
  var hhmm = function (m) {
    var h = Math.floor(m / 60), mi = m % 60;
    return h + "h" + (mi ? ("0" + mi).slice(-2) : "");
  };
  var lisible = function (li) {
    var h = $(".heures", li);
    return h ? h.textContent.trim() : "";
  };

  if (lignes.length) {
    var now = new Date();
    var jourJs = now.getDay();                      // 0 = dimanche
    var jourIso = jourJs === 0 ? 7 : jourJs;        // 1 = lundi … 7 = dimanche
    var mnt = now.getHours() * 60 + now.getMinutes();

    var ligneDuJour = null;
    lignes.forEach(function (li) {
      if (parseInt(li.getAttribute("data-jour"), 10) === jourIso) {
        li.classList.add("aujourdhui");
        ligneDuJour = li;
      }
    });

    var etat = "ferme", texte = "Fermé aujourd’hui", suite = "";
    if (ligneDuJour) {
      var cr = creneaux(ligneDuJour);
      var ouvert = cr.some(function (c) { return mnt >= c.d && mnt < c.f; });
      if (ouvert) {
        etat = "ouvert";
        var courant = cr.filter(function (c) { return mnt >= c.d && mnt < c.f; })[0];
        texte = "Ouvert maintenant";
        suite = "jusqu’à " + hhmm(courant.f);
      } else {
        var aVenir = cr.filter(function (c) { return c.d > mnt; })[0];
        if (aVenir) {
          texte = "Fermé — ouvre à " + hhmm(aVenir.d);
        } else {
          // prochain jour ouvre
          for (var i = 1; i <= 7; i++) {
            var cible = ((jourIso - 1 + i) % 7) + 1;
            var li2 = lignes.filter(function (l) { return parseInt(l.getAttribute("data-jour"), 10) === cible; })[0];
            if (li2 && creneaux(li2).length) {
              var c0 = creneaux(li2)[0];
              texte = "Fermé — ouvre " + (i === 1 ? "demain" : JOURS[cible % 7]) + " à " + hhmm(c0.d);
              break;
            }
          }
        }
      }
    }

    var badge = $("#statut-ouvert"), badgeTxt = $("#statut-texte");
    if (badge && badgeTxt) {
      badge.setAttribute("data-etat", etat);
      badgeTxt.textContent = texte;
      if (suite) badge.setAttribute("title", texte + " " + suite);
    }
    var ddJour = $("#horaire-jour");
    if (ddJour) {
      var hj = ligneDuJour ? lisible(ligneDuJour) : "—";
      ddJour.textContent = JOURS[jourJs].charAt(0).toUpperCase() + JOURS[jourJs].slice(1) + " : " + (hj || "fermé");
    }
  }

  /* ---------- 5. formulaire : validation inline, pas de dependance ---------- */
  var form = $("#form-contact");
  if (form) {
    var retour = $("#form-retour");
    var regles = {
      "f-nom": function (v) { return v.trim().length >= 2; },
      "f-mail": function (v) { return /^[^\s@]+@[^\s@]+\.[a-z]{2,}$/i.test(v.trim()); },
      "f-tel": function (v) { return v.trim() === "" || v.replace(/[^0-9+]/g, "").length >= 9; },
      "f-msg": function (v) { return v.trim().length >= 5; }
    };
    var verifier = function (id) {
      var champ = $("#" + id);
      if (!champ) return true;
      var ok = regles[id](champ.value);
      var bloc = champ.closest(".champ");
      var msg = $('.err[data-pour="' + id + '"]');
      if (bloc) bloc.setAttribute("data-erreur", ok ? "0" : "1");
      if (msg) msg.hidden = ok;
      champ.setAttribute("aria-invalid", ok ? "false" : "true");
      return ok;
    };
    Object.keys(regles).forEach(function (id) {
      var champ = $("#" + id);
      if (!champ) return;
      champ.addEventListener("blur", function () { verifier(id); });
      champ.addEventListener("input", function () {
        if (champ.closest(".champ") && champ.closest(".champ").getAttribute("data-erreur") === "1") verifier(id);
      });
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var ok = Object.keys(regles).map(verifier).every(Boolean);
      if (!ok) {
        var premier = $('.champ[data-erreur="1"] input, .champ[data-erreur="1"] textarea');
        if (premier) premier.focus();
        if (retour) { retour.hidden = true; }
        return;
      }
      if (retour) {
        retour.hidden = false;
        retour.textContent = "Merci, votre demande est bien notée. Nous revenons vers vous sous 48 heures ouvrées.";
        retour.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
      form.reset();
    });
  }
})();
