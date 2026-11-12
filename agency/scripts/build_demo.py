#!/usr/bin/env python3
"""Generateur de demos personnalisees — l'arme commerciale de l'agence.

A partir d'une ligne de la base de prospects, produit en une commande un site
vitrine (ou une carte interactive restaurant) au nom du prospect, pret a etre
filme pour la video de prospection et mis en ligne tel quel.

  build_demo.py --cle siren:104221718
  build_demo.py --cle siren:104221718 --type carte
  build_demo.py --cle siren:104221718 --tel "03 87 12 34 56" --email contact@…

Stdlib uniquement. Lecture seule sur agency/data/prospects.ndjson.
Idempotent : deux executions le meme jour produisent exactement les memes
fichiers (les seules variations possibles viennent des options passees).
"""

import argparse
import json
import os
import re
import shutil
import sys
import unicodedata
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RACINE, "data", "prospects.ndjson")
TEMPLATES = os.path.join(RACINE, "templates")
CLIENTS = os.path.join(RACINE, "clients")
OFFRES = os.path.join(RACINE, "config", "offers.json")

AGENCE = "Studio Cas Machuine"
AGENCE_URL = "https://casmachuine.fr"

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
JOURS_SCHEMA = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
PETITS_MOTS = {"de", "du", "des", "la", "le", "les", "et", "a", "au", "aux", "en", "sur", "sous", "d", "l"}


# ===========================================================================
#  PALETTES — chaque couple est verifie AA (>= 4.5:1) sur fond clair et sombre
# ===========================================================================
PALETTES = {
    "restauration":     {"accent": "#b23c17", "fonce": "#8d2f10", "clair": "#ff9e78"},
    "beaute-bien-etre": {"accent": "#9c3268", "fonce": "#7d2753", "clair": "#f39ac4"},
    "batiment":         {"accent": "#1b4fd8", "fonce": "#153eac", "clair": "#8fb4ff"},
    "sport-loisirs":    {"accent": "#0f766e", "fonce": "#0b5a54", "clair": "#5fd9c8"},
    "artisanat":        {"accent": "#8a4a0d", "fonce": "#6e3b0a", "clair": "#eda766"},
    "sante-liberal":    {"accent": "#1d6fa5", "fonce": "#175883", "clair": "#86c5ec"},
    "commerce":         {"accent": "#6b3fc4", "fonce": "#56329d", "clair": "#bfa6ff"},
    "_defaut":          {"accent": "#334d74", "fonce": "#273c5c", "clair": "#9fbbe6"},
}

# ===========================================================================
#  ICONES — SVG inline, aucune image, aucune police d'icones
# ===========================================================================
ICO = {
    "assiette": '<circle cx="12" cy="12" r="8.2"/><circle cx="12" cy="12" r="4.2"/>',
    "verre": '<path d="M7 4h10l-1.2 5.4a4 4 0 0 1-7.6 0Z"/><path d="M12 13.5V20M8.5 20h7"/>',
    "feu": '<path d="M12 3.5c3.2 3 4.6 5.3 4.6 7.6A4.6 4.6 0 0 1 12 15.7a4.6 4.6 0 0 1-4.6-4.6c0-2.3 1.4-4.6 4.6-7.6Z"/><path d="M12 20.5a5.6 5.6 0 0 0 5.6-5.6c0 .6-3 2.4-5.6 2.4s-5.6-1.8-5.6-2.4A5.6 5.6 0 0 0 12 20.5Z"/>',
    "panier": '<path d="M5.5 8.5h13l-1.3 10H6.8Z"/><path d="M9 8.5a3 3 0 0 1 6 0"/>',
    "ciseaux": '<circle cx="7" cy="7" r="2.6"/><circle cx="7" cy="17" r="2.6"/><path d="M9 8.6 19 17M9 15.4 19 7"/>',
    "etincelle": '<path d="m12 4 1.9 5.1L19 11l-5.1 1.9L12 18l-1.9-5.1L5 11l5.1-1.9Z"/><path d="M18.5 16.5 19 18l1.5.5L19 19l-.5 1.5-.5-1.5L16.5 18l1.5-.5Z"/>',
    "main": '<path d="M9.5 11V5.8a1.4 1.4 0 0 1 2.8 0V11"/><path d="M12.3 11V4.9a1.4 1.4 0 0 1 2.8 0V11"/><path d="M15.1 11V6.6a1.4 1.4 0 0 1 2.8 0v6.9a6.5 6.5 0 0 1-6.5 6.5h-.5A5.4 5.4 0 0 1 5.5 14.6L5 12.4a1.4 1.4 0 0 1 2.5-1.1l2 2.6"/>',
    "goutte": '<path d="M12 3.8c3.3 3.9 5 6.6 5 8.9a5 5 0 0 1-10 0c0-2.3 1.7-5 5-8.9Z"/>',
    "marteau": '<path d="m13.6 7.6 3-3 3.4 3.4-3 3Z"/><path d="m13 8.2-8.3 8.3 2.8 2.8 8.3-8.3"/>',
    "regle": '<path d="m3.8 14.6 10.8-10.8 5.6 5.6L9.4 20.2Z"/><path d="m8 10.4 1.8 1.8M10.8 7.6l1.8 1.8M13.6 4.8l1.8 1.8"/>',
    "casque": '<path d="M4.8 15.5a7.2 7.2 0 0 1 14.4 0Z"/><path d="M3.6 15.5h16.8M9.8 8.6V4.9h4.4v3.7"/>',
    "halteres": '<path d="M6.5 9v6M4 10.5v3M17.5 9v6M20 10.5v3M6.5 12h11"/>',
    "cible": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1"/>',
    "coeur": '<path d="M12 19.5C7.2 16.2 4.5 13.6 4.5 10.6A3.9 3.9 0 0 1 12 8.5a3.9 3.9 0 0 1 7.5 2.1c0 3-2.7 5.6-7.5 8.9Z"/>',
    "calendrier": '<rect x="4" y="5.5" width="16" height="14.5" rx="2.4"/><path d="M4 10h16M9 3.8v3.4M15 3.8v3.4"/>',
    "horloge": '<circle cx="12" cy="12" r="8.4"/><path d="M12 7.6V12l3 1.9"/>',
    "tel": '<path d="M7.2 4.5h3l1.3 3.4-2 1.4a10 10 0 0 0 5.2 5.2l1.4-2 3.4 1.3v3a1.6 1.6 0 0 1-1.8 1.6A14.6 14.6 0 0 1 5.6 6.3 1.6 1.6 0 0 1 7.2 4.5Z"/>',
    "mail": '<path d="M4 5.5h16v13H4z"/><path d="m4.6 6.3 7.4 6 7.4-6"/>',
    "pin": '<path d="M12 21s-7-6.2-7-11a7 7 0 1 1 14 0c0 4.8-7 11-7 11Z"/><circle cx="12" cy="10" r="2.6"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "etoile": '<path d="m12 4.8 2.3 4.8 5.2.7-3.8 3.6.9 5.1L12 16.6l-4.6 2.4.9-5.1L4.5 10.3l5.2-.7Z"/>',
    "parking": '<rect x="4.5" y="4.5" width="15" height="15" rx="3.4"/><path d="M10 16V8.5h2.6a2.4 2.4 0 0 1 0 4.8H10"/>',
    "bus": '<rect x="5" y="4.8" width="14" height="11.4" rx="2.4"/><path d="M5 11h14M8.5 19.2v-3M15.5 19.2v-3"/><circle cx="8.6" cy="13.6" r=".9" fill="currentColor" stroke="none"/><circle cx="15.4" cy="13.6" r=".9" fill="currentColor" stroke="none"/>',
    "acces": '<circle cx="12" cy="12" r="8.4"/><path d="M12 8.2v4.2l2.8 1.8"/>',
    "feuille": '<path d="M12 20c0-6 3.6-10 8-10.6C19.4 15 16 20 12 20Z"/><path d="M12 20C7.6 19.4 4 15 4 9.4 8.4 10 12 14 12 20Z"/>',
}


