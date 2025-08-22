from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CropPriceDatabase:
    def __init__(self, connection_string="mongodb+srv://abdulahadhussain60:burewala123@cluster0.ea9ayds.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", database_name="crop_prices_db"):
        """Initialize MongoDB connection"""
        try:
            self.client = MongoClient(connection_string)
            self.db = self.client[database_name]
            self.collection = self.db.crop_prices

            # Test connection
            self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")

            # Create indexes for better performance
            self.create_indexes()

        except ConnectionFailure:
            logger.error("Failed to connect to MongoDB")
            raise

    def create_indexes(self):
        """Create indexes for better query performance"""
        try:
            # Create compound index on city, date, and crop for uniqueness
            self.collection.create_index([
                ("city", 1),
                ("date", 1),
                ("crop", 1)
            ], unique=True, background=True)

            # Create individual indexes for common queries
            self.collection.create_index("city", background=True)
            self.collection.create_index("date", background=True)
            self.collection.create_index("crop", background=True)

            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    def save_city_data(self, city_data):
        """Save city data to MongoDB"""
        city_name = city_data['city']
        date = city_data['date']
        prices = city_data['prices']

        documents_to_insert = []

        for price_data in prices:
            document = {
                'city': city_name,
                'date': date,
                'crop': price_data['crop'],
                'min_price': price_data['min_price'],
                'max_price': price_data['max_price'],
                'fqp': price_data['fqp'],
                'quantity': price_data['quantity'],
                'scraped_at': datetime.now()
            }
            documents_to_insert.append(document)

        if documents_to_insert:
            try:
                result = self.collection.insert_many(documents_to_insert, ordered=False)
                logger.info(f"✅ Saved {len(result.inserted_ids)} records for {city_name}")
                return len(result.inserted_ids)
            except DuplicateKeyError:
                logger.warning(f"⚠️ Some duplicate records found for {city_name}, skipping...")
                return 0
            except Exception as e:
                logger.error(f"❌ Error saving data for {city_name}: {e}")
                return 0
        return 0

    def close_connection(self):
        """Close MongoDB connection"""
        self.client.close()
        logger.info("MongoDB connection closed")

def create_robust_driver():
    """Create a robust Chrome driver with proper configuration"""
    options = Options()

    # Critical Chrome options for stability on Linux
    options.add_argument('--headless=new')  # Use new headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--disable-background-timer-throttling')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-default-apps')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-component-update')
    options.add_argument('--disable-client-side-phishing-detection')
    options.add_argument('--disable-hang-monitor')
    options.add_argument('--disable-prompt-on-repost')
    options.add_argument('--disable-domain-reliability')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--single-process')  # Run in single process mode
    options.add_argument('--no-zygote')  # Disable zygote process
    options.add_argument('--memory-pressure-off')
    options.add_argument('--max_old_space_size=4096')

    # Window and display settings
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-infobars')

    # Network settings
    options.add_argument('--aggressive-cache-discard')
    options.add_argument('--disable-images')  # Skip loading images for faster scraping

    # User agent to avoid detection
    options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    # Additional prefs to prevent crashes
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('prefs', {
        'profile.default_content_setting_values.notifications': 2,
        'profile.default_content_settings.popups': 0,
        'profile.managed_default_content_settings.images': 2,
        'profile.content_settings.plugin_whitelist.adobe-flash-player': 1,
        'profile.content_settings.exceptions.plugins.*,*.per_resource.adobe-flash-player': 1
    })

    try:
        # Try different Chrome binary locations
        chrome_paths = [
            '/usr/bin/google-chrome',
            '/usr/bin/google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium'
        ]

        chrome_binary = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_binary = path
                break

        if chrome_binary:
            options.binary_location = chrome_binary
            logger.info(f"Using Chrome binary: {chrome_binary}")

        service = Service(ChromeDriverManager().install())
        service.start()  # Start service manually

        driver = webdriver.Chrome(service=service, options=options)

        # Test if driver is working
        try:
            driver.get('data:text/html,<html><body><h1>Test</h1></body></html>')
            logger.info("Chrome driver test successful")
        except Exception as e:
            logger.error(f"Chrome driver test failed: {e}")
            driver.quit()
            raise

        # Set timeouts
        driver.set_page_load_timeout(60)
        driver.implicitly_wait(10)

        logger.info("Chrome driver created successfully")
        return driver

    except Exception as e:
        logger.error(f"Failed to create Chrome driver: {e}")
        # Try alternative approach with Firefox
        logger.info("Attempting to use Firefox as fallback...")
        try:
            from selenium.webdriver.firefox.options import Options as FirefoxOptions
            from selenium.webdriver.firefox.service import Service as FirefoxService
            from webdriver_manager.firefox import GeckoDriverManager

            firefox_options = FirefoxOptions()
            firefox_options.add_argument('--headless')
            firefox_options.add_argument('--no-sandbox')
            firefox_options.add_argument('--disable-dev-shm-usage')

            firefox_service = FirefoxService(GeckoDriverManager().install())
            driver = webdriver.Firefox(service=firefox_service, options=firefox_options)

            driver.set_page_load_timeout(60)
            driver.implicitly_wait(10)

            logger.info("Firefox driver created as fallback")
            return driver

        except Exception as firefox_error:
            logger.error(f"Firefox fallback also failed: {firefox_error}")
            raise Exception("Both Chrome and Firefox drivers failed to initialize")

