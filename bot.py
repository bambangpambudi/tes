import os
import re
import json
import time
import imaplib
import email as email_lib

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

# Selector signup
SEL_EMAIL      = "#email"
SEL_PASSWORD   = "#password"
SEL_FIRST_NAME = "#first_name"
SEL_LAST_NAME  = "#last_name"
SEL_SIGNUP_BTN = "#registration_submit"
SEL_QR_CLOSE   = "#app_qr_modal_close"

# Selector verifikasi (kemungkinan — kalau salah, debug dulu)
SEL_OTP_INPUT  = "input[name='otp'], input#otp, input[name='verification_code']"
SEL_OTP_SUBMIT = "button#verify_submit, button[type='submit']"

# Selector onboarding/profil
SEL_PHONE      = "input[name='phone'], #phone"
SEL_CITY       = "select[name='city'], #city, input[name='city']"
SEL_GENDER     = "select[name='gender']"
SEL_USER_TYPE  = "select[name='user_type']"
SEL_PROFILE_SUBMIT = "button[type='submit'], #profile_submit"

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
    try:
        qr = WebDriverWait(driver, 4).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, SEL_QR_CLOSE))
        )
        qr.click()
        print(Fore.GREEN + "[✓] QR modal closed")
        time.sleep(1)
    except Exception:
        pass
    try:
        driver.execute_script("""
            document.querySelectorAll('.modal-backdrop, .modal.show').forEach(e => e.remove());
            document.body.classList.remove('modal-open');
            document.body.style.overflow = 'auto';
        """)
    except Exception:
        pass


