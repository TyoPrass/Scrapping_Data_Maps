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


def click_first(driver, xpaths, timeout=8):
    """Klik elemen pertama yang ketemu dari daftar XPATH."""
    end = time.time() + timeout
    while time.time() < end:
        for xp in xpaths:
            try:
                el = driver.find_element(By.XPATH, xp)
                # Gunakan ActionChains untuk simulasi klik manusia
                ActionChains(driver).move_to_element(el).pause(random.uniform(0.1, 0.3)).click().perform()
                return True
            except Exception:
                pass
        time.sleep(0.2)
    return False


def human_like_scroll(driver, element, pause_time=1.2):
    """Scroll seperti manusia dengan kecepatan bervariasi"""
    scroll_pause = random.uniform(pause_time * 0.8, pause_time * 1.2)
    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", element)
    time.sleep(scroll_pause)


def random_sleep(min_sec=0.5, max_sec=2.0):
    """Sleep dengan durasi random seperti perilaku manusia"""
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
    random_sleep(0.5, 1.5)
    click_first(driver, [
        # Indonesia
        "//button//*[contains(.,'Saya setuju')]/ancestor::button",
        "//button//*[contains(.,'Setuju')]/ancestor::button",
        "//button//*[contains(.,'Terima')]/ancestor::button",
        "//button//*[contains(.,'Tolak semua')]/ancestor::button",
        # Inggris
        "//button//*[contains(.,'I agree')]/ancestor::button",
        "//button//*[contains(.,'Accept all')]/ancestor::button",
        "//button//*[contains(.,'Accept')]/ancestor::button",
        "//button//*[contains(.,'Reject all')]/ancestor::button",
    ], timeout=6)


def open_reviews_panel(driver, wait):
    random_sleep(1, 2)
    
    # Klik tab/tombol "Ulasan"
    ok = click_first(driver, [
        "//button[contains(@aria-label,'Ulasan')]",
        "//a[contains(@aria-label,'Ulasan')]",
        "//button[.//div[contains(.,'Ulasan')]]",
        # Inggris (cadangan)
        "//button[contains(@aria-label,'Reviews')]",
        "//a[contains(@aria-label,'Reviews')]",
        "//button[.//div[contains(.,'Reviews')]]",
    ], timeout=15)
    if not ok:
        raise RuntimeError("Tidak menemukan tombol 'Ulasan/Reviews'. Pastikan URL adalah halaman tempat (place).")

    # Tunggu container review muncul
    feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
    random_sleep(1, 2)
    return feed


def sort_reviews_newest(driver):
    """Opsional: ubah urutan ulasan ke 'Terbaru/Newest'."""
    clicked = click_first(driver, [
        "//button[contains(@aria-label,'Urutkan')]",
        "//button[contains(@aria-label,'Sort')]",
        "//button//*[contains(.,'Urutkan')]/ancestor::button",
        "//button//*[contains(.,'Sort')]/ancestor::button",
    ], timeout=5)
    if not clicked:
        return

    random_sleep(0.4, 0.8)
    # Pilih "Terbaru" / "Newest"
    click_first(driver, [
        "//*[@role='menu']//*[contains(.,'Terbaru')]/ancestor::*[@role='menuitemradio' or @role='menuitem']",
        "//*[@role='menu']//*[contains(.,'Newest')]/ancestor::*[@role='menuitemradio' or @role='menuitem']",
    ], timeout=5)
    random_sleep(0.5, 1.0)


def expand_more_buttons(driver, container):
    """Klik 'Lainnya/More' pada review yang sudah termuat."""
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
                    ActionChains(driver).move_to_element(b).pause(random.uniform(0.05, 0.15)).click().perform()
                    time.sleep(random.uniform(0.05, 0.1))
                except Exception:
                    pass
        except Exception:
            pass


def parse_rating_from_aria(aria_label):
    # contoh: "5,0 bintang" atau "5.0 stars"
    if not aria_label:
        return ""
    m = re.search(r"(\d+(?:[.,]\d+)?)", aria_label)
    if not m:
        return ""
    return m.group(1).replace(",", ".")


def scrape_reviews(url, chromedriver_path, max_reviews=200, headless=False, newest_first=True, scroll_pause=1.2):
    opts = Options()
    
    # User agent untuk terlihat seperti browser biasa
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36")
    
    # Pengaturan bahasa dan notifikasi
    opts.add_argument("--lang=id-ID")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--start-maximized")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    
    # Anti-deteksi bot
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)
    
    # Tambahkan preferences untuk terlihat lebih natural
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False
    }
    opts.add_experimental_option("prefs", prefs)
    
    if headless:
        opts.add_argument("--headless=new")

    # Gunakan webdriver-manager untuk auto-download ChromeDriver yang sesuai
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
    
    # Sembunyikan properti webdriver
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    })
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Tambahkan script untuk menyembunyikan automation
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['id-ID', 'id', 'en-US', 'en']
            });
        '''
    })
    
    wait = WebDriverWait(driver, 25)

    data = []
    seen = set()

    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        random_sleep(2, 4)

        try_handle_consent(driver)

        feed = open_reviews_panel(driver, wait)

        if newest_first:
            sort_reviews_newest(driver)

        last_count = 0
        stagnant = 0

        while len(data) < max_reviews and stagnant < 7:
            expand_more_buttons(driver, feed)

            # Kandidat item review
            items = feed.find_elements(By.CSS_SELECTOR, "div[data-review-id]")
            if not items:
                items = feed.find_elements(By.CSS_SELECTOR, "div[role='article']")

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

                data.append({
                    "name": name,
                    "rating": rating,
                    "date": date,
                    "text": text,
                })
                seen.add(signature)

                if len(data) >= max_reviews:
                    break

            # scroll ke bawah dengan gaya manusia
            human_like_scroll(driver, feed, scroll_pause)

            if len(data) == last_count:
                stagnant += 1
            else:
                stagnant = 0
                last_count = len(data)
            
            print(f"Progress: {len(data)}/{max_reviews} ulasan terkumpul...")

        return data

    finally:
        driver.quit()


def main():
    # ========== KONFIGURASI ==========
    # Ganti URL dan path ChromeDriver di sini
    GOOGLE_MAPS_URL = "https://maps.app.goo.gl/kTrTr5KT2VFwY4Kp9"
    CHROMEDRIVER_PATH = None  # Tidak perlu lagi karena pakai webdriver-manager
    MAX_REVIEWS = 200
    OUTPUT_FILE = "sedudo.csv"
    HEADLESS = False
    NEWEST_FIRST = True
    # =================================

    print(f"Memulai scraping...")
    print(f"URL: {GOOGLE_MAPS_URL}")
    print(f"Max reviews: {MAX_REVIEWS}")
    
    reviews = scrape_reviews(
        url=GOOGLE_MAPS_URL,
        chromedriver_path=CHROMEDRIVER_PATH,
        max_reviews=MAX_REVIEWS,
        headless=HEADLESS,
        newest_first=NEWEST_FIRST,
    )

    df = pd.DataFrame(reviews)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Selesai. Tersimpan: {OUTPUT_FILE} | Total ulasan: {len(df)}")


if __name__ == "__main__":
    main()