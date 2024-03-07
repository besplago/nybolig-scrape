"""A script for scraping housing data from nybolig.dk"""

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By


# Debugging
error_count: dict = {}


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
POSTAL_CODE_FILTERS: dict = config["postal_code_filters"]

SESSION: requests.Session = requests.Session()
HEADERS: dict = {"User-Agent": USER_AGENT}


def _get_soup(url: str) -> BeautifulSoup:
    response = SESSION.get(url, headers=HEADERS)
    response.raise_for_status()  # Check if the request was successful
    return BeautifulSoup(response.text, HTML_PARSER)


def _get_max_pages() -> int:
    soup = _get_soup(r"https://www.nybolig.dk/til-salg")
    pagination = soup.find("div", class_="results-pagination")
    if not pagination:
        return 1
    last_page = pagination.find_all("span")[-1].text
    return int(last_page)


MAX_PAGES: int = _get_max_pages()


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
    source: requests.Response = SESSION.get(bolig_url, headers=HEADERS).text
    soup = BeautifulSoup(source, HTML_PARSER)
    bolig_data: dict = {}
    image_urls: list = []

    # Extract the data from the bolig
    bolig_data["url"] = bolig_url
    bolig_data["address"] = _extract_address(soup, bolig_site)
    bolig_data["postal_code"] = _extract_postal_code(bolig_url, bolig_site)
    bolig_data["type"] = bolig_type
    bolig_data["price"] = _extract_price(soup, bolig_site)
    bolig_data.update(_extract_bolig_facts_box(soup, bolig_site, bolig_url))

    # Extract floor plan from the bolig
    image_urls.append(_extract_floorplan(soup, bolig_site))

    # Extract the images from the bolig
    if INCLUDE_IMAGES:
        image_urls.append(_extract_images(soup, bolig_site))

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

    in_range: bool = False
    in_individual: bool = False
    for postal_range in POSTAL_CODE_FILTERS["ranges"]:
        if postal_range[0] <= postal_code <= postal_range[1]:
            in_range = True
    if postal_code in POSTAL_CODE_FILTERS["individual"]:
        in_individual = True
    if not (in_range or in_individual):
        return

    a_tag = bolig.find("a", class_="tile__image-container")
    bolig_url = URL + a_tag["href"]

    # Check if redirecting to another page
    bolig_url, bolig_site = _check_redirect(bolig_url)
    if bolig_site == "unsupported":
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
        except Exception as e:
            print(f"Error extracting data from {bolig_url}: {e}")
            # Count the times the same error has occured, if it does not exist, create it
            if e not in error_count:
                error_count[e] = 1
            else:
                error_count[e] += 1
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

        for page in range(1, total_pages + 1):
            # for page in range(600, 650):
            print(f"Scraping page {page} of {total_pages}")
            sale_url: str = f"{URL}/til-salg?page={page}"
            soup: BeautifulSoup = _get_soup(sale_url)
            for bolig in soup.find_all("li", class_=LISTING_CLASS):
                futures.append(executor.submit(_process_bolig, bolig))

        # Wait for all threads to finish
        for future in futures:
            future.result()

    print(f"Finished scraping {total_pages} pages")
    print(error_count)  # NOTE: For debugging purposes


