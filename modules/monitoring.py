# ============================================================
# MODULE MONITORING — Uptime + Alertes Telegram & WhatsApp
# Tennis IA — Fulgence N'da
# ============================================================
"""
Ce script vérifie si l'app Tennis IA est en ligne.
- Si l'app tombe → alerte Telegram (+ WhatsApp si configuré)
- Si l'app revient → notification de rétablissement
- Vérifie toutes les 5 minutes

Usage :
    python modules/monitoring.py
"""

import requests
import time
from datetime import datetime

# ============================================================
# CONFIGURATION
# ============================================================

# URL de l'application à surveiller
APP_URL = "https://fulgence10-ia-tennis.hf.space"

# Intervalle de vérification (en secondes)
INTERVALLE = 300  # 5 minutes

# Timeout pour la requête (en secondes)
TIMEOUT = 15

# ── Telegram ──
TELEGRAM_BOT_TOKEN = "8795107382:AAEogXbXdKBetgJfBQp29Rj4yIDhxkHjlXc"
TELEGRAM_CHAT_ID = "5670235092"

# ── WhatsApp CallMeBot (à remplir quand tu recevras le code) ──
CALLMEBOT_PHONE = "+2250777265053"  # Ton numéro avec indicatif
CALLMEBOT_APIKEY = ""  # Mettre le code ici quand tu l'auras (ex: "123456")

# ============================================================
# ENVOI ALERTES
# ============================================================

def envoyer_telegram(message):
    """Envoie un message via Telegram Bot."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"[✅ Telegram] Message envoyé")
            return True
        else:
            print(f"[❌ Telegram] Erreur {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"[❌ Telegram] Exception: {e}")
        return False


def envoyer_whatsapp(message):
    """Envoie un message via WhatsApp CallMeBot."""
    if not CALLMEBOT_APIKEY:
        return False  # Pas encore configuré

    try:
        import urllib.parse
        message_encode = urllib.parse.quote(message)
        url = (
            f"https://api.callmebot.com/whatsapp.php"
            f"?phone={CALLMEBOT_PHONE}"
            f"&text={message_encode}"
            f"&apikey={CALLMEBOT_APIKEY}"
        )
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"[✅ WhatsApp] Message envoyé")
            return True
        else:
            print(f"[❌ WhatsApp] Erreur {response.status_code}")
            return False
    except Exception as e:
        print(f"[❌ WhatsApp] Exception: {e}")
        return False


def envoyer_alerte(message):
    """Envoie l'alerte sur tous les canaux configurés."""
    envoyer_telegram(message)
    envoyer_whatsapp(message)


# ============================================================
# VÉRIFICATION UPTIME
# ============================================================

def verifier_app():
    """
    Vérifie si l'app est en ligne.
    Retourne (True/False, code_status, temps_reponse_ms)
    """
    try:
        debut = time.time()
        response = requests.get(APP_URL, timeout=TIMEOUT)
        duree = round((time.time() - debut) * 1000)  # en ms

        if response.status_code == 200:
            return True, response.status_code, duree
        else:
            return False, response.status_code, duree

    except requests.exceptions.Timeout:
        return False, 0, TIMEOUT * 1000

    except requests.exceptions.ConnectionError:
        return False, 0, 0

    except Exception as e:
        print(f"[❌] Erreur inattendue: {e}")
        return False, -1, 0


# ============================================================
# BOUCLE PRINCIPALE DE MONITORING
# ============================================================

