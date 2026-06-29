import json
import logging
import math
import time
from enum import Enum
from threading import Lock
from typing import Any, List, Dict
import random
import os
from jo_serv.tools.tools import send_notif
COURSE_INTERVAL_S = 900  # Intervalle entre les courses en secondes; 15 minutes
COURSE_DURATION_S = 30  # Durée de la course en secondes
COURSE_TERMINEE_S = 15  # Durée d'affichage du gagnant avant la prochaine course
LEADERBOARD_FILENAME = "leaderboard.json"  # Classement des parieurs PMU

# Compteur de "pushes" en mémoire (nom_cheval -> nombre de clics).
# Les clics des utilisateurs sont accumulés ici plutôt que d'écrire le fichier
# de course à chaque clic : c'est beaucoup plus rapide sous forte charge.
# A chaque tour de simulation, ``avancer`` consomme ces pushes et les ajoute
# (1 par clic) aux bornes min/max du tirage aléatoire pour aider très
# légèrement le cheval. Le verrou dédié est volontairement distinct de
# ``pmu_mutex`` pour ne jamais bloquer les écritures de fichiers.
PMU_PUSHES: Dict[str, int] = {}
PMU_PUSH_MUTEX = Lock()
PMU_NOTIF_MUTEX = Lock()  # Mutex 



def consume_pushes(nom: str) -> int:
    """Récupère puis remet à zéro le nombre de pushes d'un cheval.

    Opération mémoire pure protégée par ``PMU_PUSH_MUTEX`` : très rapide,
    indépendante des accès disque.
    """
    with PMU_PUSH_MUTEX:
        count = PMU_PUSHES.get(nom, 0)
        if count:
            PMU_PUSHES[nom] = 0
        return count


def reset_pushes() -> None:
    """Réinitialise tous les compteurs de pushes (nouvelle course)."""
    with PMU_PUSH_MUTEX:
        PMU_PUSHES.clear()

