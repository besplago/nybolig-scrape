"""This module is used to get the coordinates of an address."""

import requests


def get_coordinates(address: str) -> tuple:
    """Gets the coordinates of an address"""
    try:
        response: requests.Response = requests.get(
            f"http://geoapi.dk/?q={address}", timeout=200
        )
        response.raise_for_status()
        data: dict = response.json()
        # If "lat" or "lng" is not in json, try again by only including the street name
        if "lat" not in data or "lng" not in data:
            # Try again by only including the street name
            # Split the address by spaces, and remove all elements after and including the first
            # number
            address_parts: list = address.split(" ")
            for i, part in enumerate(address_parts):
                if any(char.isdigit() for char in part):
                    address_parts = address_parts[:i]
                    break
            print(f"Could not get coordinates for {address}")
            address = " ".join(address_parts)
            print(f"Trying again with {address}")
            response = requests.get(f"http://geoapi.dk/?q={address}", timeout=200)
            response.raise_for_status()
            data = response.json()
            try:
                return data["lat"], data["lng"]
            except KeyError:
                print(f"Could not get coordinates for {address}")
                return (0, 0)
    except requests.exceptions.RequestException as e:
        print(f"Could not get coordinates for {address}: {e}")
        return (0, 0)


if __name__ == "__main__":
    test_address: str = "Nytorv 10"
    coordinates: tuple = get_coordinates(test_address)
    print(f"Coordinates for {test_address}: {coordinates}")
