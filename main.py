"""Main module for the scraping and converting tool."""
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

    # Check if neither -s nor -c options are provided, then call both functions
    if not args.scrape and not args.convert:
        scraper.scrape()
        converter.convert()
    else:
        # Otherwise, execute the corresponding functions based on the provided arguments
        if args.scrape:
            scraper.scrape()

        if args.convert:
            converter.convert()

if __name__ == '__main__':
    main()
