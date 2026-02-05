import time
import re
import argparse
import pandas as pd
import random
import signal
import sys
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

# Global variables untuk menyimpan data sementara
TEMP_DATA = []
TEMP_OUTPUT_FILE = ""
DRIVER_INSTANCE = None

def save_temp_data():
    """Simpan data sementara ke CSV saat interupsi"""
    global TEMP_DATA, TEMP_OUTPUT_FILE, DRIVER_INSTANCE
    
    if len(TEMP_DATA) > 0:
        df = pd.DataFrame(TEMP_DATA)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = TEMP_OUTPUT_FILE or f"backup_reviews_{timestamp}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        
        print(f"\n{'='*60}")
        print("  PROSES DIHENTIKAN - DATA OTOMATIS TERSIMPAN")
        print(f"{'='*60}")
        print(f"✓ File: {output_file}")
        print(f"✓ Total: {len(df)} ulasan")
        print(f"\nStatistik:")
        print(f"- Dengan rating: {df['rating'].notna().sum()}")
        print(f"- Tanpa rating: {df['rating'].isna().sum()}")
        print(f"{'='*60}\n")
        return output_file
    else:
        print("\n  Tidak ada data yang tersimpan\n")
        return None

def signal_handler(sig, frame):
    """Handler untuk Ctrl+C dan signal lainnya"""
    global DRIVER_INSTANCE
    print("\n\n  Terdeteksi interupsi (Ctrl+C)...")
    save_temp_data()
    
    # Tutup browser
    if DRIVER_INSTANCE:
        try:
            print("Menutup browser...")
            DRIVER_INSTANCE.quit()
        except:
            pass
    
    sys.exit(0)

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def click_first(driver, xpaths, timeout=5):
    """Klik elemen pertama yang ketemu dari daftar XPATH."""
    end = time.time() + timeout
    while time.time() < end:
        for xp in xpaths:
            try:
                el = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.1)
                el.click()
                return True
            except Exception:
                pass
        time.sleep(0.1)
    return False


def fast_scroll(driver, element, times=2):
    """Scroll cepat tanpa animasi - multiple scrolls sekaligus"""
    for _ in range(times):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
        time.sleep(0.15)  # Delay lebih singkat per scroll


def human_like_scroll(driver, element, pause_time=0.5):
    """Scroll lebih cepat dengan delay minimal"""
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
    time.sleep(pause_time)


def random_sleep(min_sec=0.1, max_sec=0.3):
    """Sleep dengan durasi random minimal"""
    time.sleep(random.uniform(min_sec, max_sec))


def safe_text(parent, css_list):
    """Ambil text pertama yang ketemu dari beberapa selector CSS."""
    for css in css_list:
        try:
            t = parent.find_element(By.CSS_SELECTOR, css).text.strip()
            if t:
                return t
        except Exception:
            pass
    return ""


def safe_attr(parent, css_list, attr):
    for css in css_list:
        try:
            v = parent.find_element(By.CSS_SELECTOR, css).get_attribute(attr)
            if v:
                return v.strip()
        except Exception:
            pass
    return ""


def parse_date_to_datetime(date_str):
    """
    Konversi string tanggal Google Maps ke datetime object.
    """
    if not date_str:
        return None
    
    now = datetime.now()
    date_str_lower = date_str.lower()
    
    match = re.search(r'(\d+)', date_str_lower)
    if not match:
        return now
    
    num = int(match.group(1))
    
    if 'tahun' in date_str_lower or 'year' in date_str_lower:
        return now - timedelta(days=num * 365)
    elif 'bulan' in date_str_lower or 'month' in date_str_lower:
        return now - timedelta(days=num * 30)
    elif 'minggu' in date_str_lower or 'week' in date_str_lower:
        return now - timedelta(weeks=num)
    elif 'hari' in date_str_lower or 'day' in date_str_lower:
        return now - timedelta(days=num)
    elif 'jam' in date_str_lower or 'hour' in date_str_lower:
        return now - timedelta(hours=num)
    elif 'menit' in date_str_lower or 'minute' in date_str_lower:
        return now - timedelta(minutes=num)
    
    return now