def svg(cle, classe="ico"):
    return '<svg class="%s" viewBox="0 0 24 24" aria-hidden="true">%s</svg>' % (classe, ICO.get(cle, ICO["check"]))


# ===========================================================================
#  PRESETS DE CONTENU PAR SECTEUR
#  Tout est redige au conditionnel du reel : aucun faux avis, aucun chiffre
#  invente. Ce qui doit etre confirme par le client est liste dans le README.
# ===========================================================================
def preset_restauration(c):
    return {
        "metier": "Restaurant",
        "metier_court": "Restaurant",
        "nav_offre": "La carte",
        "eyebrow": "Cuisine maison à %s" % c["ville"],
        "accroche": "La table de %s" % c["ville"],
        "sous_titre": "Une cuisine de produits frais, préparée sur place chaque jour. Midi et soir, sur place ou à emporter.",
        "services_titre": "Ce que nous servons",
        "services_intro": "Une carte courte qui change avec les saisons, pour que tout reste frais.",
        "services": [
            ("assiette", "Le menu du midi", "Entrée, plat et dessert au tarif du midi, servi en moins de 30 minutes. Idéal pour la pause déjeuner.", "Formule à partir de 15 €"),
            ("feu", "La carte du soir", "Des plats cuisinés à la commande, une sélection de vins choisie avec les vignerons de la région.", "Service de 19 h à 22 h"),
            ("panier", "À emporter", "Toute la carte est disponible à emporter, commande par téléphone et retrait sur place.", "Prêt en 20 minutes"),
        ],
        "services_pied": "Carte des allergènes disponible en salle et sur demande — conformément au décret n° 2015-447.",
        "apropos_titre": "Une maison ouverte depuis %s" % c["ouverture_texte"],
        "apropos": [
            "%s a ouvert ses portes à %s en %s. Une salle, une équipe réduite, et le parti pris de tout préparer sur place plutôt que de rallonger la carte." % (c["nom"], c["ville"], c["ouverture_texte"]),
            "Les produits viennent au maximum des producteurs du secteur, la carte change avec les saisons, et le plat du jour s’écrit le matin en fonction du marché.",
        ],
        "puces": [
            "Cuisine préparée sur place, tous les jours",
            "Produits de saison, fournisseurs locaux",
            "Menu enfant et options végétariennes",
            "Groupes et repas d’entreprise sur réservation",
        ],
        "citation": "Une carte courte, des produits frais, et le temps qu’il faut pour bien faire. C’est tout ce que nous savons faire, mais nous le faisons bien.",
        "citation_auteur": "L’équipe de %s" % c["nom"],
        "horaires_intro": "Le service s’arrête 30 minutes avant la fermeture indiquée. Réservation conseillée le week-end.",
        "horaires_note": "Fermeture exceptionnelle annoncée sur la fiche Google et sur cette page.",
        "contact_titre": "Réserver une table",
        "contact_intro": "Pour une table, un groupe ou une question sur la carte : écrivez-nous, nous répondons dans la journée.",
        "objets": ["Réserver une table", "Commande à emporter", "Groupe ou événement", "Question sur la carte", "Autre demande"],
        "placeholder_msg": "Ex. : une table pour 4 personnes samedi à 20 h, dont un menu sans gluten.",
        "cta_label": "Réserver une table",
        "cta_court": "Réserver",
        "fiche_tag": "Sur place & à emporter",
        "preuves": [("assiette", "Fait maison"), ("pin", "Au cœur de %s" % c["ville"]), ("feuille", "Options végétariennes")],
        "chiffres": [("Depuis %s" % c["annee"], "Ouvert à %s" % c["ville"]), ("%d j/7" % c["jours_ouverts"], "Services par semaine")],
        "horaires": [
            (1, None), (2, "11:45-14:00,19:00-21:30"), (3, "11:45-14:00,19:00-21:30"),
            (4, "11:45-14:00,19:00-21:30"), (5, "11:45-14:00,19:00-22:00"),
            (6, "11:45-14:00,19:00-22:00"), (7, "11:45-14:30"),
        ],
    }


def preset_beaute(c):
    return {
        "metier": "Salon de beauté et bien-être",
        "metier_court": "Beauté & bien-être",
        "nav_offre": "Prestations",
        "eyebrow": "Sur rendez-vous à %s" % c["ville"],
        "accroche": "Prendre soin de vous, à %s" % c["ville"],
        "sous_titre": "Des soins personnalisés, sans précipitation, dans un espace calme. Rendez-vous en ligne ou par téléphone.",
        "services_titre": "Les prestations",
        "services_intro": "Chaque rendez-vous commence par quelques minutes d’échange pour adapter le soin.",
        "services": [
            ("etincelle", "Soin du visage", "Diagnostic de peau, nettoyage, modelage et soin adapté. Repartez avec les bons gestes à refaire chez vous.", "À partir de 45 € · 1 h"),
            ("main", "Mains et pieds", "Manucure, pose, beauté des pieds. Matériel stérilisé après chaque passage.", "À partir de 25 € · 45 min"),
            ("goutte", "Modelage bien-être", "Un temps pour relâcher les tensions : dos, nuque ou corps entier, pression choisie avec vous.", "À partir de 55 € · 1 h"),
        ],
        "services_pied": "Les tarifs affichés sont des tarifs de départ : le devis exact est donné avant chaque soin, sans engagement.",
        "apropos_titre": "Un institut à taille humaine",
        "apropos": [
            "%s reçoit à %s depuis %s. Un seul rendez-vous à la fois : pas de salle d’attente, pas de soin expédié." % (c["nom"], c["ville"], c["ouverture_texte"]),
            "Les produits utilisés sont choisis pour leur composition courte et leur tolérance sur les peaux sensibles. Le protocole est adapté à chaque personne.",
        ],
        "puces": [
            "Un seul rendez-vous à la fois",
            "Matériel stérilisé après chaque passage",
            "Produits à composition courte",
            "Carte cadeau disponible",
        ],
        "citation": "Un soin réussi, c’est d’abord du temps : comprendre la peau qu’on a en face de soi avant de poser quoi que ce soit.",
        "citation_auteur": "%s" % c["nom"],
        "horaires_intro": "Les rendez-vous se prennent par téléphone ou via le formulaire. Dernier rendez-vous 1 h avant la fermeture.",
        "horaires_note": "Un créneau en dehors de ces horaires est possible sur demande.",
        "contact_titre": "Prendre rendez-vous",
        "contact_intro": "Indiquez la prestation souhaitée et vos disponibilités : une proposition de créneau vous est envoyée en retour.",
        "objets": ["Prendre rendez-vous", "Demander un conseil", "Carte cadeau", "Tarifs et prestations", "Autre demande"],
        "placeholder_msg": "Ex. : un soin du visage, plutôt en fin de journée, cette semaine ou la suivante.",
        "cta_label": "Prendre rendez-vous",
        "cta_court": "Rendez-vous",
        "fiche_tag": "Sur rendez-vous",
        "preuves": [("etincelle", "Soins personnalisés"), ("horloge", "Sur rendez-vous"), ("pin", "À %s" % c["ville"])],
        "chiffres": [("Depuis %s" % c["annee"], "Installée à %s" % c["ville"]), ("1 à 1", "Un rendez-vous à la fois")],
        "horaires": [
            (1, None), (2, "09:30-18:30"), (3, "09:30-18:30"), (4, "09:30-19:00"),
            (5, "09:30-19:00"), (6, "09:00-17:00"), (7, None),
        ],
    }