def demarrer_monitoring():
    """
    Boucle infinie qui vérifie l'app toutes les X minutes.
    Envoie une alerte à la première panne détectée.
    Envoie une notification quand l'app revient en ligne.
    """
    print("=" * 60)
    print("🎾 TENNIS IA — MONITORING DÉMARRÉ")
    print(f"📍 URL surveillée : {APP_URL}")
    print(f"⏱️  Intervalle : {INTERVALLE} secondes ({INTERVALLE // 60} min)")
    print(f"📱 Telegram : {'✅ Configuré' if TELEGRAM_BOT_TOKEN else '❌ Non configuré'}")
    print(f"📱 WhatsApp : {'✅ Configuré' if CALLMEBOT_APIKEY else '⏳ En attente du code'}")
    print("=" * 60)

    # Envoyer un message de démarrage
    envoyer_telegram(
        "🎾 *TENNIS IA — Monitoring activé*\n\n"
        f"📍 URL : `{APP_URL}`\n"
        f"⏱️ Vérification toutes les {INTERVALLE // 60} min\n"
        f"📅 Démarré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    )

    app_etait_en_ligne = True
    nb_pannes_consecutives = 0
    derniere_alerte = None

    while True:
        maintenant = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        en_ligne, code, duree = verifier_app()

        if en_ligne:
            # ── App en ligne ──
            if not app_etait_en_ligne:
                # L'app vient de revenir en ligne !
                message = (
                    "✅ *TENNIS IA — App rétablie !*\n\n"
                    f"🟢 L'app est de retour en ligne\n"
                    f"⏱️ Temps de réponse : {duree} ms\n"
                    f"📅 {maintenant}\n"
                    f"⚠️ Panne précédente : {nb_pannes_consecutives} vérification(s) échouée(s)"
                )
                envoyer_alerte(message)
                nb_pannes_consecutives = 0

            app_etait_en_ligne = True
            print(f"[{maintenant}] ✅ EN LIGNE — {duree} ms — Code {code}")

        else:
            # ── App en panne ──
            nb_pannes_consecutives += 1

            if app_etait_en_ligne or nb_pannes_consecutives % 6 == 0:
                # Première panne OU rappel toutes les 30 min (6 × 5 min)
                if code == 0:
                    raison = "Timeout (l'app ne répond pas)"
                elif code == 502:
                    raison = "Bad Gateway (serveur surchargé)"
                elif code == 503:
                    raison = "Service Unavailable (app en redémarrage ?)"
                elif code == 500:
                    raison = "Erreur serveur interne"
                else:
                    raison = f"Code HTTP {code}" if code > 0 else "Connexion impossible"

                message = (
                    "🚨 *TENNIS IA — APP EN PANNE !*\n\n"
                    f"🔴 L'app ne répond plus\n"
                    f"📍 URL : `{APP_URL}`\n"
                    f"❌ Raison : {raison}\n"
                    f"📅 {maintenant}\n"
                    f"🔄 Panne n°{nb_pannes_consecutives}\n\n"
                    f"👉 Vérifie sur HuggingFace Spaces"
                )
                envoyer_alerte(message)

            app_etait_en_ligne = False
            print(f"[{maintenant}] 🔴 HORS LIGNE — Code {code} — Panne #{nb_pannes_consecutives}")

        # Attendre avant la prochaine vérification
        time.sleep(INTERVALLE)


# ============================================================
# TEST RAPIDE (vérifie une seule fois + envoie un test)
# ============================================================

def test_rapide():
    """Test rapide : vérifie l'app et envoie un message test."""
    print("🧪 Test rapide du monitoring...")
    print()

    # Test connexion app
    en_ligne, code, duree = verifier_app()
    if en_ligne:
        print(f"✅ App en ligne — {duree} ms — Code {code}")
    else:
        print(f"🔴 App hors ligne — Code {code}")

    print()

    # Test Telegram
    print("📱 Test Telegram...")
    ok_tg = envoyer_telegram(
        "🧪 *TENNIS IA — Test monitoring*\n\n"
        f"✅ Telegram fonctionne !\n"
        f"🎾 App : {'✅ En ligne' if en_ligne else '🔴 Hors ligne'}\n"
        f"📅 {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
    )

    # Test WhatsApp
    if CALLMEBOT_APIKEY:
        print("📱 Test WhatsApp...")
        ok_wa = envoyer_whatsapp(
            "🧪 TENNIS IA — Test monitoring\n"
            f"✅ WhatsApp fonctionne !\n"
            f"🎾 App : {'En ligne' if en_ligne else 'Hors ligne'}"
        )
    else:
        print("📱 WhatsApp : ⏳ Pas encore configuré (CALLMEBOT_APIKEY vide)")

    print()
    print("🧪 Test terminé !")


# ============================================================
# POINT D'ENTRÉE
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Mode test : python modules/monitoring.py test
        test_rapide()
    else:
        # Mode monitoring : python modules/monitoring.py
        demarrer_monitoring()