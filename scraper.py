"""A script for scraping housing data from nybolig.dk"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from bs4 import BeautifulSoup

# Load configuration from file
config_file_path: Path = Path(__file__).parent.joinpath("config.json")
if not config_file_path.is_file():
    raise FileNotFoundError("Configuration file not found.")

with open(config_file_path, "r", encoding="utf-8") as config_file:
    config: dict = json.load(config_file)

URL: str = config["url"]
PAGES: int = config["pages"]
INCLUDE_IMAGES: bool = config["include_images"]
OVERRIDE_PREVIOUS_DATA: bool = config["override_previous_data"]
OUTPUT_PATH: str = config["output_path"]
USER_AGENT: str = config["user_agent"]
HTML_PARSER: str = config["html_parser"]
LISTING_CLASS: str = config["listing_class"]
BOLIG_TYPES: dict = config["bolig_types"]
MAX_PAGES: int = config["max_pages"]
POSTAL_CODE_FILTERS: dict = config["postal_code_filters"]

SESSION: requests.Session = requests.Session()
HEADERS: dict = {"User-Agent": USER_AGENT}


def _validate_config():
    for postal_range in POSTAL_CODE_FILTERS["ranges"]:
        if len(postal_range) != 2:
            raise ValueError(
                "Postal code filter ranges must have exactly two numbers.", postal_range
            )
        if postal_range[0] > postal_range[1]:
            raise ValueError(
                "Invalid postal code range: start value is greater than end value.",
                postal_range,
            )


def _extract_bolig_data(bolig_url: str, bolig_type: str, bolig_site: str) -> tuple:
    # TODO: For each extraction function, there should be an appropriate handling depending on the
    # given bolig_site string
    source: requests.Response = SESSION.get(bolig_url, headers=HEADERS).text
    soup = BeautifulSoup(source, HTML_PARSER)
    bolig_data: dict = {}
    image_urls: list = []

    # Extract the data from the bolig
    bolig_data["url"] = bolig_url
    bolig_data["address"] = _extract_address(soup, bolig_site)
    bolig_data["postal_code"] = _extract_postal_code(bolig_url)
    bolig_data["type"] = bolig_type
    bolig_data["price"] = _extract_price(soup)
    bolig_data.update(_extract_bolig_facts_box(soup))

    # Extract floor plan from the bolig
    image_urls.append(_extract_floorplan(soup))

    # Extract the images from the bolig
    if INCLUDE_IMAGES:
        image_urls.append(_extract_images(soup))

    return bolig_data, image_urls


def _create_bolig_folder(bolig_folder: Path) -> None:
    if OVERRIDE_PREVIOUS_DATA or not bolig_folder.exists():
        bolig_folder.mkdir(parents=True, exist_ok=True)
    else:
        print(f"Skipping existing folder: {bolig_folder}")


def _save_data_and_images(bolig_folder: Path, bolig_data: dict, images: list) -> None:
    with open(bolig_folder / "data.json", "w", encoding="utf-8") as f:
        json.dump(bolig_data, f, indent=4)

    for i, image_url in enumerate(images):
        image_data = SESSION.get(image_url).content
        with open(bolig_folder / f"{i}.jpg", "wb") as f:
            f.write(image_data)


def _process_bolig(bolig: BeautifulSoup) -> None:
    div_tile = bolig.find("div", class_="tile")
    if not div_tile:
        return

    # Check if appropriate bolig type
    bolig_type = _extract_bolig_type(bolig)
    if bolig_type not in BOLIG_TYPES:
        return
    if BOLIG_TYPES[bolig_type] is False:
        return

    # Check if appropriate postal code
    try:
        postal_code: int = _extract_postal_code_page_wise(bolig)
    except ValueError as ve:
        print(ve)
        return

    a_tag = bolig.find("a", class_="tile__image-container")
    bolig_url = URL + a_tag["href"]

    # Check if redirecting to another page
    bolig_url, bolig_site = _check_redirect(bolig_url)
    if bolig_site == "unsupported":
        return

    in_range: bool = False
    in_individual: bool = False
    for postal_range in POSTAL_CODE_FILTERS["ranges"]:
        if postal_range[0] <= postal_code <= postal_range[1]:
            in_range = True
    if postal_code in POSTAL_CODE_FILTERS["individual"]:
        in_individual = True
    if not (in_range or in_individual):
        return

    address_paragraph_raw = div_tile.find("p", class_="tile__address")
    address_paragraph: str = address_paragraph_raw.text.replace(",", "")

    bolig_folder = Path(OUTPUT_PATH).joinpath(address_paragraph)
    _create_bolig_folder(bolig_folder)

    if OVERRIDE_PREVIOUS_DATA or not (bolig_folder / "data.json").exists():
        try:
            bolig_data, images = _extract_bolig_data(bolig_url, bolig_type, bolig_site)
            _save_data_and_images(bolig_folder, bolig_data, images)
            print(f"{address_paragraph} extracted")
        except requests.exceptions.RequestException as e:
            print(f"Error extracting data from {bolig_url}: {e}")
    else:
        print(f"Skipping existing data in folder: {bolig_folder}")


def scrape() -> None:
    """Start scraping housing data from nybolig.dk"""
    try:
        _validate_config()
    except ValueError as ve:
        raise ve

    total_pages: int = _get_pages(PAGES)

    with ThreadPoolExecutor() as executor:
        futures: list = []

        for page in range(400, total_pages + 1):
            print(f"Scraping page {page} of {total_pages}")
            sale_url: str = f"{URL}/til-salg?page={page}"
            soup: BeautifulSoup = _get_soup(sale_url)
            for bolig in soup.find_all("li", class_=LISTING_CLASS):
                futures.append(executor.submit(_process_bolig, bolig))

        # Wait for all threads to finish
        for future in futures:
            future.result()

    print(f"Finished scraping {total_pages} pages")


def _check_redirect(bolig_url: str) -> tuple:
    supported_sites = [     # Number of listings (02/03/2024)
        # "danbolig",         # 918
        "home",             # 1140
        # "lokalbolig",       # 372
        # "eltoftnielsen",    # 72
        # "realmaeglerne",    # 325
        # "boligsiden",       # 4
        # "estate",           # 346
        # "edc",              # 928
        # "carlsbergbyen",    # 165
        # "andliving",        # 63
        # "fantasticfrank",   # 12
        # "ronniekarlsson",   # 4
        # "brikk",            # 127
        # "bobasic",          # 6
        # "thpr",             # 10
        # "minbolighandel",   # 16
        # "dmbolig",          # 12
        # "johnfrandsen",     # 102
        # "emk",              # 25
    ]
    bolig_site: str = "nybolig"
    if "viderestillingekstern" in bolig_url or "estate.dk" in bolig_url:
        bolig_site = "unsupported"
        # Remove the 'https://www.nybolig.dkhttps//' part of the url
        bolig_url = bolig_url.replace("https://www.nybolig.dk", "")
        # Follow the redirect
        new_session = requests.Session()
        bolig_url_redirect = new_session.get(bolig_url, headers=HEADERS).url
        supported_site_found: bool = False
        for supported_site in supported_sites:
            if supported_site in bolig_url_redirect:
                bolig_site = supported_site
                supported_site_found = True
                break
        if not supported_site_found:
            print(f"Unsupported site: {bolig_url_redirect}")
        bolig_url = bolig_url_redirect
    return bolig_url, bolig_site


def _get_soup(url: str) -> BeautifulSoup:
    response = SESSION.get(url, headers=HEADERS)
    response.raise_for_status()  # Check if the request was successful
    return BeautifulSoup(response.text, HTML_PARSER)


def _extract_floorplan(soup: BeautifulSoup) -> str:
    # TODO: Problem when there are multiple floor plans,
    # example: https://www.nybolig.dk/villa
    floor_plan_container = soup.find("div", class_="floorplan__drawing-container")
    if floor_plan_container:
        floor_plan_url = floor_plan_container.find(
            "img", class_="floorplan__drawing lazy"
        ).get("data-src", "")
        return floor_plan_url
    return ""


def _extract_images(soup: BeautifulSoup) -> str:
    image_urls: list = []
    for image_container in soup.find_all(
        "div", class_="slider-image__image-container"
    ):
        img_tag = image_container.find("img", class_="slider-image__image")
        if img_tag:
            image_url = img_tag.get("data-src", "")
            image_urls.append(image_url)
    return image_urls


def _extract_bolig_facts_box(soup: BeautifulSoup) -> dict:
    bolig_data: dict = {
        "size": None,
        "basement_size": None,
        "rooms": None,
        "year_built": None,
        "year_rebuilt": None,
        "energy_label": None,
    }

    for fact in soup.find_all("div", class_="case-facts__box-inner-wrap"):
        if "Boligareal" in fact.text:
            bolig_data["size"] = int(fact.find("strong").text.split(" ")[0])
        elif "Kælderstørrelse" in fact.text:
            bolig_data["basement_size"] = int(fact.find("strong").text.split(" ")[0])
        elif "Stue/Værelser" in fact.text:
            living_rooms = int(fact.find("strong").text.split("/")[0])
            rooms = int(fact.find("strong").text.split("/")[1])
            bolig_data["rooms"] = living_rooms + rooms
        elif "Bygget/Ombygget" in fact.text:
            built_rebuilt_raw = fact.find("strong").text.split("/")
            bolig_data["year_built"] = int(built_rebuilt_raw[0])
            if len(built_rebuilt_raw) > 1:
                bolig_data["year_rebuilt"] = int(built_rebuilt_raw[1])
        elif "Energimærke" in fact.text:
            bolig_data["energy_label"] = fact.contents[3].get("class")[1].split("-")[2]

    return bolig_data


def _extract_price(soup: BeautifulSoup) -> int:
    price_raw = soup.find(
        "span", class_="case-info__property__info__text__price"
    ).text.strip()
    # remove non-numeric characters
    price = int("".join(filter(str.isdigit, price_raw)))
    return price


def _extract_postal_code(url: str) -> int:
    # Extract the postal code from the url
    postal_code_raw: str = url.split("/")[4]
    if not postal_code_raw.isdigit():
        raise ValueError(f"Could not extract postal code from {url}")
    return int(postal_code_raw)


def _extract_address(soup: BeautifulSoup, bolig_site: str) -> str:
    # TODO: Move exractors into own module probably
    # Extract the address components and join them with a space
    if bolig_site == "nybolig":
        address_components = [
            component.text.strip()
            for component in soup.find_all(
                "strong", class_="case-info__property__info__main__title__address"
            )
        ]

        # Filter out empty components
        address_components = [component for component in address_components if component]

        # Join the non-empty components with a space
        address = " ".join(address_components)

        # Remove newline characters from the address
        address = address.replace("\n", "")

        # Remove commas from the address
        address = address.replace(",", "")
    elif bolig_site == "home":
        raise NotImplementedError("Extracting address from home.dk is not implemented")

    return address


def _extract_postal_code_page_wise(bolig: BeautifulSoup) -> int:
    # Extract the postal code from the url
    # Example: Tranevænget 2, 5610 Assens -> 5610, find the first number with 4 digits
    address: str = bolig.find("p", class_="tile__address").text.strip()
    postal_code_raw: str = [
        int(s) for s in address.split() if s.isdigit() and len(s) == 4
    ][0]
    postal_code: int = int(postal_code_raw)
    return postal_code


def _extract_bolig_type(bolig: BeautifulSoup) -> str:
    bolig_type_raw = bolig.find("p", class_="tile__mix").text.strip().lower()
    bolig_type = bolig_type_raw.split(" ")[0]
    return bolig_type


def _get_pages(pages: int) -> int:
    if pages > MAX_PAGES:
        print(f"Max pages is {MAX_PAGES}, continuing with {MAX_PAGES} pages")
        pages = MAX_PAGES
    return pages