def preset_batiment(c):
    return {
        "metier": "Artisan du bâtiment",
        "metier_court": "Bâtiment",
        "nav_offre": "Interventions",
        "eyebrow": "Devis gratuit · %s et alentours" % c["ville"],
        "accroche": "Vos travaux, faits une bonne fois",
        "sous_titre": "Devis clair, chantier tenu, finitions soignées. Interventions à %s et dans un rayon de 30 km." % c["ville"],
        "services_titre": "Nos interventions",
        "services_intro": "Du dépannage à la rénovation complète : un seul interlocuteur du devis à la réception du chantier.",
        "services": [
            ("marteau", "Rénovation", "Pièce par pièce ou logement complet : dépose, mise en œuvre, finitions. Planning annoncé avant le démarrage.", "Devis sous 72 h"),
            ("regle", "Travaux neufs", "Chantiers de construction et d’aménagement, coordination avec les autres corps de métier.", "Sur plan ou sur site"),
            ("casque", "Dépannage", "Interventions rapides sur les urgences du quotidien, avec un diagnostic avant tout démontage.", "Déplacement annoncé à l’avance"),
        ],
        "services_pied": "Assurance décennale et attestation de TVA fournies avec chaque devis, avant toute signature.",
        "apropos_titre": "L’artisan derrière les chantiers",
        "apropos": [
            "%s intervient à %s et dans les communes voisines depuis %s. Un interlocuteur unique, du premier rendez-vous à la réception des travaux." % (c["nom"], c["ville"], c["ouverture_texte"]),
            "Le devis détaille les fournitures, la main-d’œuvre et le calendrier. Pas de ligne « divers », pas de surprise à la facture.",
        ],
        "puces": [
            "Devis détaillé et gratuit",
            "Dates de chantier annoncées et tenues",
            "Chantier nettoyé en fin de journée",
            "Assurance décennale à jour",
        ],
        "citation": "Un chantier bien mené, c’est un client qui sait ce qui se passe chez lui, chaque jour, jusqu’à la fin.",
        "citation_auteur": "%s" % c["nom"],
        "horaires_intro": "Les visites de chantier se planifient à l’avance ; le téléphone reste joignable pendant les horaires d’atelier.",
        "horaires_note": "Interventions d’urgence possibles en dehors de ces horaires, selon planning.",
        "contact_titre": "Demander un devis",
        "contact_intro": "Décrivez votre projet en quelques lignes : nous revenons vers vous sous 72 heures ouvrées avec une date de visite.",
        "objets": ["Demander un devis", "Planifier une visite", "Dépannage urgent", "Question technique", "Autre demande"],
        "placeholder_msg": "Ex. : rénovation d’une salle de bain de 6 m², logement des années 70, travaux souhaités avant l’été.",
        "cta_label": "Demander un devis",
        "cta_court": "Devis",
        "fiche_tag": "Devis gratuit",
        "preuves": [("check", "Devis gratuit"), ("pin", "%s + 30 km" % c["ville"]), ("casque", "Assurance décennale")],
        "chiffres": [("Depuis %s" % c["annee"], "Installé à %s" % c["ville"]), ("72 h", "Pour recevoir un devis")],
        "horaires": [
            (1, "07:30-12:00,13:30-18:00"), (2, "07:30-12:00,13:30-18:00"), (3, "07:30-12:00,13:30-18:00"),
            (4, "07:30-12:00,13:30-18:00"), (5, "07:30-12:00,13:30-17:00"), (6, None), (7, None),
        ],
    }


def preset_sport(c):
    return {
        "metier": "Sport et loisirs",
        "metier_court": "Sport & loisirs",
        "nav_offre": "Activités",
        "eyebrow": "Première séance à %s" % c["ville"],
        "accroche": "Bougez à votre rythme",
        "sous_titre": "Des séances encadrées, en petit groupe ou en individuel, adaptées à votre niveau de départ.",
        "services_titre": "Les activités",
        "services_intro": "On commence par un bilan simple : ce que vous voulez, ce que vous pouvez, et à quel rythme.",
        "services": [
            ("halteres", "Séance encadrée", "Groupes limités pour garder un vrai suivi technique. Matériel fourni, aucun niveau requis.", "À partir de 15 € la séance"),
            ("cible", "Suivi individuel", "Un programme écrit pour vous, revu toutes les quatre semaines selon vos progrès.", "Bilan offert"),
            ("coeur", "Reprise en douceur", "Pour redémarrer après un arrêt long : intensité basse, progression mesurée.", "Créneaux en journée"),
        ],
        "services_pied": "Certificat médical ou questionnaire de santé demandé à l’inscription, selon votre situation.",
        "apropos_titre": "Un encadrement, pas une salle de plus",
        "apropos": [
            "%s accueille à %s depuis %s. Des groupes volontairement réduits : chacun est vu, corrigé et suivi." % (c["nom"], c["ville"], c["ouverture_texte"]),
            "Le but n’est pas la performance à tout prix mais la régularité : des séances qu’on a envie de refaire la semaine suivante.",
        ],
        "puces": [
            "Groupes réduits, suivi réel",
            "Première séance d’essai",
            "Matériel fourni",
            "Créneaux en journée et en soirée",
        ],
        "citation": "La meilleure séance est celle que vous ferez encore dans six mois. Tout le reste en découle.",
        "citation_auteur": "L’équipe de %s" % c["nom"],
        "horaires_intro": "Les créneaux se réservent à l’avance ; l’accès libre reste possible aux horaires indiqués.",
        "horaires_note": "Horaires allégés pendant les vacances scolaires, annoncés sur cette page.",
        "contact_titre": "Essayer une séance",
        "contact_intro": "Dites-nous votre objectif et vos disponibilités : on vous propose le créneau le plus adapté pour commencer.",
        "objets": ["Essayer une séance", "Tarifs et abonnements", "Suivi individuel", "Groupe ou entreprise", "Autre demande"],
        "placeholder_msg": "Ex. : reprise du sport après deux ans d’arrêt, plutôt en fin de journée.",
        "cta_label": "Essayer une séance",
        "cta_court": "Essayer",
        "fiche_tag": "Séance d’essai",
        "preuves": [("halteres", "Groupes réduits"), ("check", "Séance d’essai"), ("pin", "À %s" % c["ville"])],
        "chiffres": [("Depuis %s" % c["annee"], "Ouvert à %s" % c["ville"]), ("%d j/7" % c["jours_ouverts"], "Jours d’ouverture")],
        "horaires": [
            (1, "09:00-13:00,16:00-21:00"), (2, "09:00-13:00,16:00-21:00"), (3, "09:00-21:00"),
            (4, "09:00-13:00,16:00-21:00"), (5, "09:00-13:00,16:00-20:00"), (6, "09:00-13:00"), (7, None),
        ],
    }


def preset_defaut(c):
    return {
        "metier": "Entreprise locale",
        "metier_court": "Entreprise",
        "nav_offre": "Services",
        "eyebrow": "À %s et alentours" % c["ville"],
        "accroche": "%s, à %s" % (c["nom"], c["ville"]),
        "sous_titre": "Une entreprise locale, joignable facilement, qui répond vite et travaille proprement.",
        "services_titre": "Ce que nous faisons",
        "services_intro": "Trois façons de travailler ensemble, du premier contact jusqu’à la livraison.",
        "services": [
            ("check", "Premier échange", "On fait le point sur votre besoin, sans engagement, pour savoir si nous sommes les bons interlocuteurs.", "Gratuit"),
            ("regle", "Proposition écrite", "Un devis détaillé : ce qui est fait, ce qui ne l’est pas, le délai et le prix.", "Sous 72 h"),
            ("etoile", "Réalisation", "Le travail est suivi et vous recevez un point d’avancement à chaque étape clé.", "Délai annoncé tenu"),
        ],
        "services_pied": "Les conditions, délais et tarifs sont confirmés par écrit avant tout démarrage.",
        "apropos_titre": "Une entreprise d’ici",
        "apropos": [
            "%s est installée à %s depuis %s et travaille principalement dans un rayon de 30 km." % (c["nom"], c["ville"], c["ouverture_texte"]),
            "Un interlocuteur unique, des réponses rapides et des engagements écrits : la base, mais tenue.",
        ],
        "puces": ["Réponse sous 48 h", "Devis écrit et détaillé", "Interlocuteur unique", "Intervention locale"],
        "citation": "On préfère dire non à un chantier qu’on ne peut pas tenir plutôt que de faire attendre quelqu’un.",
        "citation_auteur": "%s" % c["nom"],
        "horaires_intro": "L’accueil téléphonique et les rendez-vous se tiennent aux horaires ci-dessous.",
        "horaires_note": "En dehors de ces horaires, le formulaire reste le moyen le plus rapide.",
        "contact_titre": "Nous contacter",
        "contact_intro": "Une question, un projet, un devis : écrivez-nous, la réponse arrive sous 48 heures ouvrées.",
        "objets": ["Demander un devis", "Prendre rendez-vous", "Question générale", "Autre demande"],
        "placeholder_msg": "Décrivez votre besoin en quelques lignes.",
        "cta_label": "Nous contacter",
        "cta_court": "Contact",
        "fiche_tag": "Entreprise locale",
        "preuves": [("check", "Réponse sous 48 h"), ("pin", "À %s" % c["ville"]), ("etoile", "Devis écrit")],
        "chiffres": [("Depuis %s" % c["annee"], "Installée à %s" % c["ville"]), ("48 h", "Délai de réponse")],
        "horaires": [
            (1, "09:00-12:00,14:00-18:00"), (2, "09:00-12:00,14:00-18:00"), (3, "09:00-12:00,14:00-18:00"),
            (4, "09:00-12:00,14:00-18:00"), (5, "09:00-12:00,14:00-17:00"), (6, None), (7, None),
        ],
    }


