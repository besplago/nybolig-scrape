"""Folder tools"""


import os
import json


WANTED_DATA: list = [
    "url",
    "address",
    "postal_code",
    "type",
    "price",
    "size",
    "basement_size",
    "rooms",
    "year_built",
    "year_rebuilt",
    "energy_label",
    "postal_avg_sqm_price"
]


def remove_empty_folders(path):
    """Removes all empty folders in a folder"""
    for root, dirs, _ in os.walk(path, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                print(f"Removed folder: {dir_path}")

def rename_folders(path):
    """Renames folders with spaces and replaces them with underscores"""
    for root, dirs, _ in os.walk(path, topdown=False):
        for name in dirs:
            dir_path = os.path.join(root, name)
            if " " in name:
                new_name = name.replace(" ", "_")
                new_path = os.path.join(root, new_name)
                os.rename(dir_path, new_path)
                print(f"Renamed folder: {dir_path} to {new_path}")

def remove_unwanted_data() -> None:
    """Removes any data from the data.jsons that is not needed."""
    for root, _, files in os.walk("output", topdown=False):
        for file in files:
            if file != "data.json":
                continue
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            for key in list(data):
                if key not in WANTED_DATA:
                    data.pop(key)
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
                print(f"Removed unwanted data from {file_path}")

if __name__ == "__main__":
    remove_unwanted_data()
