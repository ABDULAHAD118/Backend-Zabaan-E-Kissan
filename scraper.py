from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrape_crop_prices():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = "http://www.amis.pk/ViewPrices.aspx?searchType=1&commodityId=15"
    driver.get(url)
    driver.implicitly_wait(10)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()
    
    td = soup.find('td', {'id': 'ctl00_cphPage_Grd'})
    if not td:
        print("❌ Data container not found")
        return

    tables = td.find_all('table')
    if not tables:
        print("❌ No tables found inside data container")
        return

    table = tables[0]
    rows = table.find_all('tr')
    data = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 6:
            continue  # skip section titles, merged rows, or short rows

        try:
            name = cols[0].get_text(strip=True)
            min_price = cols[2].get_text(strip=True)
            max_price = cols[3].get_text(strip=True)
            fqp = cols[4].get_text(strip=True)
            quantity = cols[5].get_text(strip=True)
            data.append([name, min_price, max_price, fqp, quantity])
        except IndexError:
            continue  # extra safety

    today = datetime.now().strftime('%Y-%m-%d')
    df = pd.DataFrame(data, columns=["Crop", "Min Price", "Max Price", "FQP", "Quantity"])
    filename = f"data/amis_crop_prices_{today}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Saved {len(data)} crop records to '{filename}'")

scrape_crop_prices()