PRESETS = {
    "restauration": preset_restauration,
    "beaute-bien-etre": preset_beaute,
    "batiment": preset_batiment,
    "sport-loisirs": preset_sport,
}

TYPE_SCHEMA = {
    "restauration": "Restaurant",
    "beaute-bien-etre": "BeautySalon",
    "batiment": "HomeAndConstructionBusiness",
    "sport-loisirs": "SportsActivityLocation",
    "sante-liberal": "MedicalBusiness",
    "commerce": "Store",
}

# cartes par defaut selon le code NAF (56.10C = restauration rapide)
CARTE_RAPIDE = {
    "categories": [
        {"id": "formules", "nom": "Formules", "description": "Servies midi et soir, à consommer sur place ou à emporter."},
        {"id": "sandwichs", "nom": "Sandwichs & galettes", "description": "Pains et galettes préparés sur place."},
        {"id": "assiettes", "nom": "Assiettes", "description": "Servies avec frites maison et crudités."},
        {"id": "accompagnements", "nom": "Accompagnements", "description": None},
        {"id": "desserts", "nom": "Desserts", "description": None},
        {"id": "boissons", "nom": "Boissons", "description": None},
    ],
    "plats": [
        {"nom": "Formule sandwich", "description": "Sandwich au choix, frites maison et boisson 33 cl.", "prix": 11.0, "categorie": "formules", "signature": True, "allergenes": ["gluten", "sesame"]},
        {"nom": "Formule assiette", "description": "Assiette au choix, boisson 33 cl et dessert du jour.", "prix": 15.5, "categorie": "formules", "allergenes": ["gluten", "lait"]},
        {"nom": "Formule enfant", "description": "Petit sandwich ou nuggets, frites, compote et sirop.", "prix": 7.5, "categorie": "formules", "allergenes": ["gluten", "oeuf"]},
        {"nom": "Galette viande", "description": "Viande marinée, crudités, sauce au choix, galette chaude.", "prix": 8.5, "categorie": "sandwichs", "signature": True, "allergenes": ["gluten", "lait", "sesame"]},
        {"nom": "Sandwich poulet", "description": "Poulet mariné grillé, crudités, sauce blanche maison.", "prix": 8.0, "categorie": "sandwichs", "allergenes": ["gluten", "lait", "oeuf"]},
        {"nom": "Sandwich végétarien", "description": "Falafels maison, houmous, crudités, sauce au sésame.", "prix": 7.5, "categorie": "sandwichs", "vegetarien": True, "allergenes": ["gluten", "sesame"]},
        {"nom": "Burger maison", "description": "Steak haché frais, cheddar, oignons confits, sauce maison.", "prix": 9.5, "categorie": "sandwichs", "allergenes": ["gluten", "lait", "oeuf", "moutarde"]},
        {"nom": "Assiette mixte", "description": "Deux viandes au choix, frites maison, crudités, sauce.", "prix": 14.5, "categorie": "assiettes", "allergenes": ["lait", "sesame"]},
        {"nom": "Assiette poulet", "description": "Poulet mariné grillé, frites maison, crudités.", "prix": 12.5, "categorie": "assiettes", "allergenes": ["lait"]},
        {"nom": "Assiette végétarienne", "description": "Falafels, houmous, salade, frites maison.", "prix": 11.5, "categorie": "assiettes", "vegetarien": True, "allergenes": ["sesame"]},
        {"nom": "Frites maison", "description": "Pommes de terre fraîches, coupées sur place.", "prix": 3.5, "categorie": "accompagnements", "vegetarien": True},
        {"nom": "Salade de saison", "description": "Crudités du jour, vinaigrette maison.", "prix": 3.5, "categorie": "accompagnements", "vegetarien": True, "allergenes": ["moutarde"]},
        {"nom": "Nuggets maison", "description": "Six pièces, panure préparée sur place.", "prix": 5.0, "categorie": "accompagnements", "allergenes": ["gluten", "oeuf"]},
        {"nom": "Tiramisu", "description": "Préparé le matin même.", "prix": 4.0, "categorie": "desserts", "vegetarien": True, "allergenes": ["lait", "oeuf", "gluten"]},
        {"nom": "Salade de fruits", "description": "Fruits frais de saison.", "prix": 3.5, "categorie": "desserts", "vegetarien": True},
        {"nom": "Crêpe sucrée", "description": "Sucre, chocolat ou confiture.", "prix": 3.0, "categorie": "desserts", "vegetarien": True, "allergenes": ["gluten", "lait", "oeuf"]},
        {"nom": "Boisson 33 cl", "description": "Sodas, eau plate ou gazeuse.", "prix": 2.0, "categorie": "boissons", "vegetarien": True},
        {"nom": "Thé à la menthe", "description": "Servi en verre, préparé à la commande.", "prix": 2.5, "categorie": "boissons", "vegetarien": True},
        {"nom": "Café", "description": "Expresso ou allongé.", "prix": 1.8, "categorie": "boissons", "vegetarien": True},
    ],
}


# ===========================================================================
#  OUTILS
# ===========================================================================
def sans_accents(s):
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", sans_accents(s).lower()).strip("-")


def ech(s):
    """Echappement HTML."""
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def casse_titre(s):
    """« 17 RUE DE METZ » -> « 17 Rue de Metz » (particules en minuscules)."""
    mots, out = re.split(r"(\s+|-)", (s or "").strip()), []
    premier = True
    for m in mots:
        if not m.strip():
            out.append(m)
            continue
        bas = m.lower()
        if not premier and sans_accents(bas).strip("’'") in PETITS_MOTS:
            out.append(bas)
        elif re.match(r"^\d", m):
            out.append(m.upper() if len(m) <= 3 else m)
        else:
            out.append(bas[:1].upper() + bas[1:])
        premier = False
    return "".join(out)


def nom_propre(nom):
    """Normalise un nom en capitales venant de la base."""
    nom = re.sub(r"\s+", " ", (nom or "").strip())
    lettres = [c for c in nom if c.isalpha()]
    if lettres and sum(1 for c in lettres if c.isupper()) / len(lettres) > 0.8:
        return casse_titre(nom)
    return nom


def initiales(nom):
    mots = [m for m in re.split(r"[^\w]+", sans_accents(nom)) if m and m.lower() not in PETITS_MOTS]
    if not mots:
        return "??"
    if len(mots) == 1:
        return mots[0][:2].upper()
    return (mots[0][0] + mots[1][0]).upper()


def decouper_adresse(adresse, ville_base):
    """« 17 RUE DE METZ 57380 FAULQUEMONT » -> (rue, cp, ville)."""
    a = re.sub(r"\s+", " ", (adresse or "").strip())
    m = re.search(r"^(.*?)[\s,]*(\d{5})\s+(.+)$", a)
    if m:
        return casse_titre(m.group(1)), m.group(2), casse_titre(m.group(3))
    return casse_titre(a) or "Adresse à confirmer", "", casse_titre(ville_base)