class RaceStatus(Enum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINEE = "terminee"


class Cheval:
    def __init__(
        self,
        nom,
        vitesse,
        entrainement,
        endurance,
        sabot,
        sante,
        age,
        dopage,
    ):
        self.nom = nom
        self.vitesse = vitesse
        self.entrainement = entrainement
        self.endurance = endurance
        self.sabot = sabot
        self.sante = sante
        self.age = age
        self.dopage = dopage

        self.position = 0
        self.blesse = False
        self.mort = False
        self.paris: List[str] = []  # Liste des usernames qui ont parié sur ce cheval

    def to_dict(self) -> Dict:
        """Convertit le cheval en dictionnaire pour JSON"""
        return {
            "nom": self.nom,
            "vitesse": self.vitesse,
            "entrainement": self.entrainement,
            "endurance": self.endurance,
            "sabot": self.sabot,
            "sante": self.sante,
            "age": self.age,
            "dopage": self.dopage,
            "position": self.position,
            "blesse": self.blesse,
            "mort": self.mort,
            "paris": self.paris,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Cheval':
        """Crée un cheval depuis un dictionnaire"""
        cheval = Cheval(
            nom=data["nom"],
            vitesse=data["vitesse"],
            entrainement=data["entrainement"],
            endurance=data["endurance"],
            sabot=data["sabot"],
            sante=data["sante"],
            age=data["age"],
            dopage=data["dopage"],
        )
        cheval.position = data.get("position", 0)
        cheval.blesse = data.get("blesse", False)
        cheval.mort = data.get("mort", False)
        cheval.paris = data.get("paris", [])
        return cheval


    def avancer(self, distance_course):
        # Distribution équitable : chaque cheval avance d'une valeur aléatoire
        # tirée de la même distribution pour tous, sans tenir compte de ses
        # statistiques. Tous les chevaux ont donc exactement la même chance de
        # gagner, tout en continuant à progresser à chaque tour.
        # use COURSE_DURATION_S to scale the advance based on the course duration

        # avance = random.uniform(distance_course * 0.01, distance_course * 0.1)
        # Scale the advance based on the course duration
        # Chaque clic accumulé pousse très légèrement le cheval : on ajoute 1
        # par clic aux bornes min/max du tirage. Les pushes sont consommés ici
        # (lecture + reset atomiques) sans aucun accès disque.
        boost = consume_pushes(self.nom)
        avance = random.uniform(
            distance_course / (COURSE_DURATION_S * 5) + boost,
            distance_course / COURSE_DURATION_S + boost,
        )
        self.position += avance

    @staticmethod
    def push_cheval(cheval_name: str) -> None:
        """Enregistre un clic ("push") sur un cheval.

        Très optimisé : on incrémente uniquement un compteur en mémoire,
        protégé par ``PMU_PUSH_MUTEX``. Aucun fichier n'est lu/écrit ici, ce
        qui permet d'absorber un grand nombre de clics simultanés. Le boost
        sera appliqué au prochain tour de simulation via ``avancer``.
        """
        nom = cheval_name.strip().strip('"')
        print("Pushed cheval:", nom)
        with PMU_PUSH_MUTEX:
            PMU_PUSHES[nom] = PMU_PUSHES.get(nom, 0) + 1
class Race:
    def __init__(self, race_id: str, chevaux: List[Cheval], distance: int = 2000):
        self.race_id = race_id
        self.chevaux = chevaux
        self.distance = distance
        self.status = RaceStatus.EN_ATTENTE
        self.tour = 0
        self.gagnant = None
        self.course_suivante = 0

    def to_dict(self) -> Dict:
        """Convertit la course en dictionnaire pour JSON"""
        return {
            "race_id": self.race_id,
            "distance": self.distance,
            "status": self.status.value,
            "tour": self.tour,
            "gagnant": self.gagnant,
            "chevaux": [cheval.to_dict() for cheval in self.chevaux],
            "course_suivante": self.course_suivante,
        }

    @staticmethod
    def from_dict(data: Dict) -> 'Race':
        """Crée une course depuis un dictionnaire"""
        chevaux = [Cheval.from_dict(c) for c in data["chevaux"]]
        race = Race(
            race_id=data["race_id"],
            chevaux=chevaux,
            distance=data.get("distance", 2000),
        )
        race.status = RaceStatus(data["status"])
        race.tour = data.get("tour", 0)
        race.gagnant = data.get("gagnant")
        race.course_suivante = data.get("course_suivante", 0)
        return race

    def save_to_file(self, data_dir: str) -> None:
        """Sauvegarde la course dans un fichier JSON"""
        race_dir = os.path.join(data_dir, "pmu_race")
        os.makedirs(race_dir, exist_ok=True)
        filepath = os.path.join(race_dir, f"pmu_race_{self.race_id}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def load_from_file(data_dir: str, race_id: str) -> 'Race':
        """Charge une course depuis un fichier JSON"""
        filepath = os.path.join(data_dir, "pmu_race", f"pmu_race_{race_id}.json")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Race.from_dict(data)


def _get_pmu_lock():
    """Return the shared PMU lock defined in the server module.

    The import is performed lazily inside the function on purpose: ``server.py``
    imports this module at load time (``from jo_serv.tools.pmu import ...``)
    *before* it defines ``pmu_mutex``. A module-level import here would
    therefore create a circular import. By the time these functions actually
    run, ``server.py`` is fully initialised and the lock is available.
    """
    from jo_serv.server.server import pmu_mutex

    return pmu_mutex


def _leaderboard_path(data_dir: str) -> str:
    """Renvoie le chemin du fichier de classement PMU."""
    return os.path.join(data_dir, "pmu_race", LEADERBOARD_FILENAME)


def load_leaderboard(data_dir: str) -> Dict[str, int]:
    """Charge le classement des parieurs depuis ``leaderboard.json``.

    Renvoie un dictionnaire ``{username: points}``. Si le fichier n'existe
    pas encore (ou est illisible), un classement vide est renvoyé.
    """
    filepath = _leaderboard_path(data_dir)
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        logging.getLogger(__name__).exception(
            "Impossible de lire le classement PMU, réinitialisation à vide"
        )
        return {}


def save_leaderboard(data_dir: str, scores: Dict[str, int]) -> None:
    """Sauvegarde le classement des parieurs dans ``leaderboard.json``."""
    race_dir = os.path.join(data_dir, "pmu_race")
    os.makedirs(race_dir, exist_ok=True)
    with open(_leaderboard_path(data_dir), "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2, ensure_ascii=False)


def update_leaderboard_for_race(race: 'Race', data_dir: str) -> None:
    """Attribue 1 point à chaque parieur ayant misé sur le cheval gagnant.

    L'appelant est responsable de la prise du verrou ``pmu_mutex`` afin que la
    séquence lecture + mise à jour + écriture reste atomique.
    """
    if not race.gagnant:
        # Aucun gagnant (tous les chevaux hors course) : rien à attribuer.
        return

    scores = load_leaderboard(data_dir)
    for cheval in race.chevaux:
        if cheval.nom == race.gagnant:
            for username in cheval.paris:
                scores[username] = scores.get(username, 0) + 1
            break

    save_leaderboard(data_dir, scores)


def get_leaderboard(data_dir: str) -> List[Dict]:
    """Renvoie le classement trié par points décroissants.

    Format : ``[{"username": str, "points": int}, ...]``.
    """
    scores = load_leaderboard(data_dir)
    classement = [
        {"username": username, "points": points}
        for username, points in scores.items()
    ]
    classement.sort(key=lambda entry: entry["points"], reverse=True)
    return classement



def simuler_course(race: Race, data_dir: str = None):
    """Simule une course de chevaux et sauvegarde l'état"""
    pmu_lock = _get_pmu_lock() if data_dir else None

    race.status = RaceStatus.EN_COURS
    if data_dir:
        with pmu_lock:
            race.save_to_file(data_dir)
    # Nouvelle course : on repart de zéro pour les clics accumulés.
    reset_pushes()
    while True:
        race.tour += 1

        print(f"\n--- Tour {race.tour} ---")

        race.course_suivante = 0
        for cheval in race.chevaux:
            cheval.avancer(race.distance)

        # Sauvegarde l'état après chaque tour
        if data_dir:
            with pmu_lock:
                race.save_to_file(data_dir)
        gagnants = [c for c in race.chevaux if c.position >= race.distance]

        if gagnants:
            gagnant = max(gagnants, key=lambda c: c.position)

            # print("\n🏆 GAGNANT")
            # print(f"{gagnant.nom}")
            # print(f"Distance : {gagnant.position:.1f} m")
            
            race.status = RaceStatus.TERMINEE
            race.gagnant = gagnant.nom
            if data_dir:
                with pmu_lock:
                    race.save_to_file(data_dir)
                    # Attribuer 1 point à chaque parieur ayant misé sur le
                    # cheval gagnant (mise à jour du leaderboard.json).
                    update_leaderboard_for_race(race, data_dir)
            return
        
        time.sleep(1)


# Exemple de chevaux

chevaux_exemple = [
    Cheval("Tornafion", 85, 90, 80, 75, 90, 5, 0),
    Cheval("Cluedo", 90, 75, 70, 80, 85, 6, 20),
    Cheval("Friedrich", 80, 85, 95, 70, 88, 4, 5),
    Cheval("Whisky", 95, 70, 65, 90, 80, 8, 40),
    Cheval("Maaaarc", 88, 82, 75, 85, 92, 5, 10),
    Cheval("Ouraken", 92, 78, 68, 88, 83, 7, 30),
    Cheval("Delfino", 83, 91, 90, 78, 87, 6, 15),
    Cheval("Florence", 87, 88, 85, 72, 90, 4, 8),
]


def pmu_process(data_dir: str) -> None:
    """This process handles PMU"""
    logger = logging.getLogger(__name__)
    logger.info("PMU process start")

    pmu_lock = _get_pmu_lock()
    race_counter = 1

    while True:
        # Création d'une nouvelle course
        race_id = f"{race_counter}"
        logger.info(f"Création de la course {race_id}")
        
        # Clonage des chevaux pour ne pas réutiliser les mêmes instances
        chevaux_course = [
            Cheval(
                nom=c.nom,
                vitesse=c.vitesse,
                entrainement=c.entrainement,
                endurance=c.endurance,
                sabot=c.sabot,
                sante=c.sante,
                age=c.age,
                dopage=c.dopage,
            )
            for c in chevaux_exemple
        ]
        
        race = Race(race_id=race_id, chevaux=chevaux_course, distance=2000)
        with pmu_lock:
            race.save_to_file(data_dir)
        
        cpt = 0
        while (cpt < COURSE_INTERVAL_S):
            cpt += 1
            time.sleep(1)
            # Recharger depuis le fichier pour ne pas écraser les paris
            # enregistrés par save_bet pendant le compte à rebours.
            # L'opération lecture + mise à jour + écriture est protégée par
            # pmu_lock afin d'être atomique vis-à-vis de save_bet.
            if COURSE_INTERVAL_S - cpt == 60: # 1 minute avant la course, on envoit une notif
                with PMU_NOTIF_MUTEX:
                    if os.path.exists(f"{data_dir}/pmu_notif.json"):
                        notif_data = json.load(open(f"{data_dir}/pmu_notif.json", "r"))
                    else:
                        notif_data = {}
                    exclude_list = [x for x, enabled in notif_data.items() if not enabled]
                print("Eclusion list:", exclude_list)
                send_notif('all', "La prochaine course commence dans 1 minute ! Placez vos paris !", "🐎🐎🐎", data_dir, exclude_list=exclude_list)
            with pmu_lock:
                race = Race.load_from_file(data_dir, race_id)
                race.course_suivante = COURSE_INTERVAL_S - cpt
                race.save_to_file(data_dir)  # met à jour course_suivante

        # Recharger la course depuis le fichier pour récupérer les paris enregistrés
        with pmu_lock:
            race = Race.load_from_file(data_dir, race_id)
            race.course_suivante = 0
            race.save_to_file(data_dir)
        total_paris = sum(len(cheval.paris) for cheval in race.chevaux)
        logger.info(f"Course {race_id}: {total_paris} paris enregistrés")
        
        # Simulation de la course

        simuler_course(race, data_dir)
        
        logger.info(f"Course {race_id} terminée. Gagnant: {race.gagnant}")

        # For debug to wait for results
        
        time.sleep(COURSE_TERMINEE_S)

        race_counter += 1



def get_latest_race(data_dir: str) -> Dict:
    """Récupère la dernière course enregistrée"""
    import glob
    race_files = glob.glob(os.path.join(data_dir, "pmu_race/pmu_race_*.json"))
    
    if not race_files:
        return {"error": "Aucune course disponible"}
    
    # Trier par timestamp (dernier fichier créé)
    latest_file = max(race_files, key=os.path.getmtime)
    with _get_pmu_lock():
        with open(latest_file, "r", encoding="utf-8") as f:
            return json.load(f)


def get_last_finished_race(data_dir: str) -> Dict:
    """Récupère les résultats de la dernière course terminée.

    Renvoie un dictionnaire décrivant la dernière course ``TERMINEE`` avec le
    cheval gagnant et les listes des parieurs gagnants / perdants :

    ``{
        "race_id": str,
        "gagnant": str | None,
        "winners": [{"username": str, "cheval": str}, ...],
        "losers": [{"username": str, "cheval": str}, ...],
    }``

    Renvoie ``None`` si aucune course n'est encore terminée.
    """
    import glob

    race_files = glob.glob(os.path.join(data_dir, "pmu_race/pmu_race_*.json"))
    if not race_files:
        return None

    # Parcourir du plus récent au plus ancien pour trouver la dernière
    # course effectivement terminée.
    for race_file in sorted(race_files, key=os.path.getmtime, reverse=True):
        with open(race_file, "r", encoding="utf-8") as f:
            race_data = json.load(f)

        if race_data.get("status") != RaceStatus.TERMINEE.value:
            continue

        gagnant = race_data.get("gagnant")
        winners = []
        losers = []
        for cheval in race_data.get("chevaux", []):
            nom = cheval.get("nom")
            for username in cheval.get("paris", []):
                parieur = {"username": username, "cheval": nom}
                if nom == gagnant:
                    winners.append(parieur)
                else:
                    losers.append(parieur)

        return {
            "race_id": race_data.get("race_id"),
            "gagnant": gagnant,
            "winners": winners,
            "losers": losers,
        }

    return None


def get_all_races(data_dir: str) -> List[Dict]:
    """Récupère toutes les courses enregistrées"""
    import glob
    
    race_files = glob.glob(os.path.join(data_dir, "pmu_race/pmu_race_*.json"))
    
    races = []
    for race_file in sorted(race_files, key=os.path.getmtime, reverse=True):
        with open(race_file, "r", encoding="utf-8") as f:
            races.append(json.load(f))
    
    return races


def get_next_race_id(data_dir: str) -> str:
    """Récupère l'ID de la course actuellement ouverte aux paris.

    On se base sur la course la plus récente (même logique que
    ``get_latest_race`` et que ce que voit le client via GET /pmu), et non sur
    la plus ancienne course ``EN_ATTENTE``. Sinon les paris pouvaient être
    dirigés vers un ancien fichier resté en ``EN_ATTENTE`` (par ex. après un
    arrêt du serveur pendant un compte à rebours), ce qui faisait que la course
    en cours affichait « 0 pari » alors que le pari avait bien été enregistré
    ailleurs.
    """
    import glob

    race_files = glob.glob(os.path.join(data_dir, "pmu_race/pmu_race_*.json"))

    if not race_files:
        return None

    # La course courante est toujours la plus récemment modifiée
    # (pmu_process réécrit son fichier chaque seconde pendant le compte à rebours).
    latest_file = max(race_files, key=os.path.getmtime)
    with open(latest_file, "r", encoding="utf-8") as f:
        race_data = json.load(f)

    if race_data.get("status") == RaceStatus.EN_ATTENTE.value:
        return race_data.get("race_id")

    return None


def save_bet(data_dir: str, race_id: str, username: str, cheval_nom: str) -> bool:
    """Enregistre un pari pour une course donnée
    
    Returns:
        bool: True si le pari a été enregistré, False si la course n'accepte plus de paris
    """
    try:
        race = Race.load_from_file(data_dir, race_id)
        
        # Vérifier que la course est toujours en attente
        if race.status != RaceStatus.EN_ATTENTE:
            return False
        
        # Trouver le cheval et ajouter le username à sa liste de paris
        for cheval in race.chevaux:
            if cheval.nom == cheval_nom:
                # Retirer l'ancien pari de ce joueur si existant
                for c in race.chevaux:
                    if username in c.paris:
                        c.paris.remove(username)
                
                # Ajouter le nouveau pari
                if username not in cheval.paris:
                    cheval.paris.append(username)
                
                race.save_to_file(data_dir)
                return True
        
        return False  # Cheval non trouvé
    except Exception as e:
        logging.getLogger(__name__).exception(
            f"Erreur lors de l'enregistrement du pari ({username} -> {cheval_nom}): {e}"
        )
        return False