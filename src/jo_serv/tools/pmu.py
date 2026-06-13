import json
import logging
import math
import time
from enum import Enum
from typing import Any
import random

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

        avance = max(0, performance / 10)

        self.position += avance


def simuler_course(chevaux, distance=2000):

    tour = 0

    while True:
        tour += 1

        print(f"\n--- Tour {tour} ---")

        for cheval in chevaux:
            cheval.avancer(distance)

            if not cheval.mort:
                print(
                    f"{cheval.nom:<10} "
                    f"{cheval.position:>7.1f} m"
                    f"{' (blessé)' if cheval.blesse else ''}"
                )

        vivants = [c for c in chevaux if not c.mort]

        if not vivants:
            print("\nTous les chevaux sont hors course.")
            return

        gagnants = [c for c in vivants if c.position >= distance]

        if gagnants:
            gagnant = max(gagnants, key=lambda c: c.position)

            print("\n🏆 GAGNANT")
            print(f"{gagnant.nom}")
            print(f"Distance : {gagnant.position:.1f} m")
            return


# Exemple de chevaux

chevaux = [
    Cheval("Tornado", 85, 90, 80, 75, 90, 5, 0),
    Cheval("Flash", 90, 75, 70, 80, 85, 6, 20),
    Cheval("Comete", 80, 85, 95, 70, 88, 4, 5),
    Cheval("Eclair", 95, 70, 65, 90, 80, 8, 40),
]


def pmu_process(data_dir: str) -> None:
    """This process handles PMU"""
    logger = logging.getLogger(__name__)
    logger.info("PMU process start")

    while True:
        #TODO trig nouvelle course
        simuler_course(chevaux)
        time.sleep(120)