def is_within_last_n_years(date_str, years=5):
    """Cek apakah tanggal dalam rentang N tahun terakhir"""
    date_obj = parse_date_to_datetime(date_str)
    if not date_obj:
        return False
    
    cutoff_date = datetime.now() - timedelta(days=years * 365)
    return date_obj >= cutoff_date


def try_handle_consent(driver):
    """Coba klik 'Setuju/Accept' bila muncul dialog consent."""
    random_sleep(0.3, 0.5)
    click_first(driver, [
        "//button//*[contains(.,'Saya setuju')]/ancestor::button",
        "//button//*[contains(.,'Setuju')]/ancestor::button",
        "//button//*[contains(.,'Terima')]/ancestor::button",
        "//button//*[contains(.,'Tolak semua')]/ancestor::button",
        "//button//*[contains(.,'I agree')]/ancestor::button",
        "//button//*[contains(.,'Accept all')]/ancestor::button",
        "//button//*[contains(.,'Accept')]/ancestor::button",
        "//button//*[contains(.,'Reject all')]/ancestor::button",
    ], timeout=4)


def wait_for_manual_login(driver, timeout=60):
    """Berikan waktu HANYA untuk login manual"""
    print("\n" + "="*60)
    print("WAKTU LOGIN MANUAL")
    print("="*60)
    print(f" Waktu: {timeout} detik")
    print(" Silakan:")
    print("   1. Login ke akun Google Anda")
    print("   2. Tunggu hingga halaman Maps terbuka penuh")
    print("   3. Jangan tutup browser!")
    print("\n  Tekan Ctrl+C kapan saja untuk menghentikan dan menyimpan data")
    print("="*60 + "\n")
    
    time.sleep(timeout)
    print("✓ Waktu login selesai, memulai scraping...\n")


def open_reviews_panel(driver, wait):
    random_sleep(0.3, 0.5)
    
    ok = click_first(driver, [
        "//button[contains(@aria-label,'Ulasan')]",
        "//a[contains(@aria-label,'Ulasan')]",
        "//button[.//div[contains(.,'Ulasan')]]",
        "//button[contains(@aria-label,'Reviews')]",
        "//a[contains(@aria-label,'Reviews')]",
        "//button[.//div[contains(.,'Reviews')]]",
    ], timeout=10)
    if not ok:
        raise RuntimeError("Tidak menemukan tombol 'Ulasan/Reviews'. Pastikan URL adalah halaman tempat (place).")

    random_sleep(0.3, 0.5)
    
    feed_selectors = [
        "div[role='feed']",
        "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
        "div[class*='scrollable']"
    ]
    
    feed = None
    for selector in feed_selectors:
        try:
            feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            if feed:
                break
        except Exception:
            continue
    
    if not feed:
        raise RuntimeError("Tidak menemukan container ulasan")
    
    random_sleep(0.3, 0.5)
    return feed


def sort_reviews_newest(driver):
    """Ubah urutan ulasan ke 'Terbaru/Newest'."""
    print(" Mengubah urutan ke 'Terbaru'...")
    
    clicked = click_first(driver, [
        "//button[contains(@aria-label,'Urutkan')]",
        "//button[contains(@aria-label,'Sort')]",
        "//button//*[contains(.,'Urutkan')]/ancestor::button",
        "//button//*[contains(.,'Sort')]/ancestor::button",
    ], timeout=5)
    
    if not clicked:
        print("  Tombol 'Urutkan' tidak ditemukan")
        return False

    time.sleep(0.3)
    
    clicked_newest = click_first(driver, [
        "//*[@role='menu']//*[contains(.,'Terbaru')]/ancestor::*[@role='menuitemradio' or @role='menuitem']",
        "//*[@role='menu']//*[contains(.,'Newest')]/ancestor::*[@role='menuitemradio' or @role='menuitem']",
    ], timeout=5)
    
    if clicked_newest:
        print("✓ Berhasil mengubah urutan ke 'Terbaru'\n")
        time.sleep(0.5)
        return True
    else:
        print("  Menu 'Terbaru' tidak ditemukan\n")
        return False


def expand_more_buttons(driver, container):
    """Klik 'Lainnya/More' dengan cara lebih cepat"""
    xps = [
        ".//button[.//span[contains(.,'Lainnya')]]",
        ".//button[contains(@aria-label,'Lainnya')]",
        ".//button[.//span[contains(.,'More')]]",
        ".//button[contains(@aria-label,'More')]",
    ]
    for xp in xps:
        try:
            btns = container.find_elements(By.XPATH, xp)
            for b in btns:
                try:
                    b.click()
                    time.sleep(0.05)
                except Exception:
                    pass
        except Exception:
            pass