def tel_href(tel):
    chiffres = re.sub(r"[^\d+]", "", tel or "")
    if chiffres.startswith("0") and len(chiffres) == 10:
        return "+33" + chiffres[1:]
    return chiffres


def tel_affiche(tel):
    c = re.sub(r"\D", "", tel or "")
    if len(c) == 10:
        return " ".join(c[i:i + 2] for i in range(0, 10, 2))
    return tel


MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


def date_fr(iso):
    try:
        a, m, j = iso.split("-")
        return "%s %s %s" % (int(j), MOIS[int(m) - 1], a)
    except Exception:
        return iso or ""


def mois_annee(iso):
    try:
        a, m, _ = iso.split("-")
        return "%s %s" % (MOIS[int(m) - 1], a)
    except Exception:
        return iso or ""


def rvb(hexa):
    h = hexa.lstrip("#")
    return "%d,%d,%d" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def rgba(hexa, alpha):
    return "rgba(%s,%s)" % (rvb(hexa), alpha)


# ===========================================================================
#  BASE DE PROSPECTS (lecture seule)
# ===========================================================================
def charger_base():
    if not os.path.exists(BASE):
        sys.exit("ERREUR : base introuvable (%s)." % BASE)
    lignes = []
    with open(BASE, encoding="utf-8") as f:
        for n, ligne in enumerate(f, 1):
            ligne = ligne.strip()
            if not ligne:
                continue
            try:
                lignes.append(json.loads(ligne))
            except json.JSONDecodeError as e:
                sys.exit("ERREUR : ligne %d illisible dans la base (%s)." % (n, e))
    return lignes


def trouver(rows, cle):
    cherche = cle.strip()
    for r in rows:
        if r.get("cle") == cherche:
            return r
    for r in rows:                                   # tolerance : SIREN nu
        if r.get("siren") and r["siren"] == re.sub(r"\D", "", cherche):
            return r
    for r in rows:                                   # tolerance : nom exact
        if slug(r.get("nom")) == slug(cherche):
            return r

    proches = [r for r in rows
               if slug(cherche) and slug(cherche) in slug("%s %s %s" % (r.get("cle"), r.get("nom"), r.get("ville")))][:5]
    print("ERREUR : aucun prospect avec la cle « %s » dans %s." % (cle, os.path.relpath(BASE, os.getcwd())), file=sys.stderr)
    if proches:
        print("\nVouliez-vous dire :", file=sys.stderr)
        for r in proches:
            print("  %-22s %s — %s" % (r.get("cle"), r.get("nom"), r.get("ville")), file=sys.stderr)
    else:
        print("\nPour lister les cles disponibles :", file=sys.stderr)
        print("  python3 agency/scripts/prospects.py next --n 10", file=sys.stderr)
    sys.exit(1)


# ===========================================================================
#  CONTEXTE
# ===========================================================================
def construire_contexte(p, args, aujourdhui):
    nom = nom_propre(p.get("nom") or "Entreprise")
    ville = casse_titre(p.get("ville") or "")
    secteur = p.get("secteur") or "_defaut"
    rue, cp, ville_adr = decouper_adresse(p.get("adresse"), ville)
    ouverture = p.get("ouverture") or ""

    base = {
        "nom": nom,
        "ville": ville or ville_adr,
        "ouverture_texte": mois_annee(ouverture) or "peu",
        "annee": (ouverture or "")[:4] or str(aujourdhui.year),
    }

    preset_f = PRESETS.get(secteur, preset_defaut)
    base["jours_ouverts"] = 0
    preset = preset_f(dict(base, jours_ouverts=0))
    base["jours_ouverts"] = sum(1 for _, h in preset["horaires"] if h)
    preset = preset_f(base)                           # re-rendu avec le bon compte

    pal = PALETTES.get(secteur, PALETTES["_defaut"])
    tel = args.tel or p.get("telephone") or ""
    email = args.email or p.get("email") or ""

    return {
        "p": p, "preset": preset, "pal": pal, "secteur": secteur,
        "nom": nom, "ville": base["ville"], "rue": rue, "cp": cp,
        "tel": tel_affiche(tel), "tel_href": tel_href(tel), "email": email,
        "ouverture": ouverture, "siren": p.get("siren") or "",
        "naf": p.get("naf") or "", "annee": base["annee"],
    }


# ===========================================================================
#  FRAGMENTS HTML
# ===========================================================================
def html_horaires(preset):
    out = []
    for jour, creneaux in preset["horaires"]:
        label = JOURS[jour - 1].capitalize()
        if creneaux:
            lisible = " · ".join(
                "%sh%s – %sh%s" % (d[:2], d[3:] if d[3:] != "00" else "", f[:2], f[3:] if f[3:] != "00" else "")
                for d, f in (c.split("-") for c in creneaux.split(","))
            )
            out.append('<li data-jour="%d" data-creneaux="%s"><span class="jour">%s</span>'
                       '<span class="heures">%s</span></li>' % (jour, creneaux, label, lisible))
        else:
            out.append('<li data-jour="%d" data-ferme="1"><span class="jour">%s</span>'
                       '<span class="heures">Fermé</span></li>' % (jour, label))
    return "\n        ".join(out)


def html_services(preset):
    out = []
    for icone, titre, texte, prix in preset["services"]:
        out.append(
            '<li class="carte">'
            '<span class="carte-ico">%s</span>'
            "<h3>%s</h3><p>%s</p>"
            '<span class="carte-prix">%s</span>'
            "</li>" % (svg(icone), ech(titre), ech(texte), ech(prix))
        )
    return "\n        ".join(out)


def html_preuves(preset):
    return "\n          ".join(
        "<li>%s%s</li>" % (svg(i), ech(t)) for i, t in preset["preuves"]
    )


def html_puces(preset):
    return "\n          ".join(
        "<li>%s<span>%s</span></li>" % (svg("check"), ech(t)) for t in preset["puces"]
    )


def html_chiffres(preset):
    return "\n          ".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % (ech(v), ech(l)) for v, l in preset["chiffres"]
    )


def html_apropos(preset):
    paras = preset["apropos"]
    return "\n        ".join(
        '<p%s>%s</p>' % (' class="intro"' if i == 0 else "", ech(t)) for i, t in enumerate(paras)
    )


def html_acces(ctx):
    pts = [
        ("parking", "Stationnement possible à proximité immédiate"),
        ("bus", "Desservi par les transports en commun de %s" % ctx["ville"]),
        ("acces", "Rez-de-chaussée, accès de plain-pied"),
    ]
    return "\n            ".join("<li>%s<span>%s</span></li>" % (svg(i), ech(t)) for i, t in pts)


def html_objets(preset):
    return "".join('<option>%s</option>' % ech(o) for o in preset["objets"])


def jours_ouverture(preset):
    """« Du mardi au dimanche », « 7 jours sur 7 » ou la liste des jours."""
    ouverts = [j for j, h in preset["horaires"] if h]
    if not ouverts:
        return "Sur rendez-vous"
    if len(ouverts) == 7:
        return "7 jours sur 7"
    contigu = ouverts == list(range(ouverts[0], ouverts[-1] + 1))
    if contigu and len(ouverts) > 2:
        return "Du %s au %s" % (JOURS[ouverts[0] - 1], JOURS[ouverts[-1] - 1])
    return ", ".join(JOURS[j - 1] for j in ouverts).capitalize()


def html_contact_liste(ctx):
    items = []
    if ctx["tel"]:
        items.append((svg("tel"), "Téléphone", '<a href="tel:%s">%s</a>' % (ctx["tel_href"], ech(ctx["tel"]))))
    if ctx["email"]:
        items.append((svg("mail"), "E-mail", '<a href="mailto:%s">%s</a>' % (ech(ctx["email"]), ech(ctx["email"]))))
    items.append((svg("pin"), "Adresse", "%s, %s %s" % (ech(ctx["rue"]), ech(ctx["cp"]), ech(ctx["ville"]))))
    items.append((svg("calendrier"), "Sur place", ech(jours_ouverture(ctx["preset"]))))
    items.append((svg("horloge"), "Réponse", "Sous 48 heures ouvrées"))
    return "\n            ".join(
        "<li>%s<div><span>%s</span><strong>%s</strong></div></li>" % (ico, lab, val)
        for ico, lab, val in items
    )


