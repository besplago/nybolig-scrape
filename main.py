"""main.py"""
import argparse
import scraper
import converter

def main():
    """Main function for the scraping and converting tool."""
    parser = argparse.ArgumentParser(description='Scraping and converting tool.')

    # Add arguments for scraping and converting with shorthand options
    parser.add_argument('-s', '--scrape', action='store_true', help='Start the scraping process.')
    parser.add_argument(
        '-c', '--convert', action='store_true', help='Start the conversion process.'
    )

    args = parser.parse_args()

    if args.scrape:
        scraper.scrape()

    if args.convert:
        converter.convert()

if __name__ == '__main__':
    main()