def get_all_city_links(driver, base_url, max_retries=3):
    """Get all city links with retry mechanism"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching city links (attempt {attempt + 1}/{max_retries})")
            driver.get(base_url)

            # Wait for page to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "a"))
            )

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            city_links = []

            # Extract city name and link
            for a in soup.find_all('a', href=True):
                if 'ViewPrices.aspx' in a['href'] and 'commodityId' in a['href']:
                    city_name = a.get_text(strip=True)
                    full_url = a['href']
                    city_links.append((city_name, full_url))

            logger.info(f"Found {len(city_links)} city links")
            return city_links

        except Exception as e:
            logger.error(f"Error fetching city links (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in 5 seconds...")
                time.sleep(5)
            else:
                logger.error("Failed to fetch city links after all retries")
                return []

def scrape_city_prices(city_name, url, driver, db, max_retries=3):
    """Scrape city prices with retry mechanism and better error handling"""
    for attempt in range(max_retries):
        try:
            logger.info(f"Scraping {city_name} (attempt {attempt + 1}/{max_retries})")

            # Navigate to the page
            driver.get(url)

            # Wait for the data table to load
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "ctl00_cphPage_Grd"))
            )

            # Additional wait to ensure content is loaded
            time.sleep(3)

            soup = BeautifulSoup(driver.page_source, 'html.parser')

            td = soup.find('td', {'id': 'ctl00_cphPage_Grd'})
            if not td:
                logger.warning(f"❌ No data table found for {city_name}")
                return

            tables = td.find_all('table')
            if not tables:
                logger.warning(f"❌ No inner tables found for {city_name}")
                return

            rows = tables[0].find_all('tr')
            data = []

            # Extract date
            report_date = "Unknown"
            for row in rows:
                cells = row.find_all('td')
                if cells and 'Dated:' in cells[0].text:
                    report_date = cells[0].text.strip().replace('Dated:', '').strip()
                    break

            # Extract prices
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 6:
                    continue  # skip merged or short rows

                # Skip rows that are headers or labels like "Dated", "Min", "Max", etc.
                if "Dated" in cols[0].get_text() or "Min" in cols[2].get_text():
                    continue

                try:
                    name = cols[0].get_text(strip=True).replace("\xa0", " ")
                    min_price = cols[2].get_text(strip=True)
                    max_price = cols[3].get_text(strip=True)
                    fqp = cols[4].get_text(strip=True)
                    quantity = cols[5].get_text(strip=True)

                    # Skip empty rows
                    if not name or name.isspace():
                        continue

                    data.append({
                        "crop": name,
                        "min_price": min_price,
                        "max_price": max_price,
                        "fqp": fqp,
                        "quantity": quantity
                    })
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Skipping malformed row in {city_name}: {e}")
                    continue

            if data:
                city_data = {
                    "city": city_name,
                    "date": report_date,
                    "prices": data
                }
                saved_count = db.save_city_data(city_data)
                logger.info(f"✅ {city_name}: {len(data)} records processed, {saved_count} saved")
                return  # Success, exit retry loop
            else:
                logger.warning(f"⚠️ {city_name}: No crop data found.")
                return

        except TimeoutException:
            logger.error(f"Timeout while scraping {city_name} (attempt {attempt + 1})")
        except WebDriverException as e:
            logger.error(f"WebDriver error for {city_name} (attempt {attempt + 1}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error for {city_name} (attempt {attempt + 1}): {e}")

        if attempt < max_retries - 1:
            logger.info(f"Retrying {city_name} in 5 seconds...")
            time.sleep(5)
        else:
            logger.error(f"❌ Failed to scrape {city_name} after {max_retries} attempts")

def main():
    """Main function with improved error handling and progress tracking"""
    # Initialize database connection
    try:
        db = CropPriceDatabase()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return

    driver = None
    try:
        # Setup Selenium driver
        driver = create_robust_driver()

        base_url = 'http://www.amis.pk/DistrictCities.aspx'
        city_links = get_all_city_links(driver, base_url)

        if not city_links:
            logger.error("No city links found. Exiting.")
            return

        logger.info(f"🔎 Found {len(city_links)} city links to scrape...\n")

        # Progress tracking
        success_count = 0
        failed_count = 0

        for i, (city_name, city_url) in enumerate(city_links, 1):
            logger.info(f"Progress: {i}/{len(city_links)} - Processing {city_name}")

            try:
                scrape_city_prices(city_name, city_url, driver, db)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to process {city_name}: {e}")
                failed_count += 1

            # Add delay between requests to be respectful
            time.sleep(2)

            # Progress update every 10 cities
            if i % 10 == 0:
                logger.info(f"Progress update: {i}/{len(city_links)} completed, {success_count} successful, {failed_count} failed")

        logger.info(f"\n✅ Scraping completed!")
        logger.info(f"Total cities processed: {len(city_links)}")
        logger.info(f"Successful: {success_count}")
        logger.info(f"Failed: {failed_count}")

    except Exception as e:
        logger.error(f"Critical error in main function: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Driver closed successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

        try:
            db.close_connection()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

if __name__ == "__main__":
    main()