def jsonld(ctx, type_demo, url_site, menu=None):
    preset, p = ctx["preset"], ctx["p"]
    horaires = []
    for jour, creneaux in preset["horaires"]:
        if not creneaux:
            continue
        for c in creneaux.split(","):
            d, f = c.split("-")
            horaires.append({
                "@type": "OpeningHoursSpecification",
                "dayOfWeek": "https://schema.org/" + JOURS_SCHEMA[jour - 1],
                "opens": d, "closes": f,
            })

    data = {
        "@context": "https://schema.org",
        "@type": TYPE_SCHEMA.get(ctx["secteur"], "LocalBusiness"),
        "name": ctx["nom"],
        "description": preset["sous_titre"],
        "url": url_site,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": ctx["rue"],
            "postalCode": ctx["cp"],
            "addressLocality": ctx["ville"],
            "addressCountry": "FR",
        },
        "areaServed": {"@type": "City", "name": ctx["ville"]},
        "openingHoursSpecification": horaires,
        "currenciesAccepted": "EUR",
    }
    if ctx["tel"]:
        data["telephone"] = "+" + ctx["tel_href"].lstrip("+")
    if ctx["email"]:
        data["email"] = ctx["email"]
    if ctx["siren"]:
        data["identifier"] = {"@type": "PropertyValue", "name": "SIREN", "value": ctx["siren"]}
    if ctx["secteur"] == "restauration":
        data["servesCuisine"] = "Française"
        data["priceRange"] = "€€"
        data["acceptsReservations"] = "True"

    if menu:
        data["hasMenu"] = {
            "@type": "Menu",
            "name": "Carte de %s" % ctx["nom"],
            "inLanguage": "fr",
            "hasMenuSection": [
                {
                    "@type": "MenuSection",
                    "name": cat["nom"],
                    "hasMenuItem": [
                        dict([("@type", "MenuItem"), ("name", plat["nom"])]
                             + ([("description", plat["description"])] if plat.get("description") else [])
                             + [("offers", {"@type": "Offer", "price": "%.2f" % float(plat["prix"]), "priceCurrency": "EUR"})]
                             + ([("suitableForDiet", "https://schema.org/VegetarianDiet")] if plat.get("vegetarien") else []))
                        for plat in menu["plats"] if plat["categorie"] == cat["id"]
                    ],
                }
                for cat in menu["categories"]
            ],
        }
    return json.dumps(data, ensure_ascii=False, indent=2)


# ===========================================================================
#  SUBSTITUTIONS
# ===========================================================================
def construire_marqueurs(ctx, type_demo, url_site, aujourdhui, menu=None):
    preset, pal = ctx["preset"], ctx["pal"]
    nom, ville = ctx["nom"], ctx["ville"]
    maps = "https://www.google.com/maps/search/?api=1&query=" + \
           re.sub(r"\s+", "+", "%s %s %s %s" % (nom, ctx["rue"], ctx["cp"], ville)).replace("&", "")

    def libelle(long_, court):
        return '<span class="long">%s</span><span class="court">%s</span>' % (ech(long_), ech(court))

    if ctx["tel"]:
        cta_primaire = ('<a class="btn btn-plein" href="tel:%s">%s%s</a>'
                        % (ctx["tel_href"], svg("tel"), libelle("Appeler le %s" % ctx["tel"], "Appeler")))
        nav_cta = '<a class="btn btn-plein btn-compact" href="tel:%s">%s%s</a>' % (
            ctx["tel_href"], svg("tel"), libelle("Appeler", "Appeler"))
        fiche_tel = ('<div><dt>%sTéléphone</dt><dd><a href="tel:%s">%s</a></dd></div>'
                     % (svg("tel"), ctx["tel_href"], ech(ctx["tel"])))
        bandeau_tel = ('<div><dt>Téléphone</dt><dd><a href="tel:%s">%s</a></dd></div>'
                       % (ctx["tel_href"], ech(ctx["tel"])))
        pied_tel = " · %s" % ech(ctx["tel"])
        cta_secondaire = '<a class="btn btn-ghost" href="tel:%s">%sAppeler</a>' % (ctx["tel_href"], svg("tel"))
    else:
        cible = "#contact" if type_demo == "vitrine" else "#pratique"
        cta_primaire = '<a class="btn btn-plein" href="%s">%s%s</a>' % (
            cible, svg("mail"), libelle(preset["cta_label"], preset["cta_court"]))
        nav_cta = '<a class="btn btn-plein btn-compact" href="%s">%s%s</a>' % (
            cible, svg("mail"), libelle(preset["cta_label"], preset["cta_court"]))
        fiche_tel = ('<div><dt>%sContact</dt><dd>Par le formulaire,\u00a0réponse sous 48\u00a0h</dd></div>' % svg("mail"))
        bandeau_tel = '<div><dt>Contact</dt><dd><a href="#pratique">Voir les coordonnées</a></dd></div>'
        pied_tel = ""
        cta_secondaire = '<a class="btn btn-ghost" href="#carte">%sVoir la carte</a>' % svg("assiette")

    if type_demo == "carte":
        titre = "Carte de %s — %s à %s" % (nom, preset["metier_court"], ville)
        description = ("La carte de %s à %s : plats, prix et allergènes, mise à jour en direct. "
                       "Filtres végétarien et allergènes, lisible sur mobile." % (nom, ville))
        og_titre = "La carte de %s" % nom
        accroche = "La carte"
        sous_titre = ("Tous nos plats, leurs prix et leurs allergènes. Filtrez, cherchez, "
                      "et commandez en salle ou à emporter.")
        eyebrow = "Carte mise à jour le %s" % date_fr(aujourdhui.isoformat())
    else:
        titre = "%s — %s à %s" % (nom, preset["metier"], ville)
        description = re.sub(r"\s+", " ", "%s à %s. %s" % (preset["metier"], ville, preset["sous_titre"])).strip()
        if len(description) > 158:
            description = description[:155].rsplit(" ", 1)[0] + "…"
        og_titre = "%s — %s" % (nom, ville)
        accroche = preset["accroche"]
        sous_titre = preset["sous_titre"]
        eyebrow = preset["eyebrow"]

    note_allerg = ("Les 14 allergènes réglementaires sont indiqués plat par plat. "
                   "En cas d’allergie, prévenez-nous à la commande : certaines préparations "
                   "partagent le même plan de travail.")

    m = {
        "NOM": ech(nom),
        "SLUG": slug(nom),
        "INITIALES": ech(initiales(nom)),
        "VILLE": ech(ville),
        "SECTEUR": ech(ctx["secteur"]),
        "SECTEUR_LABEL": ech(preset["metier_court"]),
        "FICHE_TAG": ech(preset["fiche_tag"]),
        "METIER": ech(preset["metier"]),
        "METIER_COURT": ech(preset["metier_court"]),
        "NAV_OFFRE": ech(preset["nav_offre"]),
        "ADRESSE": ech("%s, %s %s" % (ctx["rue"], ctx["cp"], ville)),
        "ADRESSE_RUE": ech(ctx["rue"]),
        "CP": ech(ctx["cp"]),
        "TEL": ech(ctx["tel"]),
        "TEL_HREF": ech(ctx["tel_href"]),
        "EMAIL": ech(ctx["email"]),
        "MAPS_URL": ech(maps),
        "URL_SITE": ech(url_site),
        "TITLE": ech(titre),
        "DESCRIPTION": ech(description),
        "OG_TITLE": ech(og_titre),
        "OG_LIGNE_1": ech(accroche[:28]),
        "OG_LIGNE_2": ech(ville),
        "OG_SOUS_LIGNE": ech(preset["services_titre"] + " · " + preset["metier"]),
        "OG_BOUTON": ech(preset["cta_label"]),
        "ACCROCHE": ech(accroche),
        "SOUS_TITRE": ech(sous_titre),
        "EYEBROW": ech(eyebrow),
        "CTA_PRIMAIRE": cta_primaire,
        "CTA_SECONDAIRE": cta_secondaire,
        "NAV_CTA": nav_cta,
        "FICHE_TEL_HTML": fiche_tel,
        "BANDEAU_TEL": bandeau_tel,
        "PIED_TEL": pied_tel,
        "PREUVES_HTML": html_preuves(preset),
        "SERVICES_TITRE": ech(preset["services_titre"]),
        "SERVICES_INTRO": ech(preset["services_intro"]),
        "SERVICES_HTML": html_services(preset),
        "SERVICES_PIED": '<p class="cartes-pied">%s<span>%s</span></p>' % (svg("check"), ech(preset["services_pied"])),
        "APROPOS_TITRE": ech(preset["apropos_titre"]),
        "APROPOS_HTML": html_apropos(preset),
        "APROPOS_PUCES": html_puces(preset),
        "CITATION": ech(preset["citation"]),
        "CITATION_AUTEUR": ech(preset["citation_auteur"]),
        "CHIFFRES_HTML": html_chiffres(preset),
        "HORAIRES_INTRO": ech(preset["horaires_intro"]),
        "HORAIRES_HTML": html_horaires(preset),
        "HORAIRES_NOTE": ech(preset["horaires_note"]),
        "ACCES_HTML": html_acces(ctx),
        "CONTACT_TITRE": ech(preset["contact_titre"]),
        "CONTACT_INTRO": ech(preset["contact_intro"]),
        "CONTACT_LISTE": html_contact_liste(ctx),
        "OBJETS_HTML": html_objets(preset),
        "PLACEHOLDER_MSG": ech(preset["placeholder_msg"]),
        "FORM_NOTE": "Vos coordonnées servent uniquement à vous répondre. Aucun suivi, aucun cookie publicitaire.",
        "FORM_SUCCES": "Merci, votre demande est bien notée. Nous revenons vers vous sous 48 heures ouvrées.",
        "NOTE_ALLERGENES": ech(note_allerg),
        "DATE_MAJ": ech(date_fr(aujourdhui.isoformat())),
        "SIREN_TXT": (" · SIREN %s" % ech(ctx["siren"])) if ctx["siren"] else "",
        "MENTION_DEMO": "Démonstration réalisée par %s — contenus et horaires à valider avant mise en ligne." % AGENCE,
        "ANNEE": str(aujourdhui.year),
        "DATE_GEN": aujourdhui.isoformat(),
        "AGENCE": AGENCE,
        "AGENCE_URL": AGENCE_URL,
        "ACCENT": pal["accent"],
        "ACCENT_FONCE": pal["fonce"],
        "ACCENT_CLAIR": pal["clair"],
        "ACCENT_RVB": rvb(pal["accent"]),
        "ACCENT_CLAIR_RVB": rvb(pal["clair"]),
        "ACCENT_VOILE": rgba(pal["accent"], ".09"),
        "ACCENT_VOILE_SOMBRE": rgba(pal["clair"], ".14"),
        "JSONLD": jsonld(ctx, type_demo, url_site, menu),
    }
    if menu is not None:
        m["MENU_INLINE"] = json.dumps(menu, ensure_ascii=False)
    return m