def safe_fill(driver, selector, value, label="field"):
    try:
        el = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.clear()
        el.send_keys(value)
        print(Fore.GREEN + f"[✓] {label} filled")
        return True
    except Exception:
        ok = driver.execute_script("""
            const el = document.querySelector(arguments[0]);
            if (!el) return false;
            el.focus(); el.value = arguments[1];
            el.dispatchEvent(new Event('input', {bubbles: true}));
            el.dispatchEvent(new Event('change', {bubbles: true}));
            el.dispatchEvent(new Event('blur', {bubbles: true}));
            return true;
        """, selector, value)
        if ok:
            print(Fore.YELLOW + f"[~] {label} filled via JS")
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
            el.click(); return true;
        """, selector)
        if ok:
            print(Fore.YELLOW + f"[~] {label} clicked via JS")
        return ok


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


# ============================================================
#  IMAP — auto-ambil OTP/link dari Gmail
# ============================================================
def fetch_otp_from_gmail(gmail_user, gmail_app_pass, sender="internshala",
                          wait_seconds=90):
    """
    Cek inbox Gmail, cari email dari Internshala, ambil OTP 6 digit
    atau link verifikasi. Cek tiap 5 detik sampai timeout.
    """
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(gmail_user, gmail_app_pass)
        mail.select("inbox")
    except Exception as e:
        print(Fore.RED + f"[!] IMAP login gagal: {e}")
        return None, None

    elapsed = 0
    while elapsed < wait_seconds:
        try:
            # cari email unread dari internshala
            _, data = mail.search(None, f'(UNSEEN FROM "{sender}")')
            ids = data[0].split()
            if ids:
                # ambil yang terbaru
                _, msg_data = mail.fetch(ids[-1], "(RFC822)")
                msg = email_lib.message_from_bytes(msg_data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(errors="ignore")
                        elif part.get_content_type() == "text/html":
                            body += part.get_payload(decode=True).decode(errors="ignore")
                else:
                    body = msg.get_payload(decode=True).decode(errors="ignore")

                # cari OTP 6 digit
                otp_match = re.search(r"\b(\d{6})\b", body)
                # cari link verifikasi
                link_match = re.search(
                    r'https?://[^\s"\'<>]*(?:verify|confirm|activation)[^\s"\'<>]*',
                    body
                )

                otp = otp_match.group(1) if otp_match else None
                link = link_match.group(0) if link_match else None

                # tandai read
                mail.store(ids[-1], "+FLAGS", "\\Seen")
                mail.logout()
                return otp, link

        except Exception as e:
            print(Fore.YELLOW + f"[~] IMAP error: {e}")

        time.sleep(5)
        elapsed += 5
        print(Fore.YELLOW + f"[i] nunggu email... ({elapsed}s)")

    mail.logout()
    return None, None


# ============================================================
#  VERIFIKASI
# ============================================================
def is_verify_page(driver):
    url = driver.current_url.lower()
    page = driver.page_source.lower()
    keywords_url = ["verify", "verification", "otp", "confirm"]
    keywords_page = ["enter otp", "verification code", "verify your email",
                     "we have sent", "check your inbox"]
    if any(k in url for k in keywords_url):
        return True
    if any(k in page for k in keywords_page):
        return True
    return False


def handle_verification(driver, email, mode, gmail_user=None, gmail_pass=None):
    """
    mode: "manual" | "auto"
    return: True kalau verified, False kalau gagal
    """
    print(Fore.CYAN + "\n[*] halaman verifikasi terdeteksi.")
    driver.save_screenshot("verify_page.png")

    otp = None
    link = None

    # -------- AUTO MODE --------
    if mode == "auto":
        if not gmail_user or not gmail_pass:
            print(Fore.RED + "[!] Gmail creds kosong, fallback ke manual.")
            mode = "manual"
        else:
            print(Fore.CYAN + "[*] ambil OTP dari Gmail...")
            otp, link = fetch_otp_from_gmail(gmail_user, gmail_pass)

            if link:
                print(Fore.GREEN + f"[✓] link verifikasi ditemukan: {link[:80]}...")
                print(Fore.CYAN + "[*] buka link verifikasi...")
                driver.get(link)
                time.sleep(WAIT_LONG)
                return True

            if otp:
                print(Fore.GREEN + f"[✓] OTP ditemukan: {otp}")

    # -------- MANUAL MODE / FALLBACK --------
    if mode == "manual":
        print(Fore.YELLOW + "\n[i] Cek email kamu. Ada OTP atau link verifikasi.")
        print(Fore.YELLOW + "[i] Kalau ada link: copy paste di bawah + Enter.")
        print(Fore.YELLOW + "[i] Kalau ada OTP: ketik 6 digit.")
        user_input = input(Fore.CYAN + "OTP / Link: ").strip()

        if user_input.startswith("http"):
            print(Fore.CYAN + "[*] buka link verifikasi...")
            driver.get(user_input)
            time.sleep(WAIT_LONG)
            return True
        else:
            otp = user_input

    # -------- ISI OTP DI FORM --------
    if otp:
        print(Fore.CYAN + f"[*] isi OTP: {otp}")
        ok = safe_fill(driver, SEL_OTP_INPUT, otp, "otp")
        if not ok:
            # coba beberapa selector alternatif
            for alt in ["input[type='text']", "input[type='number']", "input.form-control"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, alt)
                    el.clear()
                    el.send_keys(otp)
                    print(Fore.GREEN + f"[✓] OTP filled via {alt}")
                    ok = True
                    break
                except Exception:
                    continue
        if not ok:
            print(Fore.RED + "[!] gagal isi OTP, cek verify_page.png")
            return False

        time.sleep(1)
        safe_click(driver, SEL_OTP_SUBMIT, "verify submit")
        time.sleep(WAIT_LONG)

        if is_verify_page(driver):
            print(Fore.RED + "[!] masih di halaman verifikasi — OTP salah / belum expired?")
            return False

        print(Fore.GREEN + "[✓] verifikasi berhasil.")
        return True

    return False


# ============================================================
#  ONBOARDING — setelah verified
# ============================================================
def fill_onboarding(driver):
    """
    Setelah verify, Internshala bawa ke onboarding: isi phone, city, dsb.
    """
    print(Fore.CYAN + "\n[*] mulai onboarding profil...")
    time.sleep(WAIT_LONG)
    driver.save_screenshot("onboarding_start.png")

    # ---- phone ----
    safe_fill(driver, SEL_PHONE, PHONE, "phone")
    time.sleep(0.7)

    # ---- city (dropdown atau input) ----
    try:
        city_el = driver.find_element(By.CSS_SELECTOR, SEL_CITY)
        tag = city_el.tag_name.lower()
        if tag == "select":
            Select(city_el).select_by_visible_text("Mumbai")
            print(Fore.GREEN + "[✓] city dropdown -> Mumbai")
        else:
            city_el.clear()
            city_el.send_keys(CITY)
            print(Fore.GREEN + "[✓] city input -> Mumbai")
    except Exception as e:
        print(Fore.YELLOW + f"[~] city skip: {e}")
    time.sleep(0.7)

    # ---- gender ----
    try:
        Select(driver.find_element(By.CSS_SELECTOR, SEL_GENDER)).select_by_visible_text("Male")
        print(Fore.GREEN + "[✓] gender -> Male")
    except Exception:
        pass

    # ---- user type ----
    try:
        Select(driver.find_element(By.CSS_SELECTOR, SEL_USER_TYPE)).select_by_visible_text("Fresher")
        print(Fore.GREEN + "[✓] user_type -> Fresher")
    except Exception:
        pass

    driver.save_screenshot("onboarding_filled.png")

    # ---- submit ----
    if safe_click(driver, SEL_PROFILE_SUBMIT, "profile submit"):
        time.sleep(WAIT_LONG)
        driver.save_screenshot("onboarding_done.png")
        print(Fore.GREEN + "[✓] onboarding submitted.")
        return True
    return False


# ============================================================
#  SIGNUP
# ============================================================
def signup(driver, email):
    print(Fore.CYAN + "[*] buka halaman signup...")
    driver.get(SIGNUP_URL)
    time.sleep(WAIT_LONG)

    close_modals(driver)

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

    driver.save_screenshot("before_submit.png")

    print(Fore.CYAN + "[*] submit...")
    safe_click(driver, SEL_SIGNUP_BTN, "signup button")
    time.sleep(WAIT_LONG)

    current = driver.current_url
    print(Fore.YELLOW + f"[i] URL sekarang: {current}")
    driver.save_screenshot("after_submit.png")

    page = driver.page_source.lower()

    if "already" in page or "exists" in page:
        print(Fore.RED + "[!] email sudah terdaftar.")
        return "already_exists"

    if is_verify_page(driver):
        print(Fore.GREEN + "[✓] masuk halaman verifikasi.")
        return "verify_email"

    if "dashboard" in current or "student" in current:
        print(Fore.GREEN + "[✓] langsung masuk dashboard.")
        return "success"

    if "error" in page or "invalid" in page:
        print(Fore.RED + "[!] ada error di form.")
        return "error"

    return "unknown"


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

    headless = input("Headless? (y/n, default y): ").strip().lower() != "n"

    # pilih mode verifikasi
    print(Fore.CYAN + "\nMode verifikasi:")
    print("  1. Manual — kamu copy OTP/link dari email")
    print("  2. Auto   — pakai IMAP Gmail (butuh App Password)")
    vmode = input("Pilih (1/2, default 1): ").strip() or "1"

    gmail_user = None
    gmail_pass = None
    if vmode == "2":
        gmail_user = input("Gmail address: ").strip()
        gmail_pass = input("Gmail App Password (16 char): ").strip()
        vmode = "auto"
    else:
        vmode = "manual"

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

            # -------- HANDLE VERIFIKASI --------
            if result == "verify_email":
                if handle_verification(driver, email, vmode, gmail_user, gmail_pass):
                    print(Fore.GREEN + "[✓] verified. lanjut onboarding...")
                    fill_onboarding(driver)
                    result = "verified"
                else:
                    print(Fore.RED + "[!] verifikasi gagal/ketinggalan.")
                    result = "verify_failed"

            # -------- LANGSUNG DASHBOARD --------
            elif result == "success":
                fill_onboarding(driver)
                result = "verified"

            log_account(email, result)
            print(Fore.GREEN + f"[✓] status akhir: {result}")

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
