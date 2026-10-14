import os
import re
import json
import time

from colorama import init, Fore
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

init(autoreset=True)

# ============================================================
#  CONFIG
# ============================================================
SIGNUP_URL = "https://internshala.com/registration/student"

PASSWORD = "Dermaga07"
NAME     = "Arya Rahman"
PHONE    = "081234567890"
CITY     = "Mumbai"

# Selector — SESUAIKAN dengan inspect element Internshala
SEL_EMAIL      = "#email"
SEL_PASSWORD   = "#password"
SEL_NAME       = "#name"
SEL_SIGNUP_BTN = "#signup_submit"

WAIT_SHORT = 2
WAIT_LONG  = 5

OUTPUT_JSON = "output/accounts.json"


# ============================================================
#  DRIVER
# ============================================================
def build_driver(headless=False):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1366,768")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


# ============================================================
#  HELPERS
# ============================================================
def wait_click(driver, selector, timeout=15):
    el = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
    )
    el.click()
    return el


def wait_fill(driver, selector, value, timeout=15):
    el = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
    )
    el.clear()
    el.send_keys(value)
    return el


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


# ============================================================
#  SIGNUP
# ============================================================
def signup(driver, email):
    print(Fore.CYAN + "[*] buka halaman signup...")
    driver.get(SIGNUP_URL)
    time.sleep(WAIT_LONG)

    print(Fore.CYAN + f"[*] isi form untuk {email}...")
    wait_fill(driver, SEL_EMAIL, email)
    time.sleep(0.8)
    wait_fill(driver, SEL_PASSWORD, PASSWORD)
    time.sleep(0.8)
    wait_fill(driver, SEL_NAME, NAME)
    time.sleep(0.8)

    print(Fore.CYAN + "[*] submit...")
    wait_click(driver, SEL_SIGNUP_BTN)
    time.sleep(WAIT_LONG)

    current = driver.current_url
    print(Fore.YELLOW + f"[i] URL sekarang: {current}")

    page = driver.page_source.lower()

    if "verify" in page or "verification" in page:
        print(Fore.GREEN + "[✓] registrasi berhasil — cek email buat verifikasi.")
        return "verify_email"
    if "already" in page or "exists" in page:
        print(Fore.RED + "[!] email sudah terdaftar.")
        return "already_exists"
    if "error" in page or "invalid" in page:
        print(Fore.RED + "[!] ada error di form.")
        return "error"
    if "dashboard" in current or "student" in current:
        print(Fore.GREEN + "[✓] langsung masuk dashboard.")
        return "success"

    return "unknown"


# ============================================================
#  PROFILE FILLER
# ============================================================
def fill_profile(driver):
    print(Fore.CYAN + "[*] isi profil...")
    time.sleep(WAIT_LONG)

    try:
        name_input = driver.find_element(By.CSS_SELECTOR, "input[name='name'], #name")
        name_input.clear()
        name_input.send_keys(NAME)
        time.sleep(0.5)

        phone_input = driver.find_element(By.CSS_SELECTOR, "input[name='phone'], #phone")
        phone_input.clear()
        phone_input.send_keys(PHONE)
        time.sleep(0.5)

        try:
            city_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name='city'], #city"))
            city_select.select_by_visible_text("Mumbai")
            print(Fore.GREEN + "[✓] city (dropdown) -> Mumbai")
        except Exception:
            city_input = driver.find_element(By.CSS_SELECTOR, "input[name='city'], #city")
            city_input.clear()
            city_input.send_keys(CITY)
            print(Fore.GREEN + "[✓] city (input) -> Mumbai")
        time.sleep(0.5)

        try:
            gender = Select(driver.find_element(By.CSS_SELECTOR, "select[name='gender']"))
            gender.select_by_visible_text("Male")
        except Exception:
            pass

        try:
            candidate = Select(driver.find_element(By.CSS_SELECTOR, "select[name='user_type']"))
            candidate.select_by_visible_text("Fresher")
        except Exception:
            pass

        print(Fore.GREEN + "[✓] profil dasar terisi.")
        time.sleep(WAIT_SHORT)

        submit = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #profile_submit")
        submit.click()
        time.sleep(WAIT_LONG)

        print(Fore.GREEN + "[✓] profil disubmit.")
        return True

    except Exception as e:
        print(Fore.RED + f"[!] gagal isi profil: {e}")
        return False


# ============================================================
#  LOGGING
# ============================================================
def log_account(email, status):
    os.makedirs("output", exist_ok=True)
    data = []
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    data.append({
        "email": email,
        "name": NAME,
        "password": PASSWORD,
        "city": CITY,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
#  MAIN
# ============================================================
def main():
    print(Fore.CYAN + "=" * 55)
    print(Fore.CYAN + "   INTERNSHALA SEMI-AUTO SIGNUP")
    print(Fore.CYAN + f"   Nama     : {NAME}")
    print(Fore.CYAN + f"   Password : {PASSWORD}")
    print(Fore.CYAN + f"   City     : {CITY}")
    print(Fore.CYAN + "=" * 55)

    # Di server/container: WAJIB headless
    headless_input = input("Headless? (y/n, default y): ").strip().lower()
    headless = headless_input != "n"

    driver = build_driver(headless=headless)

    try:
        while True:
            email = input(Fore.YELLOW + "\nEmail (atau 'q' buat keluar): ").strip()

            if email.lower() == "q":
                break
            if not is_valid_email(email):
                print(Fore.RED + "[!] format email gak valid.")
                continue

            print(Fore.CYAN + f"\n--- proses: {email} ---")
            result = signup(driver, email)

            if result == "success":
                fill_profile(driver)

            log_account(email, result)
            print(Fore.GREEN + f"[✓] status: {result}")

            lanjut = input(Fore.YELLOW + "\nLanjut akun berikutnya? (y/n): ").strip().lower()
            if lanjut != "y":
                break

        print(Fore.GREEN + f"\n[✓] selesai. log: {OUTPUT_JSON}")

    except Exception as e:
        print(Fore.RED + f"[!] error: {e}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
