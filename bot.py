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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

init(autoreset=True)

# ============================================================
#  CONFIG — Indian data
# ============================================================
SIGNUP_URL = "https://internshala.com/registration/student"

PASSWORD  = "Dermaga07"
NAME      = "Arya Rahman"
PHONE     = "9876543210"
CITY      = "Mumbai"
GENDER    = "Male"
USER_TYPE = "Fresher"
LANGUAGES = ["English", "Hindi"]

# ============================================================
#  CONFIG — Education & Preferences
# ============================================================
COLLEGE_NAME   = "University of Mumbai"
DEGREE         = "B.Tech"
STREAM         = "Computer Science"
START_YEAR     = "2022"
END_YEAR       = "2026"

INTEREST_AREAS = ["Web Development", "Software Development", "Data Science"]
WORK_TYPE      = "Internships"
WORK_MODE      = "Work from home"

WAIT_SHORT = 2
WAIT_LONG  = 5

OUTPUT_JSON = "output/accounts.json"


# ============================================================
#  DRIVER (Persis kode awal)
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
#  LOW-LEVEL HELPERS (Kode Awal untuk Signup + Helper Baru untuk Onboarding)
# ============================================================
def close_modals(driver):
    try:
        qr = WebDriverWait(driver, 4).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#app_qr_modal_close"))
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


def js_fill(driver, selector, value, label="field"):
    """Persis fungsi js_fill awal Anda yang berhasil di halaman Signup & OTP."""
    result = driver.execute_script("""
        const sel = arguments[0], val = arguments[1];
        const el = document.querySelector(sel);
        if (!el) return null;
        el.scrollIntoView({block:'center'});
        el.focus();
        el.value = val;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
        return el.value;
    """, selector, value)
    if result is not None:
        print(Fore.GREEN + f"[✓] {label} = {result}")
        return True
    print(Fore.RED + f"[!] {label} NOT FOUND ({selector})")
    return False


def fill_input_onboarding(driver, selectors, value, label="field"):
    """
    Khusus halaman Onboarding (Personal Details / Education):
    Menggabungkan send_keys + Native Setter agar form modern/React terisi penuh.
    """
    el = driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim());
        let fallback = null;
        for (const s of sels) {
            for (const n of document.querySelectorAll(s)) {
                if (!fallback) fallback = n;
                if (n.offsetParent !== null && !n.disabled) return n;
            }
        }
        return fallback;
    """, selectors)

    if not el:
        print(Fore.RED + f"[!] {label} NOT FOUND ({selectors})")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        el.click()
        el. send_keys(Keys.CONTROL + "a")
        el.send_keys(Keys.BACKSPACE)
        el.send_keys(value)
    except Exception:
        pass

    driver.execute_script("""
        const el = arguments[0], val = arguments[1];
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        if (setter) setter.call(el, val);
        else el.value = val;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
    """, el, value)

    print(Fore.GREEN + f"[✓] {label} = {value}")
    return True


def fill_autocomplete_onboarding(driver, selectors, text_value, label="autocomplete"):
    """
    Khusus field Autocomplete di Onboarding (seperti #current_city, College, Degree, Stream).
    Mengetik karakter satu per satu lalu mengeklik opsi yang muncul di dropdown.
    """
    el = driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim());
        let fallback = null;
        for (const s of sels) {
            for (const n of document.querySelectorAll(s)) {
                if (!fallback) fallback = n;
                if (n.offsetParent !== null && !n.disabled) return n;
            }
        }
        return fallback;
    """, selectors)

    if not el:
        print(Fore.YELLOW + f"[~] {label} tidak ditemukan ({selectors})")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
        time.sleep(0.3)
        el.clear()

        for ch in text_value:
            el.send_keys(ch)
            time.sleep(0.08)

        time.sleep(1.8)  # Tunggu daftar autocomplete muncul

        clicked = driver.execute_script("""
            const val = arguments[0].toLowerCase();
            const items = Array.from(document.querySelectorAll(
                '.ui-menu-item, .ui-menu-item-wrapper, .autocomplete-suggestion, .pac-item, ul[role="listbox"] li, .city-dropdown li, .dropdown-menu li, .autocomplete-items div, .chosen-results li'
            ));
            for (const item of items) {
                if (item.offsetParent !== null && item.textContent.toLowerCase().includes(val)) {
                    item.click();
                    return item.textContent.trim();
                }
            }
            return null;
        """, text_value)

        if clicked:
            print(Fore.GREEN + f"[✓] {label} dipilih dari dropdown: {clicked}")
            return True
        else:
            el.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.3)
            el.send_keys(Keys.ENTER)
            print(Fore.YELLOW + f"[~] {label} dipilih via ARROW_DOWN + ENTER: {text_value}")
            return True
    except Exception as e:
        print(Fore.YELLOW + f"[~] Fallback JS untuk {label}: {e}")
        return fill_input_onboarding(driver, selectors, text_value, label)


