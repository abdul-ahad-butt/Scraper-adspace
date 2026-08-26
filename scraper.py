import json
import re
import requests
from bs4 import BeautifulSoup
import time
import uuid

def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().replace("'", "''")

def extract_city(title, text_content):
    cities = ["Lahore", "Karachi", "Islamabad", "Quetta", "Peshawar", "Multan", "Rawalpindi", "Faisalabad", "Gujranwala", "Sialkot", "Hyderabad", "Sukkur", "Bahawalpur", "Sargodha"]
    combined = f"{title} {text_content}".lower()
    for city in cities:
        if city.lower() in combined:
            return city
    return "Pakistan"

def extract_media_type(title, text_content):
    types = ["Bridge Panel", "Digital Billboard", "Static Billboard", "Pole Sign", "SMD Screen", "Hoarding", "Gantry", "Streamer", "Wall Panel"]
    combined = f"{title} {text_content}".lower()
    for mt in types:
        if mt.lower() in combined:
            return mt
    
    if "bridge" in combined:
        return "Bridge Panel"
    elif "smd" in combined or "screen" in combined:
        return "Digital Billboard"
    return "Static/Digital Billboard"

def parse_price(price_str):
    if not price_str or "n/a" in price_str.lower():
        return 0.0
    numbers = re.findall(r"[\d,]+", price_str)
    if numbers:
        raw = numbers[-1].replace(",", "")
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return 0.0

def scrape_adbuq():
    base_urls = [
        "https://www.adbuq.com/",
        "https://www.adbuq.com/shop/",
        "https://www.adbuq.com/billboards/"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    records = []
    seen_urls = set()

    for base in base_urls:
        page = 1
        while page <= 20: 
            url = f"{base}page/{page}/" if page > 1 else base
            print(f"Fetching {url}...")
            
            try:
                response = requests.get(url, headers=headers, timeout=15)
            except requests.RequestException as e:
                print(f"Failed to fetch {url}: {e}")
                break
                
            if response.status_code == 404:
                print("Hit 404, stopping pagination for this endpoint.")
                break
            elif response.status_code != 200:
                print(f"Status {response.status_code}, stopping.")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            
            cards = soup.find_all("div", class_=re.compile(r"item-listing-wrap|property-listing|item-wrap-v", re.I))
            if not cards:
                cards = soup.select(".featured-item, .listing-item, .ooh-item, div[class*='billboard']")

            if not cards:
                print("No cards found on this page. Stopping pagination.")
                break

            new_records_on_page = 0

            for card in cards:
                text_content = card.get_text(separator=" ", strip=True)
                
                title_elem = card.find(["h2", "h3", "h4"], class_=re.compile(r"title|name", re.I))
                if not title_elem:
                    title_elem = card.find("h2") or card.find("h3")

                title = clean_text(title_elem.get_text()) if title_elem else ""
                
                # Get detail_url from the title element link to avoid getting label links
                link = title_elem.find("a", href=True) if title_elem else None
                detail_url = link["href"] if link else ""

                if not title or len(title) < 5 or not detail_url:
                    continue

                if detail_url in seen_urls:
                    continue
                seen_urls.add(detail_url)

                city = extract_city(title, text_content)
                media_type = extract_media_type(title, text_content)

                price_match = re.search(r"(?:Rs\.?|PKR)\s*([\d,]+)(?:\s*/\s*month)?", text_content, re.IGNORECASE)
                price_str = f"Rs {price_match.group(1)}" if price_match else "N/A"
                numeric_price = parse_price(price_str)

                size_match = re.search(r"(?:Size|Dimensions?):\s*([\w\d\s x]+(?:ft|feet|sqft)?)", text_content, re.IGNORECASE)
                if not size_match:
                    size_match = re.search(r"(\d+\s*x\s*\d+\s*(?:ft|feet)?)", text_content, re.IGNORECASE)
                size = clean_text(size_match.group(1)) if size_match else "N/A"

                zone_match = re.search(r"Zone:\s*([\w\d\s\,]+)", text_content, re.IGNORECASE)
                zone = clean_text(zone_match.group(1)) if zone_match else "N/A"

                ext_match = re.search(r"Extendable:\s*(Yes|No)", text_content, re.IGNORECASE)
                extendable = ext_match.group(1) if ext_match else "No"
                
                if "extendable" in text_content.lower() and extendable == "No":
                    extendable = "Yes"

                availability_status = "Login to view date"

                img = card.find("img")
                img_url = ""
                if img:
                    img_url = img.get("data-src") or img.get("src") or ""

                record = {
                    "title": title,
                    "media_type": media_type,
                    "city": city,
                    "price": price_str,
                    "numeric_price": numeric_price,
                    "size": size,
                    "zone": zone,
                    "extendable": extendable,
                    "availability_status": availability_status,
                    "image_url": img_url,
                    "detail_url": detail_url,
                }
                records.append(record)
                new_records_on_page += 1

            if new_records_on_page == 0:
                print("No new unique records on this page. Moving to next endpoint.")
                break

            time.sleep(1)
            page += 1

    print(f"\nScrape Complete. Total unique records extracted: {len(records)}")

    if not records:
        print("No records scraped. Returning without SQL generation.")
        return

    sql_statements = []
    for r in records:
        stmt = f"""INSERT INTO billboards (title, media_type, city, price, numeric_price, size, zone, extendable, availability_status, image_url, detail_url)
VALUES ('{r['title']}', '{r['media_type']}', '{r['city']}', '{r['price']}', {r['numeric_price']}, '{r['size']}', '{r['zone']}', '{r['extendable']}', '{r['availability_status']}', '{r['image_url']}', '{r['detail_url']}');"""
        sql_statements.append(stmt)

    with open("inserts.sql", "w", encoding="utf-8") as f:
        f.write("\n".join(sql_statements))

    print("Generated inserts.sql successfully!")

if __name__ == "__main__":
    scrape_adbuq()
