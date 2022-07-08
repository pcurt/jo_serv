import datetime
import hashlib
import json
import logging
import os
import shutil
import time
from typing import Any

from jo_serv.server.server import canva_array_mutex, live_update_mutex
from jo_serv.tools.tools import palette_colors

previous_sha256 = [0] * 100


def canva_png_creator(data_dir: str) -> None:
    """Create a ppm file then a png, based on modified pixels every 5 sec"""
    logger = logging.getLogger(__name__)
    logger.info("Canva png creator start")
    logger.debug(f"Data dir {data_dir}")
    palette = dict(
        blue="0 0 255",
        red="255 0 0",
        green="0 128 0",
        black="0 0 0",
        white="255 255 255",
        darkblue="0 0 139",
        lightblue="173 216 230",
        lightgreen="144 238 144",
        yellow="255 255 0",
        brown="139 69 19",
        orange="255 140 0",
        pink="255 192 203",
        lightgrey="211 211 211",
        grey="128 128 128",
        purple="128 0 128",
    )

    naming = "abcdefghijklmnopqrst"
    number_of_canva = 16
    while True:
        try:
            no_modif = True
            for canva_number in range(number_of_canva):
                with open(
                    f"{data_dir}/teams/canva/canva{canva_number}.sha256", "r"
                ) as file:
                    cur_sha = file.read()
                if previous_sha256[canva_number] != cur_sha:
                    previous_sha256[canva_number] = cur_sha
                    no_modif = False
                else:
                    continue  # nothing to be done here sha is the same
                canva_array_mutex[canva_number].acquire()
                try:
                    canva = json.load(
                        open(
                            "{}/teams/canva/canva{}.json".format(
                                data_dir, canva_number
                            ),
                            "r",
                        )
                    )
                finally:
                    canva_array_mutex[canva_number].release()
                lines_nb = 50  # todo fichier de conf
                line_list = []
                realTable = []
                for i, pix in enumerate(canva):
                    if i % lines_nb == 0:
                        if line_list:
                            realTable.append(line_list)
                        line_list = []
                    if not palette.get(pix.get("color")):
                        logger.error("color not found:", pix.get("color"))
                    line_list.append(palette.get(pix.get("color")))
                realTable.append(line_list)
                ppm = open(f"{data_dir}/teams/canva/tmp.ppm", "w")
                sizePixel = 5
                ppm.write(
                    "P3\n{} {}\n255\n".format(
                        sizePixel * len(realTable[0]), sizePixel * len(realTable)
                    )
                )
                for i in range(sizePixel * len(realTable)):
                    for j in range(sizePixel * len(realTable)):
                        if (
                            type(realTable[int(i / sizePixel)][int(j / sizePixel)])
                            != str
                        ):
                            print(
                                realTable[int(i / sizePixel)][int(j / sizePixel)], i, j
                            )
                        ppm.write(realTable[int(i / sizePixel)][int(j / sizePixel)])
                        ppm.write("\n")
                ppm.close()
                os.system(
                    "convert {}/teams/canva/tmp.ppm {}/teams/canva/canvaout{}.png".format(
                        data_dir, data_dir, naming[canva_number]
                    )
                )
            if not no_modif:
                os.system(
                    f"montage -mode concatenate -tile 4x4 {data_dir}/teams/canva/canvaout* {data_dir}/teams/canva/tmp.png"
                )  # todo: make it scalable!
                shutil.copyfile(
                    f"{data_dir}/teams/canva/tmp.png",
                    f"{data_dir}/teams/canva/canva.png",
                )
                live_update_mutex.acquire()
                try:
                    with open(f"{data_dir}/teams/canva/live_update.json", "w") as file:
                        file.write("[]")
                finally:
                    live_update_mutex.release()
            time.sleep(5)
            shutil.copyfile(
                f"{data_dir}/teams/canva/canva.png",
                f"{data_dir}/teams/canva/canva2.png",
            )
        except Exception as e:
            logger.error("Issue in canva.py {}".format(e))