def click_chip(driver, text, label=None):
    """
    Klik chip/button/label berdasarkan teks.
    Kompatibel dengan chip biasa maupun chip bertanda '+' (misal '+ English') atau radio label.
    """
    label = label or text
    result = driver.execute_script(r"""
        const rawTarget = arguments[0].toLowerCase().trim();
        const target = rawTarget.replace(/[^a-z0-9]+/g, '');
        const els = Array.from(document.querySelectorAll(
            'button, a, div, span, label, li, input[type="button"], input[type="submit"]'
        ));
        const exact = [];
        const partial = [];

        for (const el of els) {
            if (el.offsetParent === null) continue;
            let raw = (el.textContent || el.value || '').trim();
            if (!raw || raw.length > 50) continue;

            let t = raw.toLowerCase().replace(/[^a-z0-9]+/g, '');
            if (!t) continue;

            if (t === target) {
                exact.push({el, len: raw.length, text: raw});
            } else if (raw.toLowerCase().includes(rawTarget) && raw.length <= rawTarget.length + 6) {
                partial.push({el, len: raw.length, text: raw});
            }
        }

        const candidates = exact.length ? exact : partial;
        if (!candidates.length) return null;

        candidates.sort((a, b) => a.len - b.len);
        let chosen = candidates[0].el;

        // Jika elemen terdalam adalah <span> di dalam <label> atau <button>, klik juga parent-nya
        const parentClickable = chosen.closest('label, button, a, [role="button"]');
        chosen.scrollIntoView({block: 'center'});
        chosen.click();
        if (parentClickable && parentClickable !== chosen) {
            parentClickable.click();
        }
        return candidates[0].text;
    """, text)
    if result:
        print(Fore.GREEN + f"[✓] {label} clicked (matched: {result!r})")
        return True
    print(Fore.RED + f"[!] {label} NOT FOUND")
    return False


