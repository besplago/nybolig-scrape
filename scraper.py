'''A script for scraping housing data from nybolig.dk'''
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

SESSION: requests.Session = requests.Session()
HEADERS: dict = {'User-Agent': USER_AGENT}

def _extract_bolig_data(bolig_url: str) -> tuple:
    source: requests.Response = SESSION.get(bolig_url, headers=HEADERS).text
    soup = BeautifulSoup(source, HTML_PARSER)
    bolig_data: dict = {}
    image_urls: list = []

    # Extract the data from the bolig
    bolig_data['url'] = bolig_url
    bolig_data['address'] = _extract_address(soup)
    bolig_data['postal_code'] = _extract_postal_code(soup)
    bolig_data['type'] = _extract_bolig_type(soup)
    bolig_data['price'] = _extract_price(soup)
    bolig_data.update(_extract_bolig_facts_box(soup))

    # Extract floor plan from the bolig
    floor_plan_container = soup.find('div', class_='floorplan__drawing-container')
    if floor_plan_container:
        floor_plan_url = floor_plan_container.find(
            'img', class_='floorplan__drawing lazy').get('data-src', ''
        )
        image_urls.append(floor_plan_url)

    # Extract the images from the bolig
    if INCLUDE_IMAGES:
        for image_container in soup.find_all('div', class_='slider-image__image-container'):
            img_tag = image_container.find('img', class_='slider-image__image')
            if img_tag:
                image_url = img_tag.get('data-src', '')
                image_urls.append(image_url)

    return bolig_data, image_urls


def _create_bolig_folder(bolig_folder: Path) -> None:
    if OVERRIDE_PREVIOUS_DATA or not bolig_folder.exists():
        bolig_folder.mkdir(parents=True, exist_ok=True)
    else:
        print(f"Skipping existing folder: {bolig_folder}")


def _save_data_and_images(bolig_folder: Path, bolig_data: dict, images: list) -> None:
    with open(bolig_folder / 'data.json', 'w', encoding='utf-8') as f:
        json.dump(bolig_data, f, indent=4)

    for i, image_url in enumerate(images):
        image_data = SESSION.get(image_url).content
        with open(bolig_folder / f'{i}.jpg', 'wb') as f:
            f.write(image_data)


def _process_bolig(bolig: BeautifulSoup) -> None:
    div_tile = bolig.find('div', class_='tile')
    if not div_tile:
        return

    bolig_type = _extract_bolig_type(bolig)
    if bolig_type not in BOLIG_TYPES:
        return

    address_paragraph_raw = div_tile.find('p', class_='tile__address')
    address_paragraph: str = address_paragraph_raw.text.replace(',', '')
    print(f"Extracting data from {address_paragraph}")

    a_tag = bolig.find('a', class_='tile__image-container')
    bolig_url = URL + a_tag['href']

    bolig_folder = Path(OUTPUT_PATH).joinpath(address_paragraph)
    _create_bolig_folder(bolig_folder)

    if OVERRIDE_PREVIOUS_DATA or not (bolig_folder / 'data.json').exists():
        try:
            bolig_data, images = _extract_bolig_data(bolig_url)
            _save_data_and_images(bolig_folder, bolig_data, images)
        except requests.exceptions.RequestException as e:
            print(f"Error extracting data from {bolig_url}: {e}")
    else:
        print(f"Skipping existing data in folder: {bolig_folder}")


def scrape() -> None:
    """Start scraping housing data from nybolig.dk"""
    total_pages: int = _get_pages(PAGES)
    total_boliger: int = 0

    with ThreadPoolExecutor() as executor:
        futures: list = []

        for page in range(1, total_pages + 1):
            sale_url: str = f"{URL}/til-salg?page={page}"
            soup: BeautifulSoup = _get_soup(sale_url)
            for bolig in soup.find_all('li', class_=LISTING_CLASS):
                total_boliger += 1
                futures.append(executor.submit(_process_bolig, bolig))

        # Wait for all threads to finish
        for future in futures:
            future.result()

    print(f"Finished scraping {total_pages} pages")
    print(f"Extracted data from {total_boliger} boliger")


def _get_soup(url: str) -> BeautifulSoup:
    response = SESSION.get(url, headers=HEADERS)
    response.raise_for_status()  # Check if the request was successful
    return BeautifulSoup(response.text, HTML_PARSER)


def _extract_bolig_facts_box(soup: BeautifulSoup) -> dict:
    bolig_data: dict = {
        'size': None,
        'basement_size': None,
        'rooms': None,
        'year_built': None,
        'year_renovated': None,
        'energy_label': None
    }

    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Boligareal' in fact.text:
            bolig_data['size'] = int(fact.find('strong').text.split(' ')[0])
        elif 'Kælderstørrelse' in fact.text:
            bolig_data['basement_size'] = int(fact.find('strong').text.split(' ')[0])
        elif 'Stue/Værelser' in fact.text:
            living_rooms = int(fact.find('strong').text.split('/')[0])
            rooms = int(fact.find('strong').text.split('/')[1])
            bolig_data['rooms'] = living_rooms + rooms
        elif 'Bygget/Ombygget' in fact.text:
            built_rebuilt_raw = fact.find('strong').text.split('/')
            bolig_data['year_built'] = int(built_rebuilt_raw[0])
            if len(built_rebuilt_raw) > 1:
                bolig_data['year_renovated'] = int(built_rebuilt_raw[1])
        elif 'Energimærke' in fact.text:
            bolig_data['energy_label'] = fact.contents[3].get('class')[1].split('-')[2]

    return bolig_data


def _extract_price(soup: BeautifulSoup) -> int:
    price_raw = soup.find('span', class_='case-info__property__info__text__price').text.strip()
    # remove non-numeric characters
    price = int(''.join(filter(str.isdigit, price_raw)))
    return price


def _extract_postal_code(soup: BeautifulSoup) -> int:
    address_components: list = [
        component.text.strip() for component in soup.find_all(
            'strong', class_='case-info__property__info__main__title__address'
        )
    ]

    # Filter out empty components
    address_components = [component for component in address_components if component]

    # The municipality is the last component in the address
    municipality_raw: str = address_components[-1]

    # Extract the postal code from the municipality
    postal_code: int = int(municipality_raw.split(' ')[0])

    return postal_code

def _extract_address(soup: BeautifulSoup) -> str:
    # Extract the address components and join them with a space
    address_components = [
        component.text.strip() for component in soup.find_all(
            'strong', class_='case-info__property__info__main__title__address'
        )
    ]

    # Filter out empty components
    address_components = [component for component in address_components if component]

    # Join the non-empty components with a space
    address = ' '.join(address_components)

    # Remove newline characters from the address
    address = address.replace('\n', '')

    # Remove commas from the address
    address = address.replace(',', '')

    return address


def _extract_bolig_type(bolig: BeautifulSoup) -> str:
    bolig_type_raw = bolig.find('p', class_='tile__mix').text.strip().lower()
    bolig_type = bolig_type_raw.split(' ')[0]

    return bolig_type


def _get_pages(pages: int) -> int:
    if pages > MAX_PAGES:
        print(f"Max pages is {MAX_PAGES}, continuing with {MAX_PAGES} pages")
        pages = MAX_PAGES
    return pages