def parse_rating_from_aria(aria_label):
    if not aria_label:
        return ""
    m = re.search(r"(\d+(?:[.,]\d+)?)", aria_label)
    if not m:
        return ""
    return m.group(1).replace(",", ".")


def scrape_reviews(url, chromedriver_path, max_reviews=None, headless=False, newest_first=True, 
                   scroll_pause=0.3, login_time=60, years_back=5):
    global TEMP_DATA, DRIVER_INSTANCE
    
    opts = Options()
    
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36")
    opts.add_argument("--lang=id-ID")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    opts.add_experimental_option("prefs", prefs)
    
    if headless:
        opts.add_argument("--headless=new")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    DRIVER_INSTANCE = driver
    
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['id-ID', 'id', 'en-US', 'en']});
        '''
    })
    
    wait = WebDriverWait(driver, 20)

    data = []
    seen = set()
    skipped_count = 0
    skipped_old_date = 0
    found_old_reviews_count = 0

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        try_handle_consent(driver)

        # HANYA login manual, TANPA scroll manual
        wait_for_manual_login(driver, login_time)

        feed = open_reviews_panel(driver, wait)

        if newest_first:
            sort_reviews_newest(driver)

        last_count = 0
        scroll_attempts = 0
        consecutive_no_new_data = 0
        max_consecutive_no_new_data = 30
        max_old_reviews_before_stop = 30
        scroll_batch_size = 3  # Scroll 3x sebelum parsing data
        parse_every_n_scrolls = 2  # Parse data setiap 2 batch scroll

        print("\n" + "="*60)
        print(f"MEMULAI SCRAPING OTOMATIS - {years_back} TAHUN TERAKHIR")
        print("="*60)
        print("✓ Mode: TURBO SCRAPING (Scroll 3x + Parse Batch)")
        print("✓ Scraping otomatis sedang berjalan")
        print("✓ Anda BISA scroll manual untuk bantu load data")
        print(f"✓ Filter: {years_back} tahun terakhir")
        print("\n TIPS: Sambil proses jalan, scroll manual untuk load lebih banyak!")
        print("  Tekan Ctrl+C untuk stop dan auto-save")
        print("="*60 + "\n")

        while found_old_reviews_count < max_old_reviews_before_stop:
            # Scroll batch dulu (3x scroll sekaligus)
            for _ in range(scroll_batch_size):
                fast_scroll(driver, feed, times=2)  # 2x scroll per call = 6x total
                scroll_attempts += 1
            
            # Expand buttons setelah scroll batch
            expand_more_buttons(driver, feed)
            
            # Parse data setiap 2 batch scroll (atau setiap ~50 data baru)
            if scroll_attempts % parse_every_n_scrolls != 0:
                continue

            items = feed.find_elements(By.CSS_SELECTOR, "div[data-review-id]")
            if not items:
                items = feed.find_elements(By.CSS_SELECTOR, "div[role='article']")

            current_iteration_count = 0
            
            for it in items:
                rid = it.get_attribute("data-review-id") or ""
                signature = rid or (it.text[:120].strip())
                if not signature or signature in seen:
                    continue

                name = safe_text(it, [
                    "div.d4r55", "span.d4r55",
                    "a[href*='maps/contrib']",
                ])

                rating_aria = safe_attr(it, [
                    "span.kvMYJc",
                    "span[role='img']",
                    "span[aria-label*='bintang']",
                    "span[aria-label*='stars']",
                ], "aria-label")
                rating = parse_rating_from_aria(rating_aria)

                date = safe_text(it, [
                    "span.rsqaWe",
                ])

                text = safe_text(it, [
                    "span.wiI7pd",
                    "div.MyEned",
                    "span.MyEned",
                ])

                seen.add(signature)

                if not name or not date or not text:
                    skipped_count += 1
                    continue

                if not is_within_last_n_years(date, years_back):
                    skipped_old_date += 1
                    found_old_reviews_count += 1
                    continue
                else:
                    found_old_reviews_count = 0

                review_data = {
                    "name": name,
                    "rating": rating,
                    "date": date,
                    "text": text,
                }
                data.append(review_data)
                TEMP_DATA = data.copy()  # Update global untuk auto-save
                current_iteration_count += 1

                if max_reviews and len(data) >= max_reviews:
                    break

            if max_reviews and len(data) >= max_reviews:
                print(f"\n Target {max_reviews} ulasan tercapai!")
                break

            if found_old_reviews_count >= max_old_reviews_before_stop:
                print(f"\n Mencapai batas {years_back} tahun ({found_old_reviews_count} ulasan lama)")
                break

            # Check data baru
            if len(data) == last_count:
                consecutive_no_new_data += 1
            else:
                consecutive_no_new_data = 0
                last_count = len(data)
            
            if consecutive_no_new_data >= max_consecutive_no_new_data:
                print(f"\n✓ Tidak ada data baru setelah {consecutive_no_new_data}x scroll")
                break
            
            # Progress update setiap parse (lebih sering)
            print(f" Scroll #{scroll_attempts} | Data: {len(data)} (+{current_iteration_count} baru) | Diskip: {skipped_count} | Lama: {found_old_reviews_count}/{max_old_reviews_before_stop}")

        print("\n" + "="*60)
        print("SCRAPING SELESAI")
        print("="*60)
        print(f"Total ulasan ({years_back} tahun): {len(data)}")
        print(f"Diskip (incomplete): {skipped_count}")
        print(f"Diskip (>{years_back}thn): {skipped_old_date}")
        print(f"Total scroll: {scroll_attempts}")
        print("="*60 + "\n")

        return data

    except KeyboardInterrupt:
        print("\n\n  Proses dihentikan oleh user (Ctrl+C)")
        return data
    
    except Exception as e:
        print(f"\n\n Error: {e}")
        print(" Menyimpan data yang sudah terkumpul...")
        return data
    
    finally:
        print("\nMenutup browser...")
        try:
            driver.quit()
            DRIVER_INSTANCE = None
        except:
            pass


def main():
    global TEMP_OUTPUT_FILE
    
    # ========== KONFIGURASI ==========
    GOOGLE_MAPS_URL = "https://maps.app.goo.gl/jK9NLkyKqCgjFFgW7"
    CHROMEDRIVER_PATH = None
    MAX_REVIEWS = None
    OUTPUT_FILE = "PantaiKedungTumpang.csv"
    HEADLESS = False
    NEWEST_FIRST = True
    LOGIN_TIME = 30  # Waktu login saja
    YEARS_BACK = 5
    # =================================
    
    TEMP_OUTPUT_FILE = OUTPUT_FILE

    print(f" AUTO SCRAPING + MANUAL ASSIST MODE")
    print(f"URL: {GOOGLE_MAPS_URL}")
    print(f"Filter: {YEARS_BACK} tahun terakhir")
    print(f"Login time: {LOGIN_TIME}s")
    print(f"\n Scraping otomatis akan jalan, Anda bisa bantu scroll manual!")
    print(f"  Tekan Ctrl+C kapan saja untuk menghentikan dan auto-save")
    print("="*60 + "\n")
    
    try:
        reviews = scrape_reviews(
            url=GOOGLE_MAPS_URL,
            chromedriver_path=CHROMEDRIVER_PATH,
            max_reviews=MAX_REVIEWS,
            headless=HEADLESS,
            newest_first=NEWEST_FIRST,
            login_time=LOGIN_TIME,
            years_back=YEARS_BACK,
        )

        if len(reviews) > 0:
            df = pd.DataFrame(reviews)
            df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
            print(f"\n✓ Tersimpan: {OUTPUT_FILE}")
            print(f"✓ Total: {len(df)} ulasan")
            
            print("\nStatistik:")
            print(f"- Dengan rating: {df['rating'].notna().sum()}")
            print(f"- Tanpa rating: {df['rating'].isna().sum()}")
            print(f"\nPreview:")
            print(df.head(3).to_string())
        else:
            print("\n✗ Tidak ada data terkumpul")
    
    except KeyboardInterrupt:
        print("\n\n  Proses dihentikan oleh user!")
        save_temp_data()
    
    except Exception as e:
        print(f"\n\n Error tidak terduga: {e}")
        save_temp_data()


if __name__ == "__main__":
    main()