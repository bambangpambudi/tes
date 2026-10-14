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

# Selector (dari debug.py — verified)
SEL_EMAIL      = "#email"
SEL_PASSWORD   = "#password"
SEL_FIRST_NAME = "#first_name"
SEL_LAST_NAME  = "#last_name"
SEL_SIGNUP_BTN = "#registration_submit"
SEL_QR_CLOSE   = "#app_qr_modal_close"

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
    opts.add_argument("--window-size=1366,900")
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
def close_modals(driver):
    """Tutup QR modal / cookie banner / overlay yg nutupin form."""
    # 1. QR modal Internshala
    try:
        qr = WebDriverWait(driver, 4).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_QR_CLOSE))
        )
        qr.click()
        print(Fore.GREEN + "[✓] QR modal closed")
        time.sleep(1)
    except Exception:
        print(Fore.YELLOW + "[i] no QR modal")

    # 2. Hapus overlay apapun via JS
    try:
        driver.execute_script("""
            document.querySelectorAll('.modal-backdrop, .modal.show').forEach(e => e.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        """)
    except Exception:
        pass


def safe_fill(driver, selector, value, label="field"):
    """Coba fill normal. Kalau not interactable → fallback JS."""
    try:
        el = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.clear()
        el.send_keys(value)
        print(Fore.GREEN + f"[✓] {label} filled")
        return True
    except Exception:
        # fallback: isi via JS
        ok = driver.execute_script("""
            const el = document.querySelector(arguments[0]);
            if (!el) return false;
            el.focus();
            el.value = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur', {bubbles: true}));
            return true;
        """, selector, value)
        if ok:
            print(Fore.YELLOW + f"[~] {label} filled via JS (fallback)")
        else:
            print(Fore.RED + f"[!] {label} FAILED")
        return ok


def safe_click(driver, selector, label="button"):
    try:
        el = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.click()
        print(Fore.GREEN + f"[✓] {label} clicked")
        return True
    except Exception:
        ok = driver.execute_script("""
            const el = document.querySelector(arguments[0]);
            if (!el) return false;
            el.click();
            return true;
        """, selector)
        if ok:
            print(Fore.YELLOW + f"[~] {label} clicked via JS")
        return ok


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


# ============================================================
#  SIGNUP
# ============================================================
def signup(driver, email):
    print(Fore.CYAN + "[*] buka halaman signup...")
    driver.get(SIGNUP_URL)
    time.sleep(WAIT_LONG)

    close_modals(driver)

    # split nama
    parts = NAME.split(maxsplit=1)
    first_name = parts[0]
    last_name  = parts[1] if len(parts) > 1 else ""

    print(Fore.CYAN + f"[*] isi form untuk {email}...")
    safe_fill(driver, SEL_EMAIL,      email,      "email")
    time.sleep(0.7)
    safe_fill(driver, SEL_PASSWORD,   PASSWORD,   "password")
    time.sleep(0.7)
    safe_fill(driver, SEL_FIRST_NAME, first_name, "first_name")
    time.sleep(0.7)
    safe_fill(driver, SEL_LAST_NAME,  last_name,  "last_name")
    time.sleep(0.7)

    # screenshot sebelum submit (opsional)
    driver.save_screenshot("before_submit.png")

    print(Fore.CYAN + "[*] submit...")
    safe_click(driver, SEL_SIGNUP_BTN, "signup button")
    time.sleep(WAIT_LONG)

    current = driver.current_url
    print(Fore.YELLOW + f"[i] URL sekarang: {current}")

    page = driver.page_source.lower()

    if "already" in page or "exists" in page:
        print(Fore.RED + "[!] email sudah terdaftar.")
        return "already_exists"
    if "verify" in page or "verification" in page or "verify_email" in current:
        print(Fore.GREEN + "[✓] registrasi berhasil — cek email buat verifikasi.")
        return "verify_email"
    if "dashboard" in current or "student/dashboard" in current:
        print(Fore.GREEN + "[✓] langsung masuk dashboard.")
        return "success"
    if "error" in page or "invalid" in page:
        print(Fore.RED + "[!] ada error di form.")
        return "error"

    return "unknown"


# ============================================================
#  PROFILE FILLER (kalau langsung dashboard)
# ============================================================
def fill_profile(driver):
    print(Fore.CYAN + "[*] isi profil...")
    time.sleep(WAIT_LONG)

    try:
        # phone
        try:
            phone = driver.find_element(By.CSS_SELECTOR, "input[name='phone'], #phone")
            phone.clear()
            phone.send_keys(PHONE)
            time.sleep(0.5)
        except Exception:
            pass

        # city
        try:
            city_select = Select(driver.find_element(By.CSS_SELECTOR, "select[name='city'], #city"))
            city_select.select_by_visible_text("Mumbai")
        except Exception:
            try:
                city_input = driver.find_element(By.CSS_SELECTOR, "input[name='city'], #city")
                city_input.clear()
                city_input.send_keys(CITY)
            except Exception:
                pass

        # gender
        try:
            gender = Select(driver.find_element(By.CSS_SELECTOR, "select[name='gender']"))
            gender.select_by_visible_text("Male")
        except Exception:
            pass

        # user type
        try:
            candidate = Select(driver.find_element(By.CSS_SELECTOR, "select[name='user_type']"))
            candidate.select_by_visible_text("Fresher")
        except Exception:
            pass

        print(Fore.GREEN + "[✓] profil dasar terisi.")

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
