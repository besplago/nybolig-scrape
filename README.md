# Nybolig Bolig Scraper
## Overview
This project is designed to scrape data, floor plans, and images from the Nybolig website (https://www.nybolig.dk/). The scraper is implemented in Python and utilizes the BeautifulSoup library for parsing HTML.

## Installation
1. Clone the repository `git clone https://github.com/besplago/nybolig-scrape`
2. Install the required packages using pip: `pip install -r requirements.txt`
3. Activate the virtual environment:
    - Windows: `.\venv\Scripts\activate`
    - Linux: `source venv/bin/activate`
4. Install the required packages using pip: `pip install -r requirements.txt`

## Configuration
Adjust the settings in the main.py file to customize the scraper behavior.
```python
# Main.py

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
# ...
```

## Usage
Once you've configured the settings, you can run the scraper using the following command:
```bash
python main.py
```