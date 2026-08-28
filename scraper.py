import json
import re
import requests
from bs4 import BeautifulSoup
import time
import uuid
import os
import urllib.parse
import boto3
from dotenv import load_dotenv
from io import BytesIO
import mimetypes

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
    load_dotenv()
    
    r2_account_id = os.environ.get("R2_ACCOUNT_ID")
    r2_access_key_id = os.environ.get("R2_ACCESS_KEY_ID")
    r2_secret_access_key = os.environ.get("R2_SECRET_ACCESS_KEY")
    r2_bucket_name = os.environ.get("R2_BUCKET_NAME")
    r2_public_domain = os.environ.get("R2_PUBLIC_DOMAIN", "").rstrip('/')
    
    if not all([r2_account_id, r2_access_key_id, r2_secret_access_key, r2_bucket_name, r2_public_domain]):
        print("Missing required R2 configuration in .env file. Exiting.")
        return

    s3_client = boto3.client(
        's3',
        endpoint_url=f"https://{r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=r2_access_key_id,
        aws_secret_access_key=r2_secret_access_key,
        region_name="auto"
    )

    base_urls = [
        "https://www.adbuq.com/",
        "https://www.adbuq.com/shop/",
        "https://www.adbuq.com/billboards/"
    ]
    
    # Add cities for wider crawling coverage
    cities_for_urls = ["lahore", "karachi", "islamabad", "peshawar", "quetta", "multan", "rawalpindi"]
    for c in cities_for_urls:
        base_urls.append(f"https://www.adbuq.com/product-category/{c}/")
        base_urls.append(f"https://www.adbuq.com/billboards-in-{c}/")
    
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
                cards = soup.select(".featured-item, .listing-item, .ooh-item, div[class*='billboard'], .product")

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

                img_url = ""
                # 1. Prioritize data attributes on img tags
                imgs = card.find_all("img")
                for img in imgs:
                    candidates = [
                        img.get("data-src"),
                        img.get("data-lazy-src"),
                        img.get("data-bg"),
                        img.get("data-original"),
                        img.get("srcset")
                    ]
                    for cand in candidates:
                        if cand and isinstance(cand, str):
                            c_url = cand.split(",")[0].split(" ")[0].strip()
                            if "data:image" not in c_url and "1x1" not in c_url and "placeholder" not in c_url and c_url:
                                img_url = c_url
                                break
                    if not img_url:
                        cand = img.get("src")
                        if cand and isinstance(cand, str):
                            if "data:image" not in cand and "1x1" not in cand and "placeholder" not in cand:
                                img_url = cand.strip()
                    if img_url:
                        break

                # 2. Extract CSS background images
                if not img_url:
                    styled_elements = card.find_all(["div", "a"], style=True)
                    for el in styled_elements:
                        style = el.get("style", "")
                        bg_match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style, re.I)
                        if bg_match:
                            cand = bg_match.group(1).strip()
                            if "data:image" not in cand and "1x1" not in cand and "placeholder" not in cand and cand:
                                img_url = cand
                                break

                # 3. Scrape the detail page if necessary
                if not img_url and detail_url:
                    print(f"Scraping detail page for image: {detail_url}")
                    try:
                        detail_resp = requests.get(detail_url, headers=headers, timeout=10)
                        if detail_resp.status_code == 200:
                            detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                            main_imgs = detail_soup.select(".woocommerce-product-gallery__image img, .property-slider img, .single-property-image img, .entry-content img, .wp-post-image")
                            for img in main_imgs:
                                candidates = [
                                    img.get("data-src"),
                                    img.get("data-lazy-src"),
                                    img.get("data-bg"),
                                    img.get("data-original"),
                                    img.get("srcset")
                                ]
                                for cand in candidates:
                                    if cand and isinstance(cand, str):
                                        c_url = cand.split(",")[0].split(" ")[0].strip()
                                        if "data:image" not in c_url and "1x1" not in c_url and "placeholder" not in c_url and c_url:
                                            img_url = c_url
                                            break
                                if not img_url:
                                    cand = img.get("src")
                                    if cand and isinstance(cand, str):
                                        if "data:image" not in cand and "1x1" not in cand and "placeholder" not in cand:
                                            img_url = cand.strip()
                                if img_url:
                                    break
                    except requests.RequestException:
                        pass

                # 4. Ensure Absolute URLs
                if img_url:
                    img_url = urllib.parse.urljoin('https://www.adbuq.com', img_url)

                # 5. R2 Image Download and Upload
                final_image_url = "NULL"
                if img_url:
                    try:
                        print(f"Downloading image: {img_url}")
                        img_resp = requests.get(img_url, headers=headers, stream=True, timeout=15)
                        if img_resp.status_code == 200:
                            content_type = img_resp.headers.get('content-type')
                            if not content_type:
                                content_type = mimetypes.guess_type(img_url)[0] or 'application/octet-stream'
                            
                            ext = mimetypes.guess_extension(content_type) or '.jpg'
                            if ext == '.jpe':
                                ext = '.jpg'
                                
                            # Create slugified title for filename or fallback to uuid
                            slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
                            if not slug:
                                slug = str(uuid.uuid4())
                            
                            filename = f"{slug}-{uuid.uuid4().hex[:8]}{ext}"
                            
                            print(f"Uploading to R2 as {filename}")
                            file_obj = BytesIO(img_resp.content)
                            s3_client.upload_fileobj(
                                file_obj,
                                r2_bucket_name,
                                filename,
                                ExtraArgs={'ContentType': content_type}
                            )
                            
                            final_image_url = f"{r2_public_domain}/{filename}"
                            time.sleep(0.5) # Rate limiting
                        else:
                            print(f"Failed to download image, status: {img_resp.status_code}")
                    except Exception as e:
                        print(f"Error downloading/uploading image {img_url}: {e}")

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
                    "image_url": clean_text(final_image_url),
                    "detail_url": clean_text(detail_url),
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

    # Split into batches of 50
    batch_size = 50
    with open("inserts.sql", "w", encoding="utf-8") as f:
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            values = []
            for r in batch:
                img_val = f"'{r['image_url']}'" if r['image_url'] and r['image_url'] != "NULL" else "NULL"
                v = f"('{r['title']}', '{r['media_type']}', '{r['city']}', '{r['price']}', {r['numeric_price']}, '{r['size']}', '{r['zone']}', '{r['extendable']}', '{r['availability_status']}', {img_val}, '{r['detail_url']}')"
                values.append(v)
                
            stmt = "INSERT INTO billboards (title, media_type, city, price, numeric_price, size, zone, extendable, availability_status, image_url, detail_url) VALUES \n"
            stmt += ",\n".join(values) + ";"
            
            f.write(stmt + "\n\n")

    print("Generated inserts.sql successfully!")

if __name__ == "__main__":
    scrape_adbuq()
