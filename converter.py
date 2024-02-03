"""Converts the jsons from the output folder to a single csv file"""
import json
from pathlib import Path

def convert() -> None:
    """Converts the jsons from the output folder to a single csv file"""
    # Load the json files from the output folder. It is structured as: output/address/1.json
    jsons = []
    for json_file in Path("output").rglob("*.json"):
        with open(json_file, "r", encoding="utf-8") as file:
            jsons.append(json.load(file))

    print(f"Found {len(jsons)} json files.")

    # Convert the jsons to a csv, based on the jsons keys
    csv = []
    csv.append(",".join(jsons[0].keys()))
    for json_data in jsons:
        csv.append(",".join(str(value) for value in json_data.values()))

    # Write the csv to a file
    with open("bolig_data.csv", "w", encoding="utf-8") as csv_file:
        csv_file.write("\n".join(csv))

    print("Conversion complete.")
