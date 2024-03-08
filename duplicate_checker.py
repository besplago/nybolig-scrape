"""Script that checks for duplicate addresses in the output folder"""

import os

OUTPUT_FOLDER = "./output"


def check_duplicates():
    """Check for duplicate addresses in the output folder."""
    # The output folder contains other folders. Each of these folders are named by an address.
    # We should check that there are no duplicate addresses in the output folder.

    # Get the list of folders in the output folder
    folders = os.listdir(OUTPUT_FOLDER)

    # Save the duplicate addresses in a list
    duplicate_addresses = []
    duplicate_found = False

    # Iterate through the list of folders
    for folder in folders:
        # If the folder is a directory
        if os.path.isdir(f"{OUTPUT_FOLDER}/{folder}"):
            # Check if the folder name is already in the list of duplicate addresses
            if folder in duplicate_addresses:
                duplicate_found = True
                print(f"Duplicate address: {folder}")
            else:
                # If not, add it to the list
                duplicate_addresses.append(folder)

    # If there are no duplicate addresses, print a message
    if not duplicate_found:
        print("No duplicate addresses found.")

if __name__ == "__main__":
    check_duplicates()
