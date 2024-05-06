# Nybolig Bolig Scraper
![Nybolig Logo](https://www.nybolig.dk/-/media/nybolig/billeder-og-videoer/nybolig-presse/nb_4f.jpg?rev=e43a3eadd3264886a0d9c11bce9d5d17)

## Overview
This project is designed to scrape data, floor plans, and images from the Nybolig website ([https://www.nybolig.dk/](nybolig.dk/)). The scraper is implemented in Python and utilizes the BeautifulSoup library for parsing HTML.

## Installation
1. Clone the repository `git clone https://github.com/besplago/nybolig-scrape`
2. Activate the virtual environment (optional, but recommended):
    - Windows: `.\venv\Scripts\activate`
    - Linux: `source venv/bin/activate`
3. Install the required packages using pip: `pip install -r requirements.txt`

## Configuration
Adjust the settings in the `config.json` file to customize the scraper behavior. You can find the configuration file [here](./config.json).

- **output_path**: Specifies the directory where scraped data will be stored.
- **pages**: Defines the number of pages the scraper will traverse on the Nybolig website. Will stop working with more than ~400 pages, as these boliger are not setup on Nybolig.dk, but are simply redirections.
- **include_images**: Determines whether to download property images besides the floorplan. Set to `true` to download images; otherwise, set to `false`.
- **override_previous_data**: If set to `true`, it will overwrite any existing data in the output directory; otherwise, it will append new data.
- **bolig_types**: Specifies the types of properties to include in the scraping process. Each property type can be toggled on or off.
- **postal_code_filters**: Allows filtering properties based on postal codes. You can specify ranges of postal codes and individual postal codes to include in the scraping process.
- **remaining stuff**: Probably don't touch :\)

**Note**: if `"include_images = true"`, the scraper will download all images. This can take a long time and consume a lot of disk space.

## Usage
Once you've configured the settings, you can run the scraper using the following command:
```bash
python main.py