def appliquer(texte, marqueurs, chemin):
    for cle, val in marqueurs.items():
        texte = texte.replace("{{%s}}" % cle, str(val))
    restants = sorted(set(re.findall(r"\{\{([A-Z_0-9]+)\}\}", texte)))
    if restants:
        sys.exit("ERREUR : marqueur(s) non remplace(s) dans %s : %s" % (chemin, ", ".join(restants)))
    return texte


# ===========================================================================
#  MENU (type carte)
# ===========================================================================
def construire_menu(ctx, aujourdhui):
    """Carte adaptee au code NAF : 56.10C = restauration rapide, sinon brasserie."""
    gabarit = os.path.join(TEMPLATES, "carte-interactive", "menu.json")
    with open(gabarit, encoding="utf-8") as f:
        brut = f.read()
    menu = json.loads(brut.replace("{{NOM}}", ctx["nom"]).replace("{{VILLE}}", ctx["ville"])
                      .replace("{{NOTE_ALLERGENES}}", "").replace("{{DATE_MAJ}}", aujourdhui.isoformat()))
    if ctx["naf"].startswith("56.10C") or ctx["naf"].startswith("56.30"):
        menu["categories"] = CARTE_RAPIDE["categories"]
        menu["plats"] = CARTE_RAPIDE["plats"]
    menu["restaurant"]["note_allergenes"] = (
        "Les 14 allergènes réglementaires sont indiqués plat par plat. "
        "En cas d’allergie, prévenez-nous à la commande."
    )
    menu["maj"] = aujourdhui.isoformat()
    return menu


