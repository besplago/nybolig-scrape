from bs4 import BeautifulSoup
import requests

URL = 'https://www.nybolig.dk'
PAGES = 1
MAX_PAGES = 2404
BOLIG_TYPES = {
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
HTML_PARSER = 'lxml'
LISTING_CLASS = 'list__item'

def _extract_bolig_data(bolig_url: str) -> None:
    source: str = requests.get(bolig_url, headers={'User-Agent': 'Mozilla/5.0'}).text
    soup: BeautifulSoup = BeautifulSoup(source, HTML_PARSER)
    bolig_data: dict = {}
    bolig_data['address'] = _extract_address(soup)
    bolig_data['price'] = soup.find('span', class_='case-info__property__info__text__price').text.strip()
    bolig_data['size'] = _extract_size(soup)

    print(bolig_data)

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
            try:
                _extract_bolig_data(bolig_url)
            except Exception as e:
                print(f"Error extracting data from {bolig_url}: {e}")
        page += 1
    print(f"Finished scraping {pages} pages")

def _extract_size(soup: BeautifulSoup) -> str:
    for fact in soup.find_all('div', class_='case-facts__box'):
        if 'Boligareal' in fact.text:
            return fact.find('strong').text.strip()

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

def main():
    _start_scraping(PAGES)

if __name__ == '__main__':
    main()