def _check_redirect(bolig_url: str) -> tuple:
    supported_sites = [  # Number of listings (02/03/2024)
        "danbolig",  # 918
        # "home",             # 1140 # NOTE: facts does not show up without JS, so hard to extract
        "lokalbolig",  # 372
        # "eltoftnielsen",    # 72
        # "realmaeglerne",    # 325
        # "boligsiden",       # 4
        "estate",  # 346
        # "edc",              # 928 # NOTE: protected by WAF
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


def _extract_floorplan(soup: BeautifulSoup, bolig_site: str) -> str:
    # TODO: Problem when there are multiple floor plans,
    # example: https://www.nybolig.dk/villa
    if bolig_site == "nybolig":
        floor_plan_container = soup.find("div", class_="floorplan__drawing-container")
        if floor_plan_container:
            floor_plan_url = floor_plan_container.find(
                "img", class_="floorplan__drawing lazy"
            ).get("data-src", "")
            return floor_plan_url
    elif bolig_site == "danbolig":
        floor_plan_container = soup.find("o-property-floorplan")
        floor_plan_container = soup.find("o-property-floorplan")
        if floor_plan_container:
            floorplan2d = floor_plan_container.get(":floorplan2d", "")
            floor_plan_url = floorplan2d.split('"url": "')[1].split('",')[0]
            return floor_plan_url
    elif bolig_site == "estate":
        floor_plan_url = soup.find("img", class_="floorplan__drawing lazy").get(
            "data-src", ""
        )
    elif bolig_site == "lokalbolig":
        floor_plan_url = soup.find("img", class_="object-contain").get("src", "")
    raise ValueError("No floor plan found.")


def _extract_images(soup: BeautifulSoup, bolig_site: str) -> list:
    if bolig_site == "nybolig":
        image_urls: list = []
        for image_container in soup.find_all(
            "div", class_="slider-image__image-container"
        ):
            img_tag = image_container.find("img", class_="slider-image__image")
            if img_tag:
                image_url = img_tag.get("data-src", "")
                image_urls.append(image_url)
    return image_urls


def _extract_bolig_facts_box(
    soup: BeautifulSoup, bolig_site: str, bolig_url: str
) -> dict:
    bolig_data: dict = {
        "size": None,
        "basement_size": None,
        "rooms": None,
        "year_built": None,
        "year_rebuilt": None,
        "energy_label": None,
    }

    if bolig_site == "nybolig":
        for fact in soup.find_all("div", class_="case-facts__box-inner-wrap"):
            if "Boligareal" in fact.text:
                bolig_data["size"] = int(fact.find("strong").text.split(" ")[0])
            elif "Kælderstørrelse" in fact.text:
                bolig_data["basement_size"] = int(
                    fact.find("strong").text.split(" ")[0]
                )
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
                bolig_data["energy_label"] = (
                    fact.contents[3].get("class")[1].split("-")[2]
                )
    elif bolig_site == "home":
        # Press the "Se flere fakta" button to reveal all facts using selenium
        driver = webdriver.Chrome()
        driver.get(bolig_url)

        button = driver.find_element(
            By.XPATH,
            '//*[@id="__nuxt"]/div/div[3]/div[2]/div/div[2]/div[3]/div[2]/div/button',
        )
        driver.implicitly_wait(5)
        button.click()

        soup = BeautifulSoup(driver.page_source, HTML_PARSER)

        for fact in soup.find_all("div", class_="property-details-facts-tab"):
            print(fact.text)
    elif bolig_site == "danbolig":
        facts_table = soup.find(
            "div", class_="m-table o-propertyPresentationInNumbers__table"
        )
        # Extract the table rows
        rows = facts_table.find_all("tr")
        for row in rows:
            # Extract the table data
            data = row.find_all("td")
            if not data:
                continue
            if "Boligareal" in data[0].text:
                bolig_data["size"] = int(data[1].text.split(" ")[0])
            elif "Rum" in data[0].text:
                bolig_data["rooms"] = int(data[1].text)
            elif "Byggeår" in data[0].text:
                bolig_data["year_built"] = int(data[1].text)
            elif "Energimærke" in data[0].text:
                bolig_data["energy_label"] = data[1].text
    elif bolig_site == "estate":
        facts_box = soup.find("div", class_="case-facts__box")
        facts = facts_box.find_all("div", class_="case-facts__box-inner-wrap")
        for fact in facts:
            if "Boligareal" in fact.text:
                bolig_data["size"] = int(fact.find("strong").text.split(" ")[0])
            elif "Stue/Værelser" in fact.text:
                living_rooms = int(fact.find("strong").text.split("/")[0])
                rooms = int(fact.find("strong").text.split("/")[1])
                bolig_data["rooms"] = living_rooms + rooms
            elif "Bygget/Ombygget" in fact.text:
                # Sometimes only the year built is present
                built_rebuilt_raw = fact.find("strong").text.split("/")
                bolig_data["year_built"] = int(built_rebuilt_raw[0])
                if len(built_rebuilt_raw) > 1:
                    bolig_data["year_rebuilt"] = int(built_rebuilt_raw[1])
    elif bolig_site == "lokalbolig":
        # Find all divs with the class "flex justify-between [&:nth-child(even)]:bg-lighter px-5 py-2 md:px-4"
        facts = soup.find_all(
            "div",
            class_="flex justify-between [&:nth-child(even)]:bg-lighter px-5 py-2 md:px-4",
        )
        for fact in facts:
            label = fact.contents[0].text
            if "Boligareal" in label:
                area_raw = fact.contents[1].text
                # remove non-numeric characters
                area = "".join(filter(str.isdigit, area_raw))
                # remove the last character, which is a **2
                area = int(area[:-1])
                bolig_data["size"] = area
            elif "Værelser inkl. stuer" in label:
                rooms = int(fact.contents[1].text)
                bolig_data["rooms"] = rooms
            elif "Byggeår" in label:
                bolig_data["year_built"] = int(fact.contents[1].text)
            elif "Energimærke" in label:
                bolig_data["energy_label"] = fact.contents[1].text

    return bolig_data


def _extract_price(soup: BeautifulSoup, bolig_site: str) -> int:
    if bolig_site == "nybolig":
        price_raw = soup.find(
            "span", class_="case-info__property__info__text__price"
        ).text.strip()
        # remove non-numeric characters
        price = int("".join(filter(str.isdigit, price_raw)))
    elif bolig_site == "home":
        price_raw = soup.find(
            "h3", class_="property-details-information__fact"
        ).text.strip()
        # remove non-numeric characters
        price = int("".join(filter(str.isdigit, price_raw)))
    elif bolig_site == "danbolig":
        a_label = soup.find("li", class_="a-label u-none md:u-flex").text.strip()
        # remove non-numeric characters
        price = int("".join(filter(str.isdigit, a_label)))
    elif bolig_site == "estate":
        price_raw = soup.find(
            "span", class_="case-info__property__info__text__price"
        ).text.strip()
        # remove non-numeric characters
        price = int("".join(filter(str.isdigit, price_raw)))
    elif bolig_site == "lokalbolig":
        price_raw = (
            soup.find("div", class_="flex justify-between").contents[1].text.strip()
        )
        # remove non-numeric characters
        price = int("".join(filter(str.isdigit, price_raw)))

    return price


def _extract_postal_code(url: str, bolig_site: str) -> int:
    if bolig_site == "nybolig":
        # Extract the postal code from the url
        postal_code_raw: str = url.split("/")[4]
        if not postal_code_raw.isdigit():
            raise ValueError(f"Could not extract postal code from {url}")
    elif bolig_site == "home":
        # Extract the postal code from the url
        for s in url.split("-"):
            if s.isdigit() and len(s) == 4:
                postal_code_raw = s
                break
        if not postal_code_raw.isdigit():
            raise ValueError(f"Could not extract postal code from {url}")
    elif (
        bolig_site == "danbolig" or bolig_site == "estate" or bolig_site == "lokalbolig"
    ):
        # Extract the postal code from the url
        for s in url.split("/"):
            if s.isdigit() and len(s) == 4:
                postal_code_raw = s
                break
        if not postal_code_raw.isdigit():
            raise ValueError(f"Could not extract postal code from {url}")
    return int(postal_code_raw)


def _extract_address(soup: BeautifulSoup, bolig_site: str) -> str:
    # Extract the address components and join them with a space
    if bolig_site == "nybolig":
        address_components = [
            component.text.strip()
            for component in soup.find_all(
                "strong", class_="case-info__property__info__main__title__address"
            )
        ]

        # Filter out empty components
        address_components = [
            component for component in address_components if component
        ]

        # Join the non-empty components with a space
        address = " ".join(address_components)

        # Remove newline characters from the address
        address = address.replace("\n", "")

        # Remove commas from the address
        address = address.replace(",", "")
    elif bolig_site == "home":
        address = soup.find("h3", class_="h3--bold").text.strip()

        # Remove newline characters from the address
        address = address.replace("\n", "")

        # Remove commas from the address
        address = address.replace(",", "")
    elif bolig_site == "danbolig":
        address = soup.find("h1", class_="a-lead o-propertyHero__address").text.strip()

        # Remove newline characters from the address
        address = address.replace("\n", "")

        # Remove commas from the address
        address = address.replace(",", "")

        # Remove spaces that are more than one
        address = " ".join(address.split())
    elif bolig_site == "edc":
        address1 = soup.find("h1", class_=" font-bold md:style-h3").text.strip()
        address2 = soup.find("span", class_="block md:text-primary-dusty").text.strip()
    elif bolig_site == "estate":
        address = soup.find(
            "h1", class_="case-info__property__info__main__title"
        ).text.strip()

        # Remove newline characters from the address
        address = address.replace("\n", "")

        # Remove commas from the address
        address = address.replace(",", "")

        # Remove spaces that are more than one
        address = " ".join(address.split())
    elif bolig_site == "lokalbolig":
        div = soup.find("div", class_="flex flex-col gap-3").contents[1]
        address1 = div.contents[0].contents[0].text.strip()
        address2 = div.contents[1].text.strip()
        address = f"{address1} {address2}"

        # Remove newline characters from the address
        address = address.replace("\n", "")

        # Remove commas from the address
        address = address.replace(",", "")

        # Remove spaces that are more than one
        address = " ".join(address.split())

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
    if pages > MAX_PAGES or pages < 1:
        print(f"Max pages is {MAX_PAGES}, continuing with {MAX_PAGES} pages")
        pages = MAX_PAGES
    return pages
