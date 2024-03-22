"""Adds new features to the preexisting bolig data."""
import os
import threading
import json
import pandas as pd

OUTPUT_FOLDER_PATH: str = r"./output/part_1"


def _load_postal_avg_sqm_price() -> dict:
    """
    Note:
        Data from: https://rkr.statistikbank.dk/statbank5a/SelectVarVal/Define.asp?MainTable=BM011
        Settings:
            Postnumre: Marker alle
            Ejendomskategori: Ejerlejlighed
            Priser på realiserede handler: Realiseret handlspris
            Kvartal: 2023K1, 2023K2, 2023K3, 2023K4
    """
    df = pd.read_csv(
        "./postal_avg_sqm_price.csv",
        delimiter=";",
        encoding="utf-8",
        index_col=2,
        header=0,
    )
    # Remove the first two columns
    df = df.drop(df.columns[[0, 1]], axis=1)
    # Make all values integers, if they cannot be converted, they will be 0
    df = df.apply(pd.to_numeric, errors="coerce")
    # Iterate each row and calculate the average price per square meter. If a column contains a 0,
    # it will be ignored in the calculation.
    for index, row in df.iterrows():
        avg_price = 0
        count = 0
        for value in row:
            if value != 0:
                avg_price += value
                count += 1
        if count != 0:
            df.at[index, "postal_avg_sqm_price"] = avg_price / count
        else:
            df.at[index, "postal_avg_sqm_price"] = 0

    # Remove the columns that are not needed
    df = df.drop(df.columns[[0, 1, 2, 3]], axis=1)

    # Turn into a dictionary
    postal_avg_sqm_price = df.to_dict()
    # The dict is nested, remove the nesting
    postal_avg_sqm_price = postal_avg_sqm_price["postal_avg_sqm_price"]
    # Fill all NaN values with 0
    postal_avg_sqm_price = {
        key: 0.0 if pd.isna(value) else value
        for key, value in postal_avg_sqm_price.items()
    }

    # Update the keys to be integers. They can be of to formats: "1000-1499 Kbh.K." or
    # "2000 Frederiksberg". The first format will be converted to such that each postal code in the
    # range will be a separate row in the dataframe. The second format will be converted to an
    # integer.
    for key in list(postal_avg_sqm_price):
        if "-" in key:
            start, end = key.split("-")
            # remove non-numeric characters
            start = int("".join(filter(str.isdigit, start)))
            if not any(char.isdigit() for char in end):
                postal_code = int("".join(filter(str.isdigit, key)))
                postal_avg_sqm_price[postal_code] = postal_avg_sqm_price[key]
                postal_avg_sqm_price.pop(key)
                continue
            end = int("".join(filter(str.isdigit, end)))
            for postal_code in range(start, end + 1):
                postal_avg_sqm_price[postal_code] = postal_avg_sqm_price[key]
            postal_avg_sqm_price.pop(key)
        else:
            # remove non-numeric characters
            postal_code = int("".join(filter(str.isdigit, key)))
            postal_avg_sqm_price[postal_code] = postal_avg_sqm_price[key]
            postal_avg_sqm_price.pop(key)

    return postal_avg_sqm_price


def add_postal_avg_sqm_price(bolig_data: dict) -> dict:
    """Adds the average square meter price to the bolig data."""
    if "postal_avg_sqm_price" in bolig_data:
        return bolig_data
    postal_avg_sqm_price = _load_postal_avg_sqm_price()
    postal_code = bolig_data["postal_code"]
    bolig_data["postal_avg_sqm_price"] = postal_avg_sqm_price.get(postal_code, 0)
    print(f"Added postal_avg_sqm_price to {bolig_data['address']}")
    return bolig_data


def add_new_features(bolig_folder: str) -> None:
    """Adds any new features to preexisting bolig data."""
    folder_path = os.path.join(OUTPUT_FOLDER_PATH, bolig_folder)
    if not os.path.isdir(folder_path):
        return

    data_path = os.path.join(folder_path, "data.json")
    with open(data_path, "r", encoding="utf-8") as file:
        bolig_data = json.load(file)
    bolig_data = add_postal_avg_sqm_price(bolig_data)
    with open(data_path, "w", encoding="utf-8") as file:
        json.dump(bolig_data, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    # Get list of folders
    folders = os.listdir(OUTPUT_FOLDER_PATH)

    # Create threads for each folder
    threads = []
    for folder in folders:
        thread = threading.Thread(target=add_new_features, args=(folder,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to finish
    for thread in threads:
        thread.join()
