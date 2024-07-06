import json
import os
import pandas
from jo_serv.tools.excel_mgmt import (
    concatenate_players,
    create_empty_dict, 
    generate_pools,
    generate_series,
    generate_table,
    generate_teams,
    get_athletes,
    get_file_name,
    get_sport_config, 
    store_infos,
    )
from jo_serv.tools.match_mgmt import team_to_next_step

def parse_excel(data_dir: str):
    path = os.path.join(f"{data_dir}/JO_2024.xlsx")
    excel_sheet = pandas.read_excel(path, sheet_name=None, engine="openpyxl")
    export_path = os.path.join(f"{data_dir}/JO_2024_export.xlsx")
    athletes = create_empty_dict(excel_sheet)

    useful_data = ("Nom Prénom",
                "Sexe")
    sports_name = ("10 km de Meyssiez",
            "Volley",
            "Concours de pizza",
            "Waterpolo",
            "Spikeball",
            "Course d'orientation",
            "Beer pong",
            "Lancer de tong",
            "Blindtest",
            "Babyfoot",
            "Flechette",
            "Slackline",
            "Polish Horseshoes",
            "Ventriglisse",
            "100m Ricard",
            "Blitz",
            "Petanque",
            )

    sports = dict()
    for sport_name in sports_name:
        sports[sport_name] = dict()
    for sheet in excel_sheet:
        for column_name in excel_sheet[sheet]:
            if column_name in useful_data:
                athletes = store_infos(excel_sheet[sheet][column_name], athletes, column_name)
            if column_name in sports_name:
                file_name = get_file_name(column_name, data_dir)
                sport_config = get_sport_config(file_name, data_dir)
                sport_votes = excel_sheet[sheet][column_name]
                sports[column_name]["athletes"] = get_athletes(sport_votes, athletes)
                print(f"Generating teams for {column_name}.")
                sports[column_name]["teams"] = generate_teams(sport_config, get_athletes(sport_votes, athletes))
        break
    writer = pandas.ExcelWriter(export_path, engine="openpyxl")
    for sport in sports_name:
        print(f"Exporting {sport}")
        try:
            data = pandas.DataFrame(sports[sport]['teams'])
        except KeyError:
            print(sports[sport])
        data.to_excel(writer, sheet_name=sport)
    writer.close()

    athletes_list = []
    for index in athletes:
        athlete = athletes[index]
        athletes_list.append(dict(Player=athlete["Nom Prénom"], in_killer=True))
    with open(f"{data_dir}/athletes/All.json", "w") as file:
        json.dump(athletes_list, file, ensure_ascii=False)


def parse_exported_excel(data_dir: str):
    path = os.path.join(f"{data_dir}/JO_2024_export.xlsx")

    sports_name = ("10 km de Meyssiez",
            "Volley",
            "Concours de pizza",
            "Waterpolo",
            "Spikeball",
            "Course d'orientation",
            "Beer pong",
            "Lancer de tong",
            "Blindtest",
            "Babyfoot",
            "Flechette",
            "Slackline",
            "Polish Horseshoes",
            "Ventriglisse",
            "100m Ricard",
            "Blitz",
            "Petanque",
            )

    for sport_name in sports_name:
        excel_sheet = pandas.read_excel(path, sheet_name=sport_name, engine="openpyxl")
        teams_list = dict()
        teams_list["Teams"] = []
        unique_id = 1
        for column_name in excel_sheet: 
            if "team" in column_name:
                team_dict = dict()
                team_dict["stillingame"] = "True" 
                team_dict["uniqueid"] = unique_id
                team_dict["Players"] = concatenate_players(excel_sheet, column_name)
                teams_list["Teams"].append(team_dict)
                unique_id += 1
            file_name = get_file_name(sport_name, data_dir)
        with open(f"{data_dir}/teams/{file_name}", "w") as file:
            json.dump(teams_list, file, ensure_ascii=False)
        file_name = get_file_name(sport_name, data_dir)
        sport_config = get_sport_config(file_name, data_dir)
        if sport_config["Type"] == "Table":
            states = ["playoff", "paris", "results"]
            status = "playoff"
            print(sport_name)
            teams_per_match = sport_config["Teams per match"]
            table = generate_table(teams_list["Teams"], teams_per_match)
            file_name = file_name[:-5] + "_playoff.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(table, file, ensure_ascii=False)
            matches = table["matches"]
            for match in matches:
                if match["over"]:
                    sport = file_name.replace("_playoff.json", "")
                    team_to_next_step(sport, match["uniqueId"], data_dir)
        elif sport_config["Type"] == "Pool":
            states = ["poules","playoff", "paris", "results"]
            status = "poules"
            print(sport_name)
            pools = generate_pools(teams_list["Teams"])
            file_name = file_name[:-5] + "_poules.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(pools, file, ensure_ascii=False)
        elif sport_config["Type"] == "Series":
            status = "final"
            states = ["final", "paris", "results"]
            series = generate_series(teams_list["Teams"], sport_config)
            file_name = file_name[:-5] + "_series.json"
            with open(f"{data_dir}/teams/{file_name}", "w") as file:
                json.dump(series, file, ensure_ascii=False)
        
        file_name = get_file_name(sport_name, data_dir)
        file_name = file_name[:-5] + "_status.json"
        status_info = dict(status=status, states=states, arbitre=[""], rules=sport_config["rules"], sportname=file_name.replace("_status.json", ""))
        with open(f"{data_dir}/teams/{file_name}", "w") as file:
            json.dump(status_info, file, ensure_ascii=False)

