from bs4 import BeautifulSoup
import requests
import json
import os
from pathlib import Path

# Load configuration from file
config_file_path = Path("config.json")
if not config_file_path.is_file():
    raise FileNotFoundError("Configuration file not found.")

with open(config_file_path, "r", encoding="utf-8") as config_file:
    config = json.load(config_file)

URL = config["url"]
PAGES = config["pages"]
INCLUDE_IMAGES = config["include_images"]
OUTPUT_PATH = config["output_path"]
USER_AGENT = config["user_agent"]
HTML_PARSER = config["html_parser"]
LISTING_CLASS = config["listing_class"]
BOLIG_TYPES = config["bolig_types"]
MAX_PAGES = config["max_pages"]

SESSION = requests.Session()
HEADERS = {'User-Agent': USER_AGENT}

def _extract_bolig_data(bolig_url: str) -> tuple:
    source = SESSION.get(bolig_url, headers=HEADERS).text
    soup = BeautifulSoup(source, HTML_PARSER)
    bolig_data = {}
    image_urls = []

    # Extract the data from the bolig
    bolig_data['url'] = bolig_url
    bolig_data['address'] = _extract_address(soup)
    bolig_data['price'] = _extract_price(soup)
    bolig_data['size'] = _extract_size(soup)
    bolig_data['rooms'] = _extract_rooms(soup)
    bolig_data['year_built'] = _extract_year_built(soup)
    bolig_data['year_renovated'] = _extract_year_renovated(soup)

    # Extract floor plan from the bolig
    floor_plan_container = soup.find('div', class_='floorplan__drawing-container')
    if floor_plan_container:
        floor_plan_url = floor_plan_container.find('img', class_='floorplan__drawing lazy').get('data-src', '')
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
    bolig_folder.mkdir(parents=True, exist_ok=True)


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

    valid_bolig_type = _check_bolig_type(bolig)
    if not valid_bolig_type:
        return

    address_paragraph = div_tile.find('p', class_='tile__address')
    print(f"Extracting data from {address_paragraph.text}")

    a_tag = bolig.find('a', class_='tile__image-container')
    bolig_url = URL + a_tag['href']

    bolig_folder = Path(OUTPUT_PATH).joinpath(address_paragraph.text)
    _create_bolig_folder(bolig_folder)

    try:
        bolig_data, images = _extract_bolig_data(bolig_url)
        _save_data_and_images(bolig_folder, bolig_data, images)
    except requests.exceptions.RequestException as e:
        print(f"Error extracting data from {bolig_url}: {e}")


def _start_scraping(pages: int) -> None:
    total_pages = _get_pages(pages)
    for page in range(1, total_pages + 1):
        sale_url = f"{URL}/til-salg?page={page}"
        soup = _get_soup(sale_url)
        for bolig in soup.find_all('li', class_=LISTING_CLASS):
            _process_bolig(bolig)
    print(f"Finished scraping {total_pages} pages")


def _get_soup(url: str) -> BeautifulSoup:
    response = SESSION.get(url, headers=HEADERS)
    response.raise_for_status()  # Check if the request was successful
    return BeautifulSoup(response.text, HTML_PARSER)


def _extract_year_renovated(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Bygget/Ombygget' in fact.text:
            year_renovated_raw = fact.find('strong').text.split('/')
            if len(year_renovated_raw) > 1:
                year_renovated = int(year_renovated_raw[1])
                return year_renovated
            else:
                return None


def _extract_year_built(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Bygget/Ombygget' in fact.text:
            year_built = int(fact.find('strong').text.split('/')[0])
            return year_built


def _extract_rooms(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Stue/Værelser' in fact.text:
            living_rooms = int(fact.find('strong').text.split('/')[0])
            rooms = int(fact.find('strong').text.split('/')[1])
            return living_rooms + rooms


def _extract_size(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Boligareal' in fact.text:
            return int(fact.find('strong').text.split(' ')[0])


def _extract_price(soup: BeautifulSoup) -> int:
    price_raw = soup.find('span', class_='case-info__property__info__text__price').text.strip()
    # remove non-numeric characters
    price = int(''.join(filter(str.isdigit, price_raw)))
    return price


def _extract_address(soup: BeautifulSoup) -> str:
    # Extract the address components and join them with a space
    address_components = [
        component.text.strip() for component in soup.find_all('strong', class_='case-info__property__info__main__title__address')
    ]

    # Filter out empty components
    address_components = [component for component in address_components if component]

    # Join the non-empty components with a space
    address = ' '.join(address_components)

    # Remove newline characters from the address
    address = address.replace('\n', '')

    return address


def _check_bolig_type(bolig: BeautifulSoup) -> bool:
    bolig_type_raw = bolig.find('p', class_='tile__mix').text.strip().lower()
    bolig_type = bolig_type_raw.split(' ')[0]
    if bolig_type in BOLIG_TYPES:
        return BOLIG_TYPES[bolig_type]
    else:
        print(BOLIG_TYPES)
        print(f"Unknown bolig type: {bolig_type}")
        return False


def _get_pages(pages: int) -> int:
    if pages > MAX_PAGES:
        print(f"Max pages is {MAX_PAGES}, continuing with {MAX_PAGES} pages")
        pages = MAX_PAGES
    return pages


def main():
    _start_scraping(PAGES)


if __name__ == '__main__':
    main()
