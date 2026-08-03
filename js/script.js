/* =========================================================
   ClairArgent — outils
   Tous les calculs tournent dans le navigateur.
   Aucune donnée n'est envoyée ni stockée.
   ========================================================= */

const eur = n => Math.round(n).toLocaleString('fr-FR') + ' €';
const num = id => parseFloat(document.getElementById(id).value) || 0;

function alerteChamp(id){
  const c = document.getElementById(id);
  c.focus();
  c.style.borderColor = '#f5b544';
  setTimeout(() => { c.style.borderColor = ''; }, 1600);
}

function animerNombre(el, cible){
  const finale = Math.round(cible).toLocaleString('fr-FR') + ' €';
  const duree = 900, debut = performance.now();
  let termine = false;

  function frame(now){
    const p = Math.min((now - debut) / duree, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(cible * eased).toLocaleString('fr-FR') + ' €';
    if(p < 1) requestAnimationFrame(frame);
    else termine = true;
  }

  if(typeof requestAnimationFrame === 'function') requestAnimationFrame(frame);

  // Filet de sécurité : si l'animation ne tourne pas (onglet en arrière-plan,
  // mode économie d'énergie), on force l'affichage de la valeur finale.
  setTimeout(() => { if(!termine) el.textContent = finale; }, 1000);
}

function afficher(id){
  const box = document.getElementById(id);
  box.classList.add('show');
}

/* ---------- 1. Budget 50/30/20 ---------- */
function calculerBudget(){
  const revenu = num('revenu');
  if(revenu <= 0) return alerteChamp('revenu');

  const taux = num('taux'), annees = num('annees');
  const besoins = revenu * 0.5, envies = revenu * 0.3, epargne = revenu * 0.2;

  const tm = (taux / 100) / 12, mois = annees * 12;
  const capital = tm > 0 ? epargne * ((Math.pow(1 + tm, mois) - 1) / tm) : epargne * mois;
  const verse = epargne * mois;

  document.getElementById('res-besoins').textContent  = eur(besoins);
  document.getElementById('res-envies').textContent   = eur(envies);
  document.getElementById('res-epargne').textContent  = eur(epargne);
  document.getElementById('res-verse').textContent    = eur(verse);
  document.getElementById('res-interets').textContent = eur(capital - verse);

  afficher('tool-result');
  requestAnimationFrame(() => {
    document.getElementById('bar-besoins').style.width = '50%';
    document.getElementById('bar-envies').style.width  = '30%';
    document.getElementById('bar-epargne').style.width = '20%';
  });
  animerNombre(document.getElementById('res-capital'), capital);
}

/* ---------- 2. Charges micro-entreprise ---------- */
let activiteChoisie = 21.2; // services BIC par défaut

function choisirActivite(btn, taux){
  document.querySelectorAll('#seg-activite .seg').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activiteChoisie = taux;
  document.getElementById('taux-cotis').value = taux;
}

function calculerCharges(){
  const ca = num('ca-mensuel');
  if(ca <= 0) return alerteChamp('ca-mensuel');

  const tauxCotis = num('taux-cotis');
  const tauxImpot = num('taux-impot');

  const cotisations = ca * (tauxCotis / 100);
  const impot = ca * (tauxImpot / 100);
  const net = ca - cotisations - impot;
  const partGardee = (net / ca) * 100;

  document.getElementById('ch-cotis').textContent  = eur(cotisations);
  document.getElementById('ch-impot').textContent  = eur(impot);
  document.getElementById('ch-annuel').textContent = eur((cotisations + impot) * 12);
  document.getElementById('ch-pct').textContent    = Math.round(partGardee) + ' %';

  afficher('charges-result');
  requestAnimationFrame(() => {
    document.getElementById('bar-net').style.width    = partGardee + '%';
    document.getElementById('bar-cotis').style.width  = (cotisations / ca * 100) + '%';
    document.getElementById('bar-impot').style.width  = (impot / ca * 100) + '%';
  });
  animerNombre(document.getElementById('ch-net'), net);
}

/* ---------- 3. TJM freelance ---------- */
function calculerTJM(){
  const objectif = num('objectif-net');
  if(objectif <= 0) return alerteChamp('objectif-net');

  const joursMois = num('jours-mois');
  const tauxCharges = num('tjm-charges');
  const fraisMensuels = num('frais-mensuels');

  if(joursMois <= 0) return alerteChamp('jours-mois');

  // CA nécessaire pour obtenir l'objectif net après charges et frais
  const caNecessaire = (objectif + fraisMensuels) / (1 - tauxCharges / 100);
  const tjm = caNecessaire / joursMois;

  document.getElementById('tjm-ca').textContent      = eur(caNecessaire);
  document.getElementById('tjm-annuel').textContent  = eur(caNecessaire * 12);
  document.getElementById('tjm-charges-m').textContent = eur(caNecessaire * (tauxCharges / 100));
  document.getElementById('tjm-horaire').textContent = eur(tjm / 7);

  afficher('tjm-result');
  animerNombre(document.getElementById('tjm-val'), tjm);
}

/* ---------- 4. Objectif épargne ---------- */
function calculerObjectif(){
  const cible = num('obj-montant');
  if(cible <= 0) return alerteChamp('obj-montant');

  const dejaEpargne = num('obj-deja');
  const annees = num('obj-annees');
  const taux = num('obj-taux');

  if(annees <= 0) return alerteChamp('obj-annees');

  const mois = annees * 12;
  const tm = (taux / 100) / 12;

  // Valeur future du capital déjà placé
  const futurDeja = dejaEpargne * Math.pow(1 + tm, mois);
  const restant = Math.max(cible - futurDeja, 0);

  // Versement mensuel nécessaire
  const mensuel = tm > 0
    ? restant / ((Math.pow(1 + tm, mois) - 1) / tm)
    : restant / mois;

  const totalVerse = mensuel * mois;
  const interets = cible - totalVerse - dejaEpargne;

  document.getElementById('obj-total').textContent    = eur(totalVerse);
  document.getElementById('obj-interets').textContent = eur(Math.max(interets, 0));
  document.getElementById('obj-futur-deja').textContent = eur(futurDeja);

  const atteint = document.getElementById('obj-atteint');
  if(restant <= 0){
    atteint.textContent = "Ton capital actuel suffit déjà à atteindre l'objectif sur cette durée.";
    atteint.style.display = 'block';
  } else {
    atteint.style.display = 'none';
  }

  afficher('obj-result');
  animerNombre(document.getElementById('obj-mensuel'), mensuel);
}

/* =========================================================
   NEWSLETTER
   ---------------------------------------------------------
   Pour activer la collecte automatique des emails, colle
   ci-dessous l'URL de ton formulaire (Formspree, Buttondown,
   Brevo, n8n webhook public...). Exemple :
   const NEWSLETTER_ENDPOINT = "https://formspree.io/f/xxxxxxx";

   Tant que la valeur reste vide, le formulaire bascule sur
   l'envoi d'un email pré-rempli : ça fonctionne dès maintenant,
   sans aucun compte à créer.
   ========================================================= */
const NEWSLETTER_ENDPOINT = "";
const NEWSLETTER_EMAIL    = "woirinalex178@gmail.com";

function messageNewsletter(type, texte){
  const box = document.getElementById('nl-msg');
  if(!box) return;
  box.className = 'nl-msg show ' + type;
  box.textContent = texte;
}

async function inscrireNewsletter(event){
  if(event) event.preventDefault();

  const champ = document.getElementById('nl-email');
  if(!champ) return false;

  const email = champ.value.trim();
  const valide = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);

  if(!valide){
    messageNewsletter('err', "Cette adresse email ne semble pas valide. Vérifie la saisie.");
    champ.focus();
    return false;
  }

  const bouton = document.getElementById('nl-btn');
  const libelle = bouton ? bouton.textContent : '';
  if(bouton){ bouton.disabled = true; bouton.textContent = 'Envoi...'; }

  try {
    if(NEWSLETTER_ENDPOINT){
      const rep = await fetch(NEWSLETTER_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ email, source: 'clairargent', date: new Date().toISOString() })
      });
      if(!rep.ok) throw new Error('reponse ' + rep.status);
      messageNewsletter('ok', "C'est noté. Tu recevras le prochain récap dès sa parution.");
      champ.value = '';
    } else {
      // Mode sans backend : ouvre le client mail avec un message pré-rempli
      const sujet = encodeURIComponent('Inscription newsletter ClairArgent');
      const corps  = encodeURIComponent(
        "Bonjour,\n\nJe souhaite m'inscrire à la newsletter ClairArgent.\n\nEmail : " + email + "\n"
      );
      window.location.href = 'mailto:' + NEWSLETTER_EMAIL + '?subject=' + sujet + '&body=' + corps;
      messageNewsletter('ok', "Ton logiciel de messagerie s'ouvre : il ne reste qu'à envoyer l'email.");
    }
  } catch(err){
    messageNewsletter('err', "L'envoi a échoué. Réessaie dans un moment, ou écris directement à " + NEWSLETTER_EMAIL + ".");
  } finally {
    if(bouton){ bouton.disabled = false; bouton.textContent = libelle; }
  }

  return false;
}

/* ---------- Apparition au scroll + raccourcis clavier ---------- */
document.addEventListener('DOMContentLoaded', () => {
  const cibles = document.querySelectorAll('.reveal');
  if(!('IntersectionObserver' in window)){
    cibles.forEach(el => el.classList.add('visible'));
  } else {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if(entry.isIntersecting){
          setTimeout(() => entry.target.classList.add('visible'), i * 80);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });
    cibles.forEach(el => obs.observe(el));
  }

  // Entrée = lance le calcul du bloc courant
  document.querySelectorAll('.tool-shell').forEach(shell => {
    const bouton = shell.querySelector('button.btn');
    shell.querySelectorAll('input').forEach(input => {
      input.addEventListener('keydown', e => {
        if(e.key === 'Enter' && bouton) bouton.click();
      });
    });
  });

  // Newsletter : soumission au clavier et au clic
  const nlForm = document.getElementById('nl-form');
  if(nlForm) nlForm.addEventListener('submit', inscrireNewsletter);
});
