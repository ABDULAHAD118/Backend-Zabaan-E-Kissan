from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import time
import json

def get_all_city_links(driver, base_url):
    driver.get(base_url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    city_links = []

    # Extract city name and link
    for a in soup.find_all('a', href=True):
        if 'ViewPrices.aspx' in a['href'] and 'commodityId' in a['href']:
            city_name = a.get_text(strip=True)
            full_url = a['href']
            city_links.append((city_name, full_url))

    return city_links

def scrape_city_prices(city_name, url, driver, all_city_data):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    td = soup.find('td', {'id': 'ctl00_cphPage_Grd'})
    if not td:
        print(f"❌ No data table found for {city_name}")
        return

    tables = td.find_all('table')
    if not tables:
        print(f"❌ No inner tables found for {city_name}")
        return

    rows = tables[0].find_all('tr')
    data = []

    # Extract date
    report_date = "Unknown"
    for row in rows:
        cells = row.find_all('td')
        if cells and 'Dated:' in cells[0].text:
            report_date = cells[0].text.strip().replace('Dated:', '')
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
            data.append({
                "crop": name,
                "min_price": min_price,
                "max_price": max_price,
                "fqp": fqp,
                "quantity": quantity
            })
        except IndexError:
            continue


    if data:
        safe_city = city_name.replace(" ", "_").replace("/", "-")
        all_city_data.append({
            "city": city_name,
            "date": report_date,
            "prices": data
        })
        print(f"✅ {city_name}: {len(data)} records scraped")
    else:
        print(f"⚠️ {city_name}: No crop data found.")

def main():
    os.makedirs("data", exist_ok=True)

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    base_url = 'http://www.amis.pk/DistrictCities.aspx'
    city_links = get_all_city_links(driver, base_url)
    print(f"🔎 Found {len(city_links)} city links to scrape...\n")

    all_city_data = []

    for city_name, city_url in city_links:
        scrape_city_prices(city_name, city_url, driver, all_city_data)

    driver.quit()

    # Save all data to a dated JSON file
    today = datetime.now().strftime('%Y-%m-%d')
    json_path = f"data/crop_prices_{today}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_city_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ All crop prices saved to: {json_path}")

if __name__ == "__main__":
    main()
