import requests
import json
from datetime import datetime, timezone
import os

API_URL = "https://api-v3.doinsport.club/clubs/bookings?activityType=event&startAt[after]=2026-02-04T23:00:00Z&order[startAt]=asc&club.id=5e956442-62fa-4f6f-9048-d51fbd7d42cf&itemsPerPage=20&timetableBlockPrice.category.id=478ed804-431f-4f6e-9195-920e7bf37732"
SEEN_FILE = "seen_tournaments.json"
NTFY_TOPIC = "tournois-padel-arena-12345"

def load_seen_ids():
    """Charge les IDs depuis le fichier de sauvegarde."""
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, 'r') as f:
        try:
            return set(json.load(f))
        except json.JSONDecodeError:
            return set()

def save_seen_ids(ids):
    """Sauvegarde les IDs dans le fichier."""
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(ids), f)

def send_notification(title, message):
    """Envoie une notification via ntfy.sh."""
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={"Title": title.encode('utf-8')}
        )
        print(f"✅ Notification envoyée pour : {title}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de la notification : {e}")

def test_api():
    # --- Construction dynamique de l'URL pour chercher les tournois à partir de maintenant ---
    now_utc_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    api_url = f"https://api-v3.doinsport.club/clubs/bookings?activityType=event&startAt[after]={now_utc_str}&order[startAt]=asc&club.id=5e956442-62fa-4f6f-9048-d51fbd7d42cf&itemsPerPage=20&timetableBlockPrice.category.id=478ed804-431f-4f6e-9195-920e7bf37732"

    print(f"Recherche de nouveaux tournois ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')})...")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status() # Lève une exception pour les codes d'erreur (4xx ou 5xx)

        # Gérer les réponses API incohérentes (parfois une liste, parfois un dictionnaire)
        data = response.json()
        if isinstance(data, dict):
            items = data.get('hydra:member', [])
        elif isinstance(data, list):
            items = data
        else:
            items = []

        if not items:
            print("Aucun tournoi à venir trouvé.")
            return

        seen_ids = load_seen_ids()
        current_ids = set()
        new_tournaments_found = False

        for item in items:
            # Création d'un identifiant unique plus robuste en combinant titre et date
            title = item.get('title', '')
            start_at = item.get('startAt', '')
            item_id = f"{title}-{start_at}"

            if not item_id:
                continue
            
            current_ids.add(item_id)

            # C'est un nouveau tournoi s'il n'est pas dans nos archives
            if item_id not in seen_ids:
                new_tournaments_found = True
                start_at_str = item.get('startAt', '')
                
                # Formatage de la date pour la notification
                try:
                    date_obj = datetime.fromisoformat(start_at_str.replace('Z', '+00:00'))
                    date_formatted = date_obj.strftime('%d/%m/%Y à %Hh%M')
                    message = f"Le {date_formatted}"
                except (ValueError, TypeError):
                    message = "Date non spécifiée"
                
                send_notification(title, message)
        
        if not new_tournaments_found:
            print("Pas de nouveau tournoi détecté.")

        # Mettre à jour la liste des tournois vus pour la prochaine fois
        save_seen_ids(current_ids)

    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion : {e}")

if __name__ == "__main__":
    test_api()
    # input("\nAppuyez sur Entrée pour quitter...") # Mis en commentaire pour l'automatisation