def select_dropdown_or_chip(driver, selectors, value, label="dropdown"):
    """Pilih opsi dari <select> atau isi sebagai input/chip."""
    selected = driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim());
        const val = arguments[1].toLowerCase();
        for (const s of sels) {
            const el = document.querySelector(s);
            if (el && el.tagName === 'SELECT') {
                for (const opt of el.options) {
                    if (opt.text.toLowerCase().includes(val) || opt.value.toLowerCase() === val) {
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        return opt.text;
                    }
                }
            }
        }
        return null;
    """, selectors, str(value))

    if selected:
        print(Fore.GREEN + f"[✓] {label} (select) = {selected}")
        return True

    if fill_autocomplete_onboarding(driver, selectors, str(value), label):
        return True

    return click_chip(driver, str(value), label)


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


# ============================================================
#  IMAP (Persis kode awal)
# ============================================================
def fetch_otp_from_gmail(gmail_user, gmail_app_pass, sender="internshala",
                         wait_seconds=90):
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
            _, data = mail.search(None, f'(UNSEEN FROM "{sender}")')
            ids = data[0].split()
            if ids:
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

                otp_match = re.search(r"\b(\d{6})\b", body)
                link_match = re.search(
                    r'https?://[^\s"\'<>]*(?:verify|confirm|activation)[^\s"\'<>]*',
                    body
                )

                otp = otp_match.group(1) if otp_match else None
                link = link_match.group(0) if link_match else None

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
#  VERIFIKASI (Persis kode awal)
# ============================================================
def is_verify_page(driver):
    url = driver.current_url.lower()
    page = driver.page_source.lower()
    keywords_url = ["verify", "verification", "otp", "confirm"]
    keywords_page = ["enter otp", "verification code", "verify your email",
                     "we have sent", "check your inbox"]
    return any(k in url for k in keywords_url) or any(k in page for k in keywords_page)


def handle_verification(driver, email, mode, gmail_user=None, gmail_pass=None):
    print(Fore.CYAN + "\n[*] halaman verifikasi terdeteksi.")
    driver.save_screenshot("verify_page.png")

    otp = None
    link = None

    if mode == "auto" and gmail_user and gmail_pass:
        print(Fore.CYAN + "[*] ambil OTP dari Gmail...")
        otp, link = fetch_otp_from_gmail(gmail_user, gmail_pass)
        if link:
            print(Fore.GREEN + f"[✓] link: {link[:80]}...")
            driver.get(link)
            time.sleep(WAIT_LONG)
            return True
        if otp:
            print(Fore.GREEN + f"[✓] OTP: {otp}")

    if not otp:
        print(Fore.YELLOW + "\n[i] Cek email. Copy OTP 6 digit atau paste link.")
        user_input = input(Fore.CYAN + "OTP / Link: ").strip()
        if user_input.startswith("http"):
            driver.get(user_input)
            time.sleep(WAIT_LONG)
            return True
        otp = user_input

    print(Fore.CYAN + f"[*] isi OTP: {otp}")
    ok = js_fill(
        driver,
        "input[name='otp'], input#otp, input[name='verification_code'], input[type='text'], input[type='number']",
        otp,
        "otp"
    )
    if not ok:
        print(Fore.RED + "[!] gagal isi OTP")
        return False

    time.sleep(1)
    click_chip(driver, "verify")
    click_chip(driver, "submit")
    time.sleep(WAIT_LONG)

    if is_verify_page(driver):
        print(Fore.RED + "[!] masih di halaman verifikasi.")
        return False

    print(Fore.GREEN + "[✓] verifikasi berhasil.")
    return True


# ============================================================
#  ONBOARDING — Personal Details, Education, & Preferences
# ============================================================
def click_next_button(driver, label="Next"):
    """Klik tombol Next / Submit / Save di halaman onboarding."""
    clicked = driver.execute_script("""
        const btns = document.querySelectorAll(
            '#personal_details_submit, #education_submit, #preferences_submit, button[type="submit"], input[type="submit"], .btn-primary, button'
        );
        for (const b of btns) {
            if (b.offsetParent !== null && !b.disabled) {
                const txt = (b.textContent || b.value || '').trim();
                if (/next|continue|save|submit|done|find/i.test(txt)) {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return txt;
                }
            }
        }
        return null;
    """)
    if clicked:
        print(Fore.GREEN + f"[✓] {label} diklik ({clicked!r})")
        return True
    return click_chip(driver, "next", label)


def fill_education(driver):
    print(Fore.CYAN + "\n[*] mengisi halaman Education...")
    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("education_start.png")

    click_chip(driver, "Graduation", "Education Type (Graduation)")
    time.sleep(0.5)

    fill_autocomplete_onboarding(
        driver,
        "#college, input[name='college'], input[placeholder*='college' i], input[placeholder*='institute' i]",
        COLLEGE_NAME,
        "College"
    )
    time.sleep(0.5)

    if not fill_autocomplete_onboarding(
        driver,
        "#degree, input[name='degree'], input[placeholder*='degree' i]",
        DEGREE,
        "Degree"
    ):
        click_chip(driver, DEGREE, "Degree Chip")
    time.sleep(0.5)

    if not fill_autocomplete_onboarding(
        driver,
        "#stream, input[name='stream'], input[placeholder*='stream' i], input[placeholder*='specialization' i]",
        STREAM,
        "Stream"
    ):
        click_chip(driver, STREAM, "Stream Chip")
    time.sleep(0.5)

    select_dropdown_or_chip(
        driver,
        "#start_year, select[name='start_year'], input[name='start_year'], input[placeholder*='start year' i]",
        START_YEAR,
        "Start Year"
    )
    time.sleep(0.4)

    select_dropdown_or_chip(
        driver,
        "#end_year, select[name='end_year'], input[name='end_year'], input[placeholder*='end year' i], input[placeholder*='graduation year' i]",
        END_YEAR,
        "End Year"
    )
    time.sleep(0.5)

    driver.save_screenshot("education_filled.png")
    click_next_button(driver, "Next (Education)")
    time.sleep(WAIT_LONG)


def fill_preferences(driver):
    print(Fore.CYAN + "\n[*] mengisi halaman Preferences / Interests...")
    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("preferences_start.png")

    click_chip(driver, WORK_TYPE, f"Looking for: {WORK_TYPE}")
    time.sleep(0.5)

    click_chip(driver, WORK_MODE, f"Work Mode: {WORK_MODE}")
    time.sleep(0.5)

    for interest in INTEREST_AREAS:
        if not click_chip(driver, interest, f"Interest Chip: {interest}"):
            fill_autocomplete_onboarding(
                driver,
                "input[placeholder*='interest' i], input[placeholder*='category' i], input[placeholder*='search' i], input[placeholder*='profile' i], #preferences_search",
                interest,
                f"Interest Search: {interest}"
            )
        time.sleep(0.5)

    fill_autocomplete_onboarding(
        driver,
        "input[placeholder*='city' i], input[placeholder*='location' i], #preferred_city",
        CITY,
        "Preferred City"
    )
    time.sleep(0.5)

    driver.save_screenshot("preferences_filled.png")
    click_next_button(driver, "Save/Next (Preferences)")
    time.sleep(WAIT_LONG)
    driver.save_screenshot("onboarding_complete.png")
    print(Fore.GREEN + f"[✓] Onboarding selesai! URL akhir: {driver.current_url}")


def fill_onboarding(driver):
    print(Fore.CYAN + "\n[*] mulai onboarding profil (Personal Details)...")
    time.sleep(WAIT_LONG)
    close_modals(driver)
    driver.save_screenshot("onboarding_start.png")
    print(Fore.YELLOW + f"[i] URL: {driver.current_url}")

    # ---- PHONE ----
    fill_input_onboarding(
        driver,
        "#phone, #phone_primary, input[name='phone'], input[name='phone_primary'], input[type='tel']",
        PHONE,
        "phone"
    )
    time.sleep(0.5)

    # ---- CITY (Ketik & pilih dari dropdown autocomplete) ----
    fill_autocomplete_onboarding(
        driver,
        "#current_city, input[name='current_city'], input[placeholder*='city' i]",
        CITY,
        "city"
    )
    time.sleep(0.5)

    # ---- GENDER (chip button) ----
    click_chip(driver, GENDER, "gender")
    time.sleep(0.5)

    # ---- USER TYPE (chip button) ----
    if not click_chip(driver, USER_TYPE, "user type"):
        click_chip(driver, "College student", "user type fallback")
    time.sleep(0.5)

    # ---- LANGUAGES (chip button) ----
    for lang in LANGUAGES:
        click_chip(driver, lang, f"language: {lang}")
        time.sleep(0.3)

    driver.save_screenshot("onboarding_filled.png")

    # ---- NEXT ----
    print(Fore.CYAN + "[*] klik Next...")
    click_next_button(driver, "Next (Personal Details)")
    time.sleep(WAIT_LONG)

    driver.save_screenshot("onboarding_done.png")
    print(Fore.YELLOW + f"[i] URL setelah Next: {driver.current_url}")

    # ---- Lanjut otomatis ke Education & Preferences ----
    for step in range(3):
        curr_url = driver.current_url.lower()
        page_src = driver.page_source.lower()

        if "dashboard" in curr_url or ("internships" in curr_url and "preference" not in curr_url):
            print(Fore.GREEN + "[✓] Sudah masuk ke Dashboard!")
            break
        elif any(k in curr_url for k in ["education", "academic", "qualification", "degree"]) or "college" in page_src:
            fill_education(driver)
        elif any(k in curr_url for k in ["preference", "interest", "career"]) or "areas of interest" in page_src or "looking for" in page_src:
            fill_preferences(driver)
        else:
            fill_education(driver)
            fill_preferences(driver)
            break

    return True


# ============================================================
#  SIGNUP (Persis kode awal Anda yang sukses mengirim OTP)
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
    js_fill(driver, "#email",      email,      "email")
    time.sleep(0.5)
    js_fill(driver, "#password",   PASSWORD,   "password")
    time.sleep(0.5)
    js_fill(driver, "#first_name", first_name, "first_name")
    time.sleep(0.5)
    js_fill(driver, "#last_name",  last_name,  "last_name")
    time.sleep(0.5)

    driver.save_screenshot("before_submit.png")

    print(Fore.CYAN + "[*] submit...")
    try:
        driver.find_element(By.CSS_SELECTOR, "#registration_submit").click()
    except Exception:
        driver.execute_script(
            "document.querySelector('#registration_submit').click();"
        )
    time.sleep(WAIT_LONG)

    current = driver.current_url
    print(Fore.YELLOW + f"[i] URL: {current}")
    driver.save_screenshot("after_submit.png")

    page = driver.page_source.lower()

    if is_verify_page(driver):
        print(Fore.GREEN + "[✓] masuk halaman verifikasi.")
        return "verify_email"
    if "dashboard" in current or "onboarding" in current or "personal_details" in current:
        print(Fore.GREEN + "[✓] langsung masuk onboarding/dashboard.")
        return "success"

    # Cek pesan error spesifik di form jika tertahan di halaman registrasi
    err_msg = driver.execute_script("""
        const els = document.querySelectorAll('.help-block, .error, #email-error, .toast-message, .alert');
        return Array.from(els).map(e => e.textContent.trim()).filter(Boolean).join(' | ');
    """) or ""
    if err_msg:
        print(Fore.RED + f"[!] Pesan dari web: {err_msg}")
        if "already" in err_msg.lower() or "exist" in err_msg.lower() or "registered" in err_msg.lower():
            return "already_exists"
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
        "phone": PHONE,
        "city": CITY,
        "college": COLLEGE_NAME,
        "degree": DEGREE,
        "stream": STREAM,
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
    print(Fore.CYAN + "   INTERNSHALA SEMI-AUTO SIGNUP (India)")
    print(Fore.CYAN + f"   Nama      : {NAME}")
    print(Fore.CYAN + f"   Password  : {PASSWORD}")
    print(Fore.CYAN + f"   Phone     : +91 {PHONE}")
    print(Fore.CYAN + f"   City      : {CITY}")
    print(Fore.CYAN + f"   Gender    : {GENDER}")
    print(Fore.CYAN + f"   Type      : {USER_TYPE}")
    print(Fore.CYAN + f"   Education : {DEGREE} ({STREAM}) - {COLLEGE_NAME}")
    print(Fore.CYAN + "=" * 55)

    headless = input("Headless? (y/n, default y): ").strip().lower() != "n"

    print(Fore.CYAN + "\nMode verifikasi:")
    print("  1. Manual")
    print("  2. Auto IMAP Gmail")
    vmode = input("Pilih (1/2, default 1): ").strip() or "1"

    gmail_user = gmail_pass = None
    if vmode == "2":
        gmail_user = input("Gmail address: ").strip()
        gmail_pass = input("Gmail App Password: ").strip()
        vmode = "auto"
    else:
        vmode = "manual"

    driver = build_driver(headless=headless)

    try:
        while True:
            email = input(Fore.YELLOW + "\nEmail (atau 'q'): ").strip()
            if email.lower() == "q":
                break
            if not is_valid_email(email):
                print(Fore.RED + "[!] email gak valid.")
                continue

            print(Fore.CYAN + f"\n--- proses: {email} ---")
            result = signup(driver, email)

            if result == "verify_email":
                if handle_verification(driver, email, vmode, gmail_user, gmail_pass):
                    print(Fore.GREEN + "[✓] verified. lanjut onboarding...")
                    fill_onboarding(driver)
                    result = "verified"
                else:
                    result = "verify_failed"
            elif result == "success":
                fill_onboarding(driver)
                result = "verified"

            log_account(email, result)
            print(Fore.GREEN + f"[✓] status akhir: {result}")

            if input(Fore.YELLOW + "\nLanjut? (y/n): ").strip().lower() != "y":
                break

        print(Fore.GREEN + f"\n[✓] selesai. log: {OUTPUT_JSON}")

    except Exception as e:
        print(Fore.RED + f"[!] error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
