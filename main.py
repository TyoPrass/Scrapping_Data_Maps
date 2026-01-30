  
import time
import re
import argparse
import pandas as pd
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager


def click_first(driver, xpaths, timeout=5):  # Kurangi timeout
    """Klik elemen pertama yang ketemu dari daftar XPATH."""
    end = time.time() + timeout
    while time.time() < end:
        for xp in xpaths:
            try:
                el = driver.find_element(By.XPATH, xp)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.1)
                el.click()  # Klik langsung lebih cepat
                return True
            except Exception:
                pass
        time.sleep(0.1)
    return False


def fast_scroll(driver, element):
    """Scroll cepat langsung ke bawah"""
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
    time.sleep(0.3)


def human_like_scroll(driver, element, pause_time=0.5):  # Kurangi pause
    """Scroll lebih cepat dengan delay minimal"""
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
    time.sleep(pause_time)


def random_sleep(min_sec=0.2, max_sec=0.5):
    """Sleep dengan durasi minimal"""
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


def wait_for_manual_interaction(driver, timeout=60, manual_scroll_time=30):
    """Berikan waktu untuk login manual DAN scroll manual"""
    print("\n" + "="*60)
    print("FASE 1: LOGIN MANUAL")
    print("="*60)
    print(f"⏰ Waktu: {timeout} detik")
    print("📝 Silakan login ke akun Google Anda")
    print("="*60 + "\n")
    
    time.sleep(timeout)
    
    print("\n" + "="*60)
    print("FASE 2: SCROLL MANUAL UNTUK PRE-LOAD DATA")
    print("="*60)
    print(f"⏰ Waktu: {manual_scroll_time} detik")
    print("🚀 SCROLL CEPAT-CEPAT KE BAWAH!")
    print("💡 Tips:")
    print("   - Scroll secepat mungkin untuk load banyak ulasan")
    print("   - Semakin banyak scroll = semakin cepat scraping")
    print("   - Data yang sudah ter-load akan langsung di-scrape")
    print("="*60 + "\n")
    
    # Countdown timer
    for remaining in range(manual_scroll_time, 0, -5):
        print(f"⏳ Sisa waktu scroll manual: {remaining} detik...")
        time.sleep(5)
    
    print("\n✓ Melanjutkan scraping otomatis...\n")


def open_reviews_panel(driver, wait):
    random_sleep(0.5, 1.0)
    
    # Klik tab/tombol "Ulasan"
    ok = click_first(driver, [
        "//button[contains(@aria-label,'Ulasan')]",
        "//a[contains(@aria-label,'Ulasan')]",
        "//button[.//div[contains(.,'Ulasan')]]",
        "//button[contains(@aria-label,'Reviews')]",
        "//a[contains(@aria-label,'Reviews')]",
        "//button[.//div[contains(.,'Reviews')]]",
    ], timeout=10)
    if not ok:
        raise RuntimeError("Tidak menemukan tombol 'Ulasan/Reviews'.")

    random_sleep(0.5, 1.0)
    
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
    
    random_sleep(0.5, 1.0)
    return feed


