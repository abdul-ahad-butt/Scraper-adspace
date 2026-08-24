import json
import re
import requests
from bs4 import BeautifulSoup


def clean_text(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip().replace("'", "''")


def parse_price(price_str):
    if not price_str:
        return 0.0
    numbers = re.findall(r"[\d,]+", price_str)
    if numbers:
        raw = numbers[0].replace(",", "")
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return 0.0


def scrape_adbuq():
    url = "https://www.adbuq.com/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    print("Fetching listings from ADBUQ...")
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch page. Status code: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Target cards based on common listing wrappers
    cards = soup.find_all(
        ["div", "article"], class_=re.compile(r"card|item|listing|product", re.I)
    )

    if not cards:
        cards = soup.select(
            ".featured-item, .listing-item, .ooh-item, div[class*='billboard']"
        )

    records = []

    for card in cards:
        text_content = card.get_text(separator=" ", strip=True)

        title_elem = card.find(
            ["h2", "h3", "h4", "a"], class_=re.compile(r"title|name", re.I)
        )
        title = clean_text(title_elem.get_text()) if title_elem else ""

        if not title or len(title) < 5:
            continue

        price_match = re.search(
            r"Rs\s*[\d,]+(?:/month)?", text_content, re.IGNORECASE
        )
        price_str = price_match.group(0) if price_match else "N/A"
        numeric_price = parse_price(price_str)

        size_match = re.search(
            r"Size:\s*([\w\d\s x]+)", text_content, re.IGNORECASE
        )
        size = clean_text(size_match.group(1)) if size_match else "N/A"

        zone_match = re.search(
            r"Zone:\s*([\w\d\s\,]+)", text_content, re.IGNORECASE
        )
        zone = clean_text(zone_match.group(1)) if zone_match else "N/A"

        ext_match = re.search(
            r"Extendable:\s*(Yes|No)", text_content, re.IGNORECASE
        )
        extendable = ext_match.group(1) if ext_match else "No"

        img = card.find("img")
        img_url = img.get("src", "") if img else ""

        link = card.find("a", href=True)
        detail_url = link["href"] if link else ""

        record = {
            "title": title,
            "media_type": "Static/Digital Billboard",
            "city": "Pakistan",
            "price": price_str,
            "numeric_price": numeric_price,
            "size": size,
            "zone": zone,
            "extendable": extendable,
            "availability_status": "Login to view date",
            "image_url": img_url,
            "detail_url": detail_url,
        }

        if record not in records:
            records.append(record)

    print(f"Scraped {len(records)} records.")

    # Generate SQL file for D1 Batch Execution
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
