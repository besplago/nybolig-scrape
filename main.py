from bs4 import BeautifulSoup
import requests
import json
import os

# Settings
OUTPUT_PATH = './output'
PAGES = 1 # Amount of pages to scrape
INCLUDE_IMAGES = True # Is very slow if set to True
BOLIG_TYPES = { # Which bolig types to include
    'villa': True,
    'rækkehus': True,
    'ejerlejlighed': True,
    'fritidsbolig': True,
    'andelsbolig': True,
    'villalejlighed': True,
    'landejendom': False,
    'helårsgrund': False,
    'fritidsgrund': False,
}

# Constants
URL = 'https://www.nybolig.dk'
MAX_PAGES = 2404
HTML_PARSER = 'lxml'
LISTING_CLASS = 'list__item'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3 Edge/16.16299'

def _extract_bolig_data(bolig_url: str) -> tuple:
    source = requests.get(bolig_url, headers={'User-Agent': USER_AGENT}).text
    soup: BeautifulSoup = BeautifulSoup(source, HTML_PARSER)
    bolig_data: dict = {}
    image_urls: list = []

    # Extract the data from the bolig
    bolig_data['url'] = bolig_url
    bolig_data['address'] = _extract_address(soup)
    bolig_data['price'] = _extract_price(soup)
    bolig_data['size'] = _extract_size(soup)
    bolig_data['rooms'] = _extract_rooms(soup)
    bolig_data['year_built'] = _extract_year_built(soup)
    bolig_data['year_renovated'] = _extract_year_renovated(soup)

    # Extract floor plan from the bolig
    floor_plan_container: BeautifulSoup = soup.find('div', class_='floorplan__drawing-container')
    if floor_plan_container:
        floor_plan_url: str = floor_plan_container.find('img', class_='floorplan__drawing lazy').get('data-src', '')
        image_urls.append(floor_plan_url)

    # Extract the images from the bolig
    if INCLUDE_IMAGES:
        for image_container in soup.find_all('div', class_='slider-image__image-container'):
            img_tag = image_container.find('img', class_='slider-image__image')
            if img_tag:
                image_url = img_tag.get('data-src', '')
                image_urls.append(image_url)

    return (bolig_data, image_urls)

def _start_scraping(pages: int) -> None:
    pages: int = _get_pages(pages)
    page: int = 1
    while page <= pages:
        sale_url: str = f"{URL}/til-salg?page={page}"
        source: str = requests.get(sale_url, headers={'User-Agent': 'Mozilla/5.0'}).text
        soup: BeautifulSoup = BeautifulSoup(source, HTML_PARSER)
        for bolig in soup.find_all('li', class_=LISTING_CLASS):
            div_tile: BeautifulSoup = bolig.find('div', class_='tile')
            if not div_tile:
                continue
            valid_bolig_type: bool = _check_bolig_type(bolig)
            if not valid_bolig_type:
                continue
            address_paragraph: BeautifulSoup = div_tile.find('p', class_='tile__address')
            print(f"Extracting data from {address_paragraph.text}")

            a_tag = bolig.find('a', class_='tile__image-container')
            bolig_url: str = URL + a_tag['href']

            # Create new folder for bolig
            bolig_folder: str = f"{OUTPUT_PATH}/{address_paragraph.text}"
            if not os.path.exists(bolig_folder):
                os.mkdir(bolig_folder)

            # Extract the data from the bolig
            try:
                bolig_data, images = _extract_bolig_data(bolig_url)
                # Save the data to a json file
                with open(f"{bolig_folder}/data.json", 'w') as f:
                    json.dump(bolig_data, f, indent=4)

                # Save the images to the folder
                for i, image_url in enumerate(images):
                    image_data = requests.get(image_url).content
                    with open(f"{bolig_folder}/{i}.jpg", 'wb') as f:
                        f.write(image_data)
            except Exception as e:
                print(f"Error extracting data from {bolig_url}: {e}")
        page += 1
    print(f"Finished scraping {pages} pages")

def _extract_year_renovated(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Bygget/Ombygget' in fact.text:
            year_renovated_raw: str = fact.find('strong').text.split('/')
            if len(year_renovated_raw) > 1:
                year_renovated: int = int(year_renovated_raw[1])
                return year_renovated
            else:
                return None

def _extract_year_built(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Bygget/Ombygget' in fact.text:
            year_built: int = int(fact.find('strong').text.split('/')[0])
            return year_built

def _extract_rooms(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Stue/Værelser' in fact.text:
            living_rooms: int = int(fact.find('strong').text.split('/')[0])
            rooms: int = int(fact.find('strong').text.split('/')[1])
            return living_rooms + rooms

def _extract_size(soup: BeautifulSoup) -> int:
    for fact in soup.find_all('div', class_='case-facts__box-inner-wrap'):
        if 'Boligareal' in fact.text:
            return int(fact.find('strong').text.split(' ')[0])

def _extract_price(soup: BeautifulSoup) -> int:
    price_raw: str = soup.find('span', class_='case-info__property__info__text__price').text.strip()
    # remove non-numeric characters
    price: int = int(''.join(filter(str.isdigit, price_raw)))
    return price

def _extract_address(soup: BeautifulSoup) -> str:
    # Extract the address components and join them with a space
    address_components = [
        component.text.strip() for component in soup.find_all('strong', class_='case-info__property__info__main__title__address')
    ]

    # Filter out empty components
    address_components = [component for component in address_components if component]

    # Join the non-empty components with a space
    address: str = ' '.join(address_components)

    # Remove newline characters from the address
    address = address.replace('\n', '')

    return address

def _check_bolig_type(bolig: BeautifulSoup) -> bool:
    bolig_type_raw: str = bolig.find('p', class_='tile__mix').text.strip().lower()
    bolig_type: str = bolig_type_raw.split(' ')[0]
    if bolig_type in BOLIG_TYPES:
        return BOLIG_TYPES[bolig_type]
    else:
        print(f"Unknown bolig type: {bolig_type}")
        return False

def _get_pages(pages: int) -> int:
    if pages > MAX_PAGES:
        print(f"Max pages is {MAX_PAGES}, continuing with {MAX_PAGES} pages")
        pages = MAX_PAGES
    return pages

def _check_output_path() -> None:
    if not os.path.exists(OUTPUT_PATH):
        os.mkdir(OUTPUT_PATH)

def main():
    _check_output_path()
    _start_scraping(PAGES)

if __name__ == '__main__':
    main()