def sort_reviews_newest(driver):
    """Ubah urutan ulasan ke 'Terbaru/Newest'."""
    print("\n⏳ Mengubah urutan ke 'Terbaru'...")
    
    clicked = click_first(driver, [
        "//button[contains(@aria-label,'Urutkan')]",
        "//button[contains(@aria-label,'Sort')]",
        "//button//*[contains(.,'Urutkan')]/ancestor::button",
        "//button//*[contains(.,'Sort')]/ancestor::button",
    ], timeout=5)
    
    if not clicked:
        print("⚠️  Tombol 'Urutkan' tidak ditemukan")
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
        print("⚠️  Menu 'Terbaru' tidak ditemukan\n")
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
                   scroll_pause=0.3, login_time=60, manual_scroll_time=30):
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

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(1)

        try_handle_consent(driver)

        # Login + Manual Scroll untuk pre-load data
        wait_for_manual_interaction(driver, login_time, manual_scroll_time)

        feed = open_reviews_panel(driver, wait)

        if newest_first:
            sort_reviews_newest(driver)

        # Tambahan waktu untuk scroll manual setelah sort
        if manual_scroll_time > 0:
            print(f"\n WAKTU SCROLL MANUAL TAMBAHAN: {manual_scroll_time} detik")
            print(" Scroll lagi untuk pre-load lebih banyak data!")
            print("="*60 + "\n")
            
            # Countdown
            for remaining in range(manual_scroll_time, 0, -10):
                print(f" Sisa waktu: {remaining} detik...")
                time.sleep(10)
            
            print("\n✓ Melanjutkan scraping otomatis...\n")

        last_count = 0
        scroll_attempts = 0
        consecutive_no_new_data = 0
        max_consecutive_no_new_data = 5  # Kurangi dari 15 ke 5

        print("\n" + "="*60)
        print("MEMULAI SCRAPING OTOMATIS - MODE CEPAT")
        print("="*60)
        print("✓ Data lengkap (name, date, text)")
        print("✓ Scroll otomatis minimal delay")
        print("="*60 + "\n")

        while consecutive_no_new_data < max_consecutive_no_new_data:
            expand_more_buttons(driver, feed)

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

                data.append({
                    "name": name,
                    "rating": rating,
                    "date": date,
                    "text": text,
                })
                current_iteration_count += 1

                if max_reviews and len(data) >= max_reviews:
                    break

            if max_reviews and len(data) >= max_reviews:
                print(f"\n✓ Target {max_reviews} ulasan tercapai!")
                break

            # Fast scroll
            fast_scroll(driver, feed)
            scroll_attempts += 1

            if len(data) == last_count:
                consecutive_no_new_data += 1
            else:
                consecutive_no_new_data = 0
                last_count = len(data)
            
            if consecutive_no_new_data >= max_consecutive_no_new_data:
                print(f"\n✓ Tidak ada data baru setelah {consecutive_no_new_data}x scroll")
                break
            
            # Progress setiap 3 scroll
            if scroll_attempts % 3 == 0:
                print(f"⚡ Scroll #{scroll_attempts} | Data: {len(data)} | Diskip: {skipped_count} | Baru: {current_iteration_count}")

        print("\n" + "="*60)
        print("SCRAPING SELESAI")
        print("="*60)
        print(f"Total ulasan: {len(data)}")
        print(f"Diskip (incomplete): {skipped_count}")
        print(f"Total scroll: {scroll_attempts}")
        print("="*60 + "\n")

        return data

    finally:
        print("\nMenutup browser...")
        driver.quit()


def main():
    # ========== KONFIGURASI ==========
    GOOGLE_MAPS_URL = "https://www.google.com/maps/place/Taman+Rajekwesi/@-7.1577847,111.8669561,870m/data=!3m2!1e3!4b1!4m6!3m5!1s0x2e7781f1abd639c9:0xbd04c2f9a63639b6!8m2!3d-7.15779!4d111.871827!16s%2Fg%2F11bv2l_p30?hl=id&entry=ttu&g_ep=EgoyMDI2MDEyNy4wIKXMDSoASAFQAw%3D%3D"
    CHROMEDRIVER_PATH = None
    MAX_REVIEWS = None  # None = ambil semua
    OUTPUT_FILE = "taman_rajekwesi.csv"
    HEADLESS = False
    NEWEST_FIRST = True
    LOGIN_TIME = 60  # Waktu login
    MANUAL_SCROLL_TIME = 30  # Waktu scroll manual untuk pre-load
    # =================================

    print(f" FAST SCRAPING MODE WITH MANUAL SCROLL")
    print(f"URL: {GOOGLE_MAPS_URL}")
    print(f"Login: {LOGIN_TIME}s | Manual Scroll: {MANUAL_SCROLL_TIME}s x2")
    if MAX_REVIEWS:
        print(f"Target: {MAX_REVIEWS} ulasan")
    else:
        print(f"Mode: AMBIL SEMUA ULASAN")
    
    reviews = scrape_reviews(
        url=GOOGLE_MAPS_URL,
        chromedriver_path=CHROMEDRIVER_PATH,
        max_reviews=MAX_REVIEWS,
        headless=HEADLESS,
        newest_first=NEWEST_FIRST,
        login_time=LOGIN_TIME,
        manual_scroll_time=MANUAL_SCROLL_TIME,
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


if __name__ == "__main__":
    main()