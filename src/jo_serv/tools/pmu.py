import json
import logging
import math
import time
from enum import Enum
from typing import Any, List, Dict
import random
import os

COURSE_INTERVAL_S = 10  # Intervalle entre les courses en secondes

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

    def calcul_performance(self):

        performance = (
            self.vitesse * 0.35
            + self.entrainement * 0.25
            + self.endurance * 0.20
            + self.sabot * 0.10
            + self.sante * 0.10
        )

        performance += self.dopage * 0.15

        return performance

    def avancer(self, distance_course):

        if self.mort:
            return

        fatigue = self.position / max(self.endurance * 20, 1)

        performance = self.calcul_performance()

        performance *= max(0.3, 1 - fatigue * 0.3)

        # Aléatoire
        performance += random.uniform(-10, 10)

        # Risque de blessure
        risque_blessure = (
            0.001
            + self.age * 0.0002
            + self.dopage * 0.0005
            + fatigue * 0.01
        )

        if not self.blesse and random.random() < risque_blessure:
            self.blesse = True
            print(f"⚠️ {self.nom} se blesse !")

        if self.blesse:
            performance *= 0.5

        # Risque de décès
        risque_deces = (
            0.00001
            + self.age * 0.000005
            + self.dopage * 0.00001
        )

        if random.random() < risque_deces:
            self.mort = True
            print(f"💀 {self.nom} décède pendant la course.")
            return

        #avance = max(0, performance / 2) # about 1min course
        avance = max(0, performance * 4)  # about 20s course

        self.position += avance


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


def simuler_course(race: Race, data_dir: str = None):
    """Simule une course de chevaux et sauvegarde l'état"""
    pmu_lock = _get_pmu_lock() if data_dir else None

    race.status = RaceStatus.EN_COURS
    if data_dir:
        with pmu_lock:
            race.save_to_file(data_dir)

    while True:
        race.tour += 1

        print(f"\n--- Tour {race.tour} ---")

        race.course_suivante = 0
        for cheval in race.chevaux:
            cheval.avancer(race.distance)

            if not cheval.mort:
                print(
                    f"{cheval.nom:<10} "
                    f"{cheval.position:>7.1f} m"
                    f"{' (blessé)' if cheval.blesse else ''}"
                )

        # Sauvegarde l'état après chaque tour
        if data_dir:
            with pmu_lock:
                race.save_to_file(data_dir)

        vivants = [c for c in race.chevaux if not c.mort]

        if not vivants:
            print("\nTous les chevaux sont hors course.")
            race.status = RaceStatus.TERMINEE
            if data_dir:
                with pmu_lock:
                    race.save_to_file(data_dir)
            return

        gagnants = [c for c in vivants if c.position >= race.distance]

        if gagnants:
            gagnant = max(gagnants, key=lambda c: c.position)

            print("\n🏆 GAGNANT")
            print(f"{gagnant.nom}")
            print(f"Distance : {gagnant.position:.1f} m")
            
            race.status = RaceStatus.TERMINEE
            race.gagnant = gagnant.nom
            if data_dir:
                with pmu_lock:
                    race.save_to_file(data_dir)
            return
        
        time.sleep(1)


# Exemple de chevaux

chevaux_exemple = [
    Cheval("Tornado", 85, 90, 80, 75, 90, 5, 0),
    Cheval("Flash", 90, 75, 70, 80, 85, 6, 20),
    Cheval("Comete", 80, 85, 95, 70, 88, 4, 5),
    Cheval("Eclair", 95, 70, 65, 90, 80, 8, 40),
    Cheval("Tempete", 88, 82, 75, 85, 92, 5, 10),
    Cheval("Ouragan", 92, 78, 68, 88, 83, 7, 30),
    Cheval("Foudre", 87, 88, 85, 72, 90, 4, 8),
    Cheval("Zephyr", 83, 91, 90, 78, 87, 6, 15),
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
        
        time.sleep(COURSE_INTERVAL_S)

        race_counter += 1



def get_latest_race(data_dir: str) -> Dict:
    """Récupère la dernière course enregistrée"""
    import glob
    
    race_files = glob.glob(os.path.join(data_dir, "pmu_race/pmu_race_*.json"))
    
    if not race_files:
        return {"error": "Aucune course disponible"}
    
    # Trier par timestamp (dernier fichier créé)
    latest_file = max(race_files, key=os.path.getmtime)
    
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