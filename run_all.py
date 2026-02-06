import subprocess
import sys
import os
import time

# Configuration des services : { "Nom": "Chemin du script run.py" }
SERVICES = {
    "AUTH-SERVICE": "auth_services/run.py",
    # "SCRAPER-SERVICE": "scraper_services/run.py",
}

processus_actifs = []

def demarrer_services():
    print("🚀 Initialisation du projet GitFetch...")
    
    for nom, chemin in SERVICES.items():
        if os.path.exists(chemin):
            print(f"[+] Lancement de {nom}...")
            # On lance chaque service comme un processus indépendant
            p = subprocess.Popen([sys.executable, chemin])
            processus_actifs.append(p)
            time.sleep(1)  # Pause pour éviter les conflits au démarrage
        else:
            print(f"[!] Erreur : Le fichier {chemin} est introuvable.")

    print("\n✅ Tous les services sont lancés.")
    print("Utilisez Ctrl+C pour arrêter tous les micro-services d'un coup.\n")

    try:
        # Garde le script parent ouvert pour surveiller les enfants
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt des services en cours...")
        for p in processus_actifs:
            p.terminate()
        print("👋 Tous les services ont été fermés proprement.")

if __name__ == "__main__":
    demarrer_services()