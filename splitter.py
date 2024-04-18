"""Split the data into train, test, and validation sets."""
import os
import random
import shutil
from tqdm import tqdm

INPUT_FOLDER = "./output_raw"
OUTPUT_FOLDER = "./output"

TRAIN_RATIO = 0.7
TEST_RATIO = 0.2
VALID_RATIO = 0.1
N = 2
SEED = 42  # Seed value for random shuffling

def clear_folder(folder_path: str) -> None:
    """Clear the contents of a folder."""
    if os.path.exists(folder_path):
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

def split_data(
    n: int, train_ratio: float, test_ratio: float, valid_ratio: float
) -> None:
    """
    Split the data into train, test, and validation sets.

    Args:
        n (int): The number of parts to split the train data into.
        train_ratio (float): The ratio of the train data.
        test_ratio (float): The ratio of the test data.
        valid_ratio (float): The ratio of the validation data.
    """
    tolerance = 1e-10

    if abs(train_ratio + test_ratio + valid_ratio - 1.0) > tolerance:
        raise ValueError(
            "The sum of train_ratio, test_ratio, and valid_ratio must be very close to 1."
        )

    # Clear output folders
    print("Clearing output folder...")
    clear_folder(OUTPUT_FOLDER)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    os.makedirs(f"{OUTPUT_FOLDER}/train", exist_ok=True)
    os.makedirs(f"{OUTPUT_FOLDER}/test", exist_ok=True)
    os.makedirs(f"{OUTPUT_FOLDER}/valid", exist_ok=True)

    folders = os.listdir(INPUT_FOLDER)

    # Calculate the number of folders for each set
    n_folders = len(folders)
    n_train = int(n_folders * train_ratio)
    n_test = int(n_folders * test_ratio)

    # Set seed for random shuffling
    random.seed(SEED)

    # Shuffle the folders
    random.shuffle(folders)

    # Copy folders to train set
    for folder in tqdm(folders[:n_train], desc="Copying train data"):
        src = f"{INPUT_FOLDER}/{folder}"
        dst = f"{OUTPUT_FOLDER}/train/{folder}"
        shutil.copytree(src, dst)

    # Copy folders to test set
    for folder in tqdm(folders[n_train:n_train + n_test], desc="Copying test data"):
        src = f"{INPUT_FOLDER}/{folder}"
        dst = f"{OUTPUT_FOLDER}/test/{folder}"
        shutil.copytree(src, dst)

    # Copy folders to validation set
    for folder in tqdm(folders[n_train + n_test:], desc="Copying validation data"):
        src = f"{INPUT_FOLDER}/{folder}"
        dst = f"{OUTPUT_FOLDER}/valid/{folder}"
        shutil.copytree(src, dst)

    print("Data split into train, test, and validation sets.")

    # Split the train set into n parts
    train_folders = os.listdir(f"{OUTPUT_FOLDER}/train")
    n_train_parts = n
    n_train_folders_in_part = [len(train_folders) // n_train_parts] * n_train_parts
    n_train_folders_in_part[-1] += len(train_folders) % n_train_parts

    for i, n_folders in enumerate(n_train_folders_in_part):
        part_folder = f"{OUTPUT_FOLDER}/train/train_{i + 1}"
        os.makedirs(part_folder, exist_ok=True)

        # Move the folders to the part folder
        for _ in tqdm(range(n_folders), desc=f"Splitting train data part {i + 1}"):
            folder = random.choice(train_folders)
            src = f"{OUTPUT_FOLDER}/train/{folder}"
            dst = f"{part_folder}/{folder}"
            shutil.move(src, dst)
            train_folders.remove(folder)

    print(f"Train data split into {n} parts.")

if __name__ == "__main__":
    split_data(N, TRAIN_RATIO, TEST_RATIO, VALID_RATIO)
