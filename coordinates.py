"""This module is used to get the coordinates of an address using the geoapi.dk API."""

import requests

MANUAL_COORDINATES_FIRST: dict = {
    "Johan Wilmanns Vej 29 st. th 2800 Kongens Lyngby": (55.764868665793344, 12.50519455796523),
}
MANUAL_COORDINATES_SECOND: dict = {
    "Ørestads Boulevard 1": (55.66752263915916, 12.587827732846602),
    "Valhøjs Alle 1": (55.67367611300166, 12.462472177004795),
    "Islands Brygge 1": (55.66917199942024, 12.58031235967339),
    "Richard Mortensens Vej 1": (55.623590614685405, 12.572957027213938),
    "Robert Jacobsens Vej 1": (55.623729501007716, 12.57536419568169),
    "Gyngmose Parkvej 1": (55.72730576264755, 12.474742999162634),
    "Maglekæret 1": (55.522554339623746, 12.208119701551434),
    "Gyngemose Parkvej 1": (55.72736617930284, 12.474785918617677),
    "Blåfuglestræde 1": (55.64425581034795, 12.210666643437085),
    "Rundholtsvej 1": (55.65343921247853, 12.565782944232227),
    "Troldmands Allé 1": (55.54545404431426, 12.234007961672802),
}


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
            # number. Also add the number 1 to the address to avoid getting the coordinates of
            # the city center.
            address_parts: list = address.split(" ")
            for i, part in enumerate(address_parts):
                if any(char.isdigit() for char in part):
                    address_parts = address_parts[:i]
                    break
            print(f"Could not get coordinates for {address}")
            address = " ".join(address_parts)
            address += " 1"
            print("Checking the manual coordinates")
            if address in MANUAL_COORDINATES_SECOND:
                return MANUAL_COORDINATES_SECOND[address]
            print(f"Trying again with {address}")
            response = requests.get(f"http://geoapi.dk/?q={address}", timeout=1000)
            response.raise_for_status()
            data = response.json()
            try:
                return data["lat"], data["lng"]
            except KeyError:
                print(f"Could not get coordinates for {address}")
                return (0, 0)
        return data["lat"], data["lng"]
    except requests.exceptions.RequestException as e:
        print(f"Could not get coordinates for {address}: {e}")
        return (0, 0)


if __name__ == "__main__":
    test_address: str = "Nytorv 10"
    coordinates: tuple = get_coordinates(test_address)
    print(f"Coordinates for {test_address}: {coordinates}")