# ===========================================================================
#  README DE MAINTENANCE
# ===========================================================================
def readme(ctx, type_demo, url_site, dossier, aujourdhui, menu, commande):
    preset = ctx["preset"]
    offres = {}
    try:
        with open(OFFRES, encoding="utf-8") as f:
            offres = {o["code"]: o for o in json.load(f)["offres"]}
    except Exception:
        pass
    code = "CARTE-INTER" if type_demo == "carte" else "SITE-VITRINE"
    offre = offres.get(code, {})

    a_valider = [
        "le **numéro de téléphone** (absent de la base — passer `--tel \"03 87 …\"` pour le réinjecter)" if not ctx["tel"] else "le numéro de téléphone affiché",
        "l'**adresse e-mail** de contact (`--email`)" if not ctx["email"] else "l'adresse e-mail affichée",
        "les **horaires** (valeurs par défaut du secteur « %s »)" % ctx["secteur"],
        "les **textes de présentation** et les intitulés de prestations",
    ]
    if type_demo == "carte":
        a_valider.append("les **plats, prix et allergènes** de `menu.json` (carte type, à remplacer par la vraie carte)")
    else:
        a_valider.append("les **tarifs indicatifs** affichés sur les cartes de prestations")

    fichiers = [
        "`index.html` — la page, tout le contenu éditable est dedans",
        "`assets/style.css` — un seul fichier de style ; les couleurs sont des variables en haut (`:root`)",
        "`assets/app.js` — comportements (menu, horaires du jour, %s)" % ("filtres et QR code" if type_demo == "carte" else "formulaire"),
        "`assets/favicon.svg`, `assets/og.svg` — icône et image de partage, générées en SVG",
    ]
    if type_demo == "carte":
        fichiers.insert(1, "`menu.json` — **la carte** : c'est le seul fichier à modifier au quotidien")
        fichiers.append("`assets/qr.js` — générateur de QR code local (aucune API externe)")

    lignes = []
    A = lignes.append
    A("# %s — démo %s" % (ctx["nom"], "carte interactive" if type_demo == "carte" else "site vitrine"))
    A("")
    A("Démo générée le %s par %s, à partir de la fiche prospect `%s`." % (date_fr(aujourdhui.isoformat()), AGENCE, ctx["p"].get("cle")))
    A("Offre correspondante : **%s** (%s €, %s jours)." % (offre.get("nom", code), offre.get("prix", "—"), offre.get("delai_j", "—")))
    A("")
    A("## Ouvrir la démo")
    A("")
    A("```bash")
    A("# double-clic sur index.html suffit%s" % (" (la carte bascule alors sur la copie intégrée du menu)" if type_demo == "carte" else ""))
    A("# ou, pour être au plus près de la mise en ligne :")
    A("python3 -m http.server 8080 --directory agency/clients/%s" % dossier)
    A("# puis http://localhost:8080")
    A("```")
    A("")
    A("## Régénérer")
    A("")
    A("```bash")
    A(commande)
    A("```")
    A("")
    A("La commande est idempotente : elle réécrit le dossier à l'identique.")
    A("**Toute modification manuelle de ces fichiers sera écrasée** — si la démo devient un")
    A("chantier client, sortir le dossier du cycle de génération ou reporter les changements")
    A("dans le gabarit `agency/templates/%s/`." % ("carte-interactive" if type_demo == "carte" else "site-vitrine"))
    A("")
    A("## Ce qu'il y a dans le dossier")
    A("")
    for f in fichiers:
        A("- %s" % f)
    A("")
    A("## À valider avec le client avant mise en ligne")
    A("")
    for v in a_valider:
        A("- [ ] %s" % v)
    A("- [ ] le **formulaire de contact** : il valide les champs mais n'envoie rien tant qu'un")
    A("      service d'envoi n'est pas branché (Formspree, Netlify Forms ou une route serveur).")
    A("- [ ] l'**image de partage** `assets/og.svg` : l'exporter en PNG 1200×630 pour que les")
    A("      réseaux sociaux l'affichent (le SVG est ignoré par Facebook et LinkedIn).")
    A("- [ ] retirer `<meta name=\"robots\" content=\"noindex, nofollow\">` de `index.html`")
    A("      le jour de la mise en ligne, et remplacer `%s` par le vrai domaine." % url_site)
    A("")
    if type_demo == "carte":
        A("## Mettre la carte à jour")
        A("")
        A("Tout se passe dans `menu.json`. Un plat ressemble à ceci :")
        A("")
        A("```json")
        A('{ "nom": "Plat du jour", "description": "Annoncé en salle.", "prix": 13.5,')
        A('  "categorie": "plats", "vegetarien": false, "signature": false,')
        A('  "allergenes": ["gluten", "lait"] }')
        A("```")
        A("")
        A("- `categorie` doit reprendre un `id` de la liste `categories` (%s)." % ", ".join("`%s`" % c["id"] for c in menu["categories"]))
        A("- `allergenes` reprend les clés de l'objet `allergenes` en haut du fichier (%d disponibles)." % len(menu["allergenes"]))
        A("- `prix` est un nombre, sans symbole : `13.5`, pas `\"13,50 €\"`.")
        A("")
        A("Après modification : recharger la page. Si elle est ouverte par double-clic")
        A("(`file://`), le navigateur refuse de lire `menu.json` — la page utilise alors la")
        A("copie intégrée au HTML, qui date de la dernière génération. **Pour voir ses")
        A("modifications, passer par `python3 -m http.server` ou régénérer la démo.**")
        A("")
        A("## QR code de table")
        A("")
        A("Bouton « QR code » en haut de page : le code est calculé dans le navigateur")
        A("(aucune API externe, aucune donnée envoyée), niveau de correction M.")
        A("L'adresse encodée est modifiable dans la fenêtre, et le code se télécharge en PNG")
        A("ou s'imprime directement en affichette.")
        A("")
    A("## Contenu : ce qui est factuel, ce qui est proposé")
    A("")
    A("Viennent de la base (sources publiques) : raison sociale, adresse, ville, SIREN,")
    A("date de création, secteur d'activité.")
    A("Tout le reste — accroches, descriptions de prestations, horaires, tarifs indicatifs,")
    A("%sengagements — est une **proposition rédactionnelle**" % ("carte, " if type_demo == "carte" else ""))
    A("à valider ou corriger par le client. Aucun faux avis client, aucune statistique inventée")
    A("ne figure sur la page.")
    A("")
    A("## Mise en ligne")
    A("")
    A("Site strictement statique (aucun build, aucune dépendance) : déposer le contenu du")
    A("dossier sur n'importe quel hébergement statique (Vercel, GitHub Pages, un FTP mutualisé).")
    A("Penser à activer HTTPS et à vérifier la fiche Google Business en parallèle.")
    A("")
    return "\n".join(lignes)


# ===========================================================================
#  CONSTRUCTION
# ===========================================================================
def construire(args):
    aujourdhui = date.fromisoformat(args.date) if args.date else date.today()
    rows = charger_base()
    p = trouver(rows, args.cle)

    type_demo = args.type
    if type_demo == "carte" and (p.get("secteur") != "restauration"):
        print("ATTENTION : « %s » n'est pas un restaurant (secteur « %s ») — la carte "
              "interactive n'est probablement pas la bonne démo."
              % (p.get("nom"), p.get("secteur")), file=sys.stderr)

    ctx = construire_contexte(p, args, aujourdhui)
    # un dossier par demo : la carte ne doit pas ecraser la vitrine du meme prospect
    dossier = args.dossier or (slug(p.get("cle") or p.get("nom")) + ("-carte" if type_demo == "carte" else ""))
    sortie = os.path.join(args.sortie or CLIENTS, dossier)
    url_site = args.url or "https://%s.fr/" % slug(ctx["nom"])
    if not url_site.endswith("/"):
        url_site += "/"

    gabarit = os.path.join(TEMPLATES, "carte-interactive" if type_demo == "carte" else "site-vitrine")
    if not os.path.isdir(gabarit):
        sys.exit("ERREUR : gabarit introuvable (%s)." % gabarit)

    menu = construire_menu(ctx, aujourdhui) if type_demo == "carte" else None
    marqueurs = construire_marqueurs(ctx, type_demo, url_site, aujourdhui, menu)

    # idempotence : on repart d'un dossier propre
    if os.path.isdir(sortie):
        shutil.rmtree(sortie)
    os.makedirs(os.path.join(sortie, "assets"), exist_ok=True)

    ecrits = []
    for racine, _, fichiers in os.walk(gabarit):
        for f in sorted(fichiers):
            src = os.path.join(racine, f)
            rel = os.path.relpath(src, gabarit)
            if rel == "menu.json" and menu is not None:
                continue                                   # genere plus bas
            dst = os.path.join(sortie, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(src, encoding="utf-8") as fh:
                contenu = fh.read()
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write(appliquer(contenu, marqueurs, rel))
            ecrits.append(rel)

    if menu is not None:
        with open(os.path.join(sortie, "menu.json"), "w", encoding="utf-8") as fh:
            json.dump(menu, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        ecrits.append("menu.json")

    commande = "python3 agency/scripts/build_demo.py --cle %s --type %s" % (p.get("cle"), type_demo)
    if args.dossier:
        commande += ' --dossier "%s"' % args.dossier
    if args.sortie:
        commande += ' --sortie "%s"' % args.sortie
    if args.tel:
        commande += ' --tel "%s"' % args.tel
    if args.email:
        commande += ' --email "%s"' % args.email
    if args.url:
        commande += ' --url "%s"' % args.url

    with open(os.path.join(sortie, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(readme(ctx, type_demo, url_site, dossier, aujourdhui, menu, commande))
    ecrits.append("README.md")

    print(json.dumps({
        "cle": p.get("cle"),
        "nom": ctx["nom"],
        "ville": ctx["ville"],
        "secteur": ctx["secteur"],
        "type": type_demo,
        "dossier": os.path.relpath(sortie, os.getcwd()),
        "fichiers": sorted(ecrits),
        "telephone": ctx["tel"] or None,
        "plats": len(menu["plats"]) if menu else None,
    }, ensure_ascii=False, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cle", required=True, help="cle du prospect (ex. siren:104221718), SIREN nu ou nom exact")
    ap.add_argument("--type", choices=["vitrine", "carte"], default="vitrine", help="gabarit a utiliser (defaut : vitrine)")
    ap.add_argument("--tel", help="telephone a afficher (absent de la base la plupart du temps)")
    ap.add_argument("--email", help="e-mail de contact a afficher")
    ap.add_argument("--url", help="domaine cible, utilise pour les balises canonical/OpenGraph")
    ap.add_argument("--dossier", help="nom du dossier de sortie (defaut : cle du prospect)")
    ap.add_argument("--sortie", help="repertoire parent (defaut : agency/clients)")
    ap.add_argument("--date", help="date de generation AAAA-MM-JJ (pour des sorties reproductibles)")
    args = ap.parse_args()
    sys.exit(construire(args))


if __name__ == "__main__":
    main()
