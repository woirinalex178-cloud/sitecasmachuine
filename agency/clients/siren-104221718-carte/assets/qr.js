/* ============================================================================
   qr.js — generateur de QR code 100 % local (aucune API, aucune dependance).
   Mode octet (UTF-8), correction d'erreur niveau M, versions 1 a 10,
   choix automatique de la version et du masque (penalites normalisees ISO 18004).

   API :
     QR.matrix(texte)                 -> { size, data: [[bool,...]] }
     QR.dessiner(canvas, texte, opts) -> dessine le code (opts: marge, echelle, clair, sombre)
   ========================================================================== */
(function (global) {
  "use strict";

  /* --- tables niveau M, versions 1..10 --- */
  var ECC_PAR_BLOC = [10, 16, 26, 18, 24, 16, 18, 22, 22, 26];
  var NB_BLOCS     = [ 1,  1,  1,  2,  2,  4,  4,  4,  5,  5];
  var P_N1 = 3, P_N2 = 3, P_N3 = 40, P_N4 = 10;

  /* --- corps de Galois GF(256), polynome primitif 0x11D --- */
  var EXP = new Uint8Array(512), LOG = new Uint8Array(256);
  (function () {
    var x = 1;
    for (var i = 0; i < 255; i++) {
      EXP[i] = x; LOG[x] = i;
      x <<= 1;
      if (x & 0x100) x ^= 0x11D;
    }
    for (var j = 255; j < 512; j++) EXP[j] = EXP[j - 255];
  })();
  function mul(a, b) { return (a === 0 || b === 0) ? 0 : EXP[LOG[a] + LOG[b]]; }

  function diviseurRS(degre) {
    var res = new Uint8Array(degre);
    res[degre - 1] = 1;
    var racine = 1;
    for (var i = 0; i < degre; i++) {
      for (var j = 0; j < degre; j++) {
        res[j] = mul(res[j], racine);
        if (j + 1 < degre) res[j] ^= res[j + 1];
      }
      racine = mul(racine, 0x02);
    }
    return res;
  }
  function resteRS(donnees, div) {
    var res = new Uint8Array(div.length);
    for (var i = 0; i < donnees.length; i++) {
      var facteur = donnees[i] ^ res[0];
      res.copyWithin(0, 1);
      res[res.length - 1] = 0;
      for (var j = 0; j < div.length; j++) res[j] ^= mul(div[j], facteur);
    }
    return Array.prototype.slice.call(res);
  }

  /* --- geometrie --- */
  function modulesBruts(ver) {
    var r = (16 * ver + 128) * ver + 64;
    if (ver >= 2) {
      var n = Math.floor(ver / 7) + 2;
      r -= (25 * n - 10) * n - 55;
      if (ver >= 7) r -= 36;
    }
    return r;
  }
  function totalMots(ver) { return Math.floor(modulesBruts(ver) / 8); }
  function motsDonnees(ver) { return totalMots(ver) - ECC_PAR_BLOC[ver - 1] * NB_BLOCS[ver - 1]; }
  function bitsCompteur(ver) { return ver <= 9 ? 8 : 16; }
  function positionsAlignement(ver) {
    if (ver === 1) return [];
    var taille = ver * 4 + 17;
    var nb = Math.floor(ver / 7) + 2;
    var pas = Math.ceil((ver * 4 + 4) / (nb * 2 - 2)) * 2;
    var res = [6];
    for (var pos = taille - 7; res.length < nb; pos -= pas) res.splice(1, 0, pos);
    return res;
  }

  /* --- texte -> octets UTF-8 --- */
  function octets(txt) {
    if (global.TextEncoder) return Array.prototype.slice.call(new global.TextEncoder().encode(txt));
    var out = [], esc = encodeURIComponent(txt);
    for (var i = 0; i < esc.length; i++) {
      if (esc.charAt(i) === "%") { out.push(parseInt(esc.substr(i + 1, 2), 16)); i += 2; }
      else out.push(esc.charCodeAt(i));
    }
    return out;
  }

  function bit(valeur, i) { return ((valeur >>> i) & 1) !== 0; }

  /* ---------------------------- construction ---------------------------- */
  function matrix(texte, opts) {
    opts = opts || {};
    var oct = octets(String(texte));
    var ver = 0;
    for (var v = 1; v <= 10; v++) {
      var capacite = motsDonnees(v) * 8 - 4 - bitsCompteur(v);
      if (oct.length * 8 <= capacite) { ver = v; break; }
    }
    if (!ver) throw new Error("Contenu trop long pour un QR code version 10 (niveau M).");

    /* 1. flux de bits */
    var bits = [];
    var pousse = function (val, n) { for (var i = n - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
    pousse(0x4, 4);                        // mode octet
    pousse(oct.length, bitsCompteur(ver)); // compteur de caracteres
    for (var i = 0; i < oct.length; i++) pousse(oct[i], 8);

    var capaBits = motsDonnees(ver) * 8;
    pousse(0, Math.min(4, capaBits - bits.length));          // terminateur
    pousse(0, (8 - bits.length % 8) % 8);                    // alignement octet
    for (var pad = 0xEC; bits.length < capaBits; pad ^= 0xEC ^ 0x11) pousse(pad, 8);

    var donnees = [];
    for (var b = 0; b < bits.length; b += 8) {
      var mot = 0;
      for (var k = 0; k < 8; k++) mot = (mot << 1) | bits[b + k];
      donnees.push(mot);
    }

    /* 2. blocs + correction d'erreur, puis entrelacement */
    var nbBlocs = NB_BLOCS[ver - 1], eccLen = ECC_PAR_BLOC[ver - 1];
    var brut = totalMots(ver);
    var nbCourts = nbBlocs - brut % nbBlocs;
    var lenCourt = Math.floor(brut / nbBlocs);
    var div = diviseurRS(eccLen);
    var blocs = [];
    for (var ib = 0, curseur = 0; ib < nbBlocs; ib++) {
      var lenDat = lenCourt - eccLen + (ib < nbCourts ? 0 : 1);
      var dat = donnees.slice(curseur, curseur + lenDat);
      curseur += lenDat;
      var ecc = resteRS(dat, div);
      if (ib < nbCourts) dat = dat.concat([0]);  // octet fictif, saute a l'entrelacement
      blocs.push(dat.concat(ecc));
    }
    var flux = [];
    for (var ii = 0; ii < blocs[0].length; ii++) {
      for (var jj = 0; jj < blocs.length; jj++) {
        if (ii !== lenCourt - eccLen || jj >= nbCourts) flux.push(blocs[jj][ii]);
      }
    }

    /* 3. grille */
    var taille = ver * 4 + 17;
    var mods = [], fonc = [];
    for (var y = 0; y < taille; y++) {
      mods.push(new Array(taille).fill(false));
      fonc.push(new Array(taille).fill(false));
    }
    var poser = function (x, y, noir) {
      if (x < 0 || y < 0 || x >= taille || y >= taille) return;
      mods[y][x] = noir; fonc[y][x] = true;
    };

    // reperes de synchronisation
    for (var t = 0; t < taille; t++) { poser(6, t, t % 2 === 0); poser(t, 6, t % 2 === 0); }
    // motifs de detection de position
    [[3, 3], [taille - 4, 3], [3, taille - 4]].forEach(function (c) {
      for (var dy = -4; dy <= 4; dy++) for (var dx = -4; dx <= 4; dx++) {
        var d = Math.max(Math.abs(dx), Math.abs(dy));
        poser(c[0] + dx, c[1] + dy, d !== 2 && d !== 4);
      }
    });
    // motifs d'alignement
    var pa = positionsAlignement(ver);
    for (var a = 0; a < pa.length; a++) for (var bq = 0; bq < pa.length; bq++) {
      if ((a === 0 && bq === 0) || (a === 0 && bq === pa.length - 1) || (a === pa.length - 1 && bq === 0)) continue;
      for (var ady = -2; ady <= 2; ady++) for (var adx = -2; adx <= 2; adx++) {
        poser(pa[a] + adx, pa[bq] + ady, Math.max(Math.abs(adx), Math.abs(ady)) !== 1);
      }
    }

    var posFormat = function (masque) {
      var d = (0 << 3) | masque;                 // niveau M = 0
      var reste = d;
      for (var z = 0; z < 10; z++) reste = (reste << 1) ^ ((reste >>> 9) * 0x537);
      var f = ((d << 10) | reste) ^ 0x5412;
      for (var p = 0; p <= 5; p++) poser(8, p, bit(f, p));
      poser(8, 7, bit(f, 6)); poser(8, 8, bit(f, 7)); poser(7, 8, bit(f, 8));
      for (var q = 9; q < 15; q++) poser(14 - q, 8, bit(f, q));
      for (var r = 0; r < 8; r++) poser(taille - 1 - r, 8, bit(f, r));
      for (var s = 8; s < 15; s++) poser(8, taille - 15 + s, bit(f, s));
      poser(8, taille - 8, true);                // module noir obligatoire
    };
    posFormat(0);

    if (ver >= 7) {                              // information de version
      var rv = ver;
      for (var w = 0; w < 12; w++) rv = (rv << 1) ^ ((rv >>> 11) * 0x1F25);
      var bv = (ver << 12) | rv;
      for (var n = 0; n < 18; n++) {
        var noir = bit(bv, n), aa = taille - 11 + n % 3, bb = Math.floor(n / 3);
        poser(aa, bb, noir); poser(bb, aa, noir);
      }
    }

    /* 4. placement des mots de code en zigzag */
    var idx = 0;
    for (var droite = taille - 1; droite >= 1; droite -= 2) {
      if (droite === 6) droite = 5;
      for (var vert = 0; vert < taille; vert++) {
        for (var dj = 0; dj < 2; dj++) {
          var xx = droite - dj;
          var monte = ((droite + 1) & 2) === 0;
          var yy = monte ? taille - 1 - vert : vert;
          if (!fonc[yy][xx] && idx < flux.length * 8) {
            mods[yy][xx] = bit(flux[idx >>> 3], 7 - (idx & 7));
            idx++;
          }
        }
      }
    }

    /* 5. masque : on garde celui qui minimise les penalites */
    var MASQUES = [
      function (x, y) { return (x + y) % 2 === 0; },
      function (x, y) { return y % 2 === 0; },
      function (x) { return x % 3 === 0; },
      function (x, y) { return (x + y) % 3 === 0; },
      function (x, y) { return (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0; },
      function (x, y) { return (x * y) % 2 + (x * y) % 3 === 0; },
      function (x, y) { return ((x * y) % 2 + (x * y) % 3) % 2 === 0; },
      function (x, y) { return ((x + y) % 2 + (x * y) % 3) % 2 === 0; }
    ];
    var appliquer = function (m) {
      for (var y2 = 0; y2 < taille; y2++) for (var x2 = 0; x2 < taille; x2++) {
        if (!fonc[y2][x2] && MASQUES[m](x2, y2)) mods[y2][x2] = !mods[y2][x2];
      }
    };

    var ajoutHist = function (longueur, hist) {
      if (hist[0] === 0) longueur += taille;
      hist.pop(); hist.unshift(longueur);
    };
    var compteMotifs = function (hist) {
      var n = hist[1];
      var noyau = n > 0 && hist[2] === n && hist[3] === n * 3 && hist[4] === n && hist[5] === n;
      return (noyau && hist[0] >= n * 4 && hist[6] >= n ? 1 : 0)
           + (noyau && hist[6] >= n * 4 && hist[0] >= n ? 1 : 0);
    };
    var cloture = function (couleur, longueur, hist) {
      if (couleur) { ajoutHist(longueur, hist); longueur = 0; }
      longueur += taille;
      ajoutHist(longueur, hist);
      return compteMotifs(hist);
    };
    var penalite = function () {
      var res = 0, x3, y3;
      for (y3 = 0; y3 < taille; y3++) {
        var cR = false, lR = 0, hR = [0, 0, 0, 0, 0, 0, 0];
        for (x3 = 0; x3 < taille; x3++) {
          if (mods[y3][x3] === cR) { lR++; if (lR === 5) res += P_N1; else if (lR > 5) res++; }
          else {
            ajoutHist(lR, hR);
            if (!cR) res += compteMotifs(hR) * P_N3;
            cR = mods[y3][x3]; lR = 1;
          }
        }
        res += cloture(cR, lR, hR) * P_N3;
      }
      for (x3 = 0; x3 < taille; x3++) {
        var cC = false, lC = 0, hC = [0, 0, 0, 0, 0, 0, 0];
        for (y3 = 0; y3 < taille; y3++) {
          if (mods[y3][x3] === cC) { lC++; if (lC === 5) res += P_N1; else if (lC > 5) res++; }
          else {
            ajoutHist(lC, hC);
            if (!cC) res += compteMotifs(hC) * P_N3;
            cC = mods[y3][x3]; lC = 1;
          }
        }
        res += cloture(cC, lC, hC) * P_N3;
      }
      for (y3 = 0; y3 < taille - 1; y3++) for (x3 = 0; x3 < taille - 1; x3++) {
        var c = mods[y3][x3];
        if (c === mods[y3][x3 + 1] && c === mods[y3 + 1][x3] && c === mods[y3 + 1][x3 + 1]) res += P_N2;
      }
      var noirs = 0;
      for (y3 = 0; y3 < taille; y3++) for (x3 = 0; x3 < taille; x3++) if (mods[y3][x3]) noirs++;
      var tot = taille * taille;
      res += (Math.ceil(Math.abs(noirs * 20 - tot * 10) / tot) - 1) * P_N4;
      return res;
    };

    var meilleur = -1, meilleurScore = Infinity;
    if (opts.masque != null) {                      // masque impose (tests / debogage)
      meilleur = opts.masque;
    } else {
      for (var m2 = 0; m2 < 8; m2++) {
        appliquer(m2); posFormat(m2);
        var sc = penalite();
        if (sc < meilleurScore) { meilleurScore = sc; meilleur = m2; }
        appliquer(m2);                              // on annule (XOR involutif)
      }
    }
    appliquer(meilleur); posFormat(meilleur);

    return { size: taille, version: ver, masque: meilleur, data: mods };
  }

  /* ---------------------------- rendu canvas ---------------------------- */
  function dessiner(canvas, texte, opts) {
    opts = opts || {};
    var m = matrix(texte);
    var marge = opts.marge == null ? 4 : opts.marge;            // zone de silence : 4 modules mini
    var cote = m.size + marge * 2;
    var echelle = Math.max(1, Math.floor((opts.px || 560) / cote));
    var px = cote * echelle;
    var ratio = opts.ratio || (global.devicePixelRatio || 1);

    canvas.width = Math.round(px * ratio);
    canvas.height = Math.round(px * ratio);
    canvas.style.width = px + "px";
    canvas.style.height = px + "px";

    var ctx = canvas.getContext("2d");
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.fillStyle = opts.clair || "#ffffff";
    ctx.fillRect(0, 0, px, px);
    ctx.fillStyle = opts.sombre || "#000000";
    for (var y = 0; y < m.size; y++) for (var x = 0; x < m.size; x++) {
      if (m.data[y][x]) ctx.fillRect((x + marge) * echelle, (y + marge) * echelle, echelle, echelle);
    }
    return m;
  }

  global.QR = { matrix: matrix, dessiner: dessiner };
})(typeof window !== "undefined" ? window : this);
