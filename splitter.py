"""This module is used to split the data into n parts."""

import os
import random

MAIN_OUTPUT_FOLDER = "./output"


def split_data(n: int, split: list = None) -> None:
    """
    Randomly split the data into n parts.

    Args:
        n (int): The number of parts to split the data into.
        split (list): A list of floats that sum to 1. The length of the list must be equal to n.
    """
    folders = os.listdir(MAIN_OUTPUT_FOLDER)

    # Check if the MAIN_OUTPUT_FOLDER contains part_ folders
    part_folders = [folder for folder in folders if "part_" in folder]
    if part_folders:
        for folder in part_folders:
            part_folder = f"{MAIN_OUTPUT_FOLDER}/{folder}"
            for sub_folder in os.listdir(part_folder):
                os.rename(f"{part_folder}/{sub_folder}", f"{MAIN_OUTPUT_FOLDER}/{sub_folder}")
            os.rmdir(part_folder)
        folders = os.listdir(MAIN_OUTPUT_FOLDER)

    n_folders = len(folders)
    print(f"Found {n_folders} folders in the output folder.")

    # Calculate the number of folders in each part based on the split list
    if split:
        if len(split) != n:
            raise ValueError("The length of the split list must be equal to n.")
        if sum(split) != 1:
            raise ValueError("The sum of the split list must be equal to 1.")
        n_folders_in_part = [int(n_folders * part) for part in split]
    else:
        # If split is not provided, divide the folders equally
        n_folders_in_part = [n_folders // n] * n
        n_folders_in_part[-1] += n_folders % n

    print(f"Splitting the data into {n} parts with the following distribution: {n_folders_in_part}")

    # Create the part folders
    for i, n_folders in enumerate(n_folders_in_part):
        part_folder = f"{MAIN_OUTPUT_FOLDER}/part_{i + 1}"
        os.mkdir(part_folder)
        print(f"Created folder: {part_folder}")

        # Move the folders to the part folder
        for _ in range(n_folders):
            folder = random.choice(folders)
            os.rename(f"{MAIN_OUTPUT_FOLDER}/{folder}", f"{part_folder}/{folder}")
            folders.remove(folder)

    # Move the remaining folders to the last part
    for folder in folders:
        os.rename(f"{MAIN_OUTPUT_FOLDER}/{folder}", f"{part_folder}/{folder}")

    print("Data split complete.")

if __name__ == "__main__":
    split_data(2, [0.5, 0.5])
