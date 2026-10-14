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
#  CONFIG — Personal Details (Indian Data)
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
WORK_TYPE      = "Internships"       # "Internships" atau "Jobs"
WORK_MODE      = "Work from home"    # "Work from home" atau "In-office"

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
#  LOW-LEVEL HELPERS
# ============================================================
def close_modals(driver):
    try:
        qr = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#app_qr_modal_close"))
        )
        qr.click()
        print(Fore.GREEN + "[✓] QR modal closed")
        time.sleep(0.5)
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
    """
    Isi input via Native Setter (kompatibel penuh dengan React/Vue)
    dengan fallback ke Selenium send_keys jika diperlukan.
    """
    el = driver.execute_script("""
        const selectors = arguments[0].split(',').map(s => s.trim());
        for (const sel of selectors) {
            const nodes = document.querySelectorAll(sel);
            for (const n of nodes) {
                if (n.offsetParent !== null && !n.disabled) return n;
            }
        }
        return null;
    """, selector)

    if not el:
        print(Fore.RED + f"[!] {label} NOT FOUND ({selector})")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        el.click()
        el.clear()
        el.send_keys(value)
    except Exception:
        pass

    driver.execute_script("""
        const el = arguments[0], val = arguments[1];
        const nativeSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        ).set;
        if (nativeSetter) {
            nativeSetter.call(el, val);
        } else {
            el.value = val;
        }
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
    """, el, value)

    print(Fore.GREEN + f"[✓] {label} = {value}")
    return True


def fill_city_autocomplete(driver, city_name):
    """
    Khusus untuk field City di Internshala yang wajib klik dari dropdown autocomplete.
    """
    selectors = "#current_city, input[name='current_city'], input[placeholder*='City' i], input[placeholder*='location' i]"
    el = driver.execute_script("""
        const nodes = document.querySelectorAll(arguments[0]);
        for (const n of nodes) {
            if (n.offsetParent !== null && !n.disabled) return n;
        }
        return null;
    """, selectors)

    if not el:
        print(Fore.RED + "[!] Field City tidak ditemukan!")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
        time.sleep(0.3)
        el.clear()

        for ch in city_name:
            el.send_keys(ch)
            time.sleep(0.08)

        time.sleep(1.8)

        clicked = driver.execute_script("""
            const city = arguments[0].toLowerCase();
            const items = Array.from(document.querySelectorAll(
                '.ui-menu-item, .ui-menu-item-wrapper, .autocomplete-suggestion, .pac-item, ul[role="listbox"] li, .city-dropdown li, .dropdown-menu li, .autocomplete-items div'
            ));
            for (const item of items) {
                if (item.offsetParent !== null && item.textContent.toLowerCase().includes(city)) {
                    item.click();
                    return item.textContent.trim();
                }
            }
            return null;
        """, city_name)

        if clicked:
            print(Fore.GREEN + f"[✓] City dipilih dari dropdown: {clicked}")
            return True
        else:
            el.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.3)
            el.send_keys(Keys.ENTER)
            print(Fore.YELLOW + f"[~] City diisi via ARROW_DOWN + ENTER: {city_name}")
            return True

    except Exception as e:
        print(Fore.RED + f"[!] Gagal isi city: {e}")
        return False


def fill_autocomplete_generic(driver, selectors, text_value, label="autocomplete"):
    """
    Mengisi input autocomplete (seperti College, Degree, Stream, atau Interest)
    dan memilih item pertama yang cocok dari dropdown yang muncul.
    """
    el = driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim());
        for (const s of sels) {
            for (const n of document.querySelectorAll(s)) {
                if (n.offsetParent !== null && !n.disabled) return n;
            }
        }
        return null;
    """, selectors)

    if not el:
        print(Fore.YELLOW + f"[~] {label} input tidak ditemukan ({selectors})")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        el.click()
        time.sleep(0.3)
        el.clear()

        for ch in text_value:
            el.send_keys(ch)
            time.sleep(0.06)

        time.sleep(1.5)

        clicked = driver.execute_script("""
            const val = arguments[0].toLowerCase();
            const items = Array.from(document.querySelectorAll(
                '.ui-menu-item, .ui-menu-item-wrapper, .autocomplete-suggestion, ul[role="listbox"] li, .dropdown-menu li, .autocomplete-items div, .chosen-results li'
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
            time.sleep(0.2)
            el.send_keys(Keys.ENTER)
            print(Fore.GREEN + f"[✓] {label} diisi via Enter: {text_value}")
            return True
    except Exception as e:
        print(Fore.RED + f"[!] Gagal isi {label}: {e}")
        return False


def click_chip(driver, text, label=None):
    """
    Klik chip/radio/label/button berdasarkan teks.
    Mendukung exact match maupun teks dengan simbol '+' (seperti '+ English').
    """
    label = label or text
    result = driver.execute_script(r"""
        const rawTarget = arguments[0].toLowerCase().trim();
        const cleanTarget = rawTarget.replace(/[^a-z0-9]+/g, '');
        
        const els = Array.from(document.querySelectorAll(
            'button, a, label, span, div, li, input[type="button"], input[type="submit"]'
        ));
        
        const exactCandidates = [];
        const partialCandidates = [];

        for (const el of els) {
            if (el.offsetParent === null) continue;
            
            let rawText = (el.textContent || el.value || '').trim().toLowerCase();
            if (!rawText || rawText.length > 45) continue;

            let cleanText = rawText.replace(/[^a-z0-9]+/g, '');
            if (!cleanText) continue;

            const rect = el.getBoundingClientRect();
            if (rect.width < 10 || rect.height < 10) continue;

            const childCount = el.children.length;

            if (cleanText === cleanTarget) {
                exactCandidates.push({el, childCount, len: rawText.length, text: rawText});
            } else if (rawText.includes(rawTarget) && rawText.length <= rawTarget.length + 6) {
                partialCandidates.push({el, childCount, len: rawText.length, text: rawText});
            }
        }

        const pool = exactCandidates.length ? exactCandidates : partialCandidates;
        if (!pool.length) return null;

        pool.sort((a, b) => (a.childCount - b.childCount) || (a.len - b.len));
        
        let targetEl = pool[0].el;
        const clickableParent = targetEl.closest('label, button, a, [role="button"]');
        const finalEl = clickableParent || targetEl;

        finalEl.scrollIntoView({block: 'center'});
        finalEl.click();
        return pool[0].text;
    """, text)

    if result:
        print(Fore.GREEN + f"[✓] {label} clicked (matched: {result!r})")
        return True
    print(Fore.RED + f"[!] {label} NOT FOUND")
    return False


def select_dropdown_or_chip(driver, selectors, value, label="dropdown"):
    """
    Mencoba memilih opsi dari <select> standar, input text, atau klik chip/dropdown item.
    """
    selected = driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim());
        const val = arguments[1].toLowerCase();
        for (const s of sels) {
            const el = document.querySelector(s);
            if (el && el.tagName === 'SELECT' && el.offsetParent !== null) {
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

    if js_fill(driver, selectors, str(value), label):
        return True

    return click_chip(driver, str(value), label)


def click_next_or_save(driver, step_name="step"):
    """Klik tombol Next / Save / Continue / Submit di akhir form."""
    clicked = driver.execute_script("""
        const btns = document.querySelectorAll(
            'button[type="submit"], input[type="submit"], #personal_details_submit, #education_submit, #preferences_submit, .btn-primary, button'
        );
        for (const b of btns) {
            if (b.offsetParent !== null && !b.disabled) {
                const txt = (b.textContent || b.value || '').trim();
                if (/^(next|continue|save|submit|done|find|let's go)/i.test(txt) || /save|next|continue/i.test(txt)) {
                    b.scrollIntoView({block: 'center'});
                    b.click();
                    return txt;
                }
            }
        }
        return null;
    """)
    if clicked:
        print(Fore.GREEN + f"[✓] Tombol lanjut ({step_name}) diklik: {clicked!r}")
        return True
    return click_chip(driver, "next", f"Next ({step_name})")


def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None


# ============================================================
#  IMAP
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
#  VERIFIKASI
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
#  ONBOARDING — Education & Preferences
# ============================================================
def fill_education(driver):
    print(Fore.CYAN + "\n[*] mengisi halaman Education...")
    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("education_start.png")

    # 1. Tipe pendidikan / kualifikasi (Graduation / College)
    click_chip(driver, "Graduation", "Education Type (Graduation)")
    time.sleep(0.5)

    # 2. College / University Name
    fill_autocomplete_generic(
        driver,
        "#college, input[name='college'], input[placeholder*='college' i], input[placeholder*='institute' i]",
        COLLEGE_NAME,
        "College"
    )
    time.sleep(0.5)

    # 3. Degree (misal: B.Tech)
    if not fill_autocomplete_generic(
        driver,
        "#degree, input[name='degree'], input[placeholder*='degree' i]",
        DEGREE,
        "Degree"
    ):
        click_chip(driver, DEGREE, "Degree Chip")
    time.sleep(0.5)

    # 4. Stream / Specialization (misal: Computer Science)
    if not fill_autocomplete_generic(
        driver,
        "#stream, input[name='stream'], input[placeholder*='stream' i], input[placeholder*='specialization' i]",
        STREAM,
        "Stream"
    ):
        click_chip(driver, STREAM, "Stream Chip")
    time.sleep(0.5)

    # 5. Start Year & End Year
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
    click_next_or_save(driver, "Education")
    time.sleep(WAIT_LONG)


def fill_preferences(driver):
    print(Fore.CYAN + "\n[*] mengisi halaman Preferences / Interests...")
    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("preferences_start.png")

    # 1. Looking for (Internships / Jobs)
    click_chip(driver, WORK_TYPE, f"Looking for: {WORK_TYPE}")
    time.sleep(0.5)

    # 2. Work Mode (Work from home / In-office)
    click_chip(driver, WORK_MODE, f"Work Mode: {WORK_MODE}")
    time.sleep(0.5)

    # 3. Areas of Interest
    for interest in INTEREST_AREAS:
        if not click_chip(driver, interest, f"Interest Chip: {interest}"):
            fill_autocomplete_generic(
                driver,
                "input[placeholder*='interest' i], input[placeholder*='category' i], input[placeholder*='search' i], input[placeholder*='profile' i], #preferences_search",
                interest,
                f"Interest Search: {interest}"
            )
        time.sleep(0.5)

    # 4. Preferred City (Jika ditanyakan lokasi preferensi)
    fill_autocomplete_generic(
        driver,
        "input[placeholder*='city' i], input[placeholder*='location' i], #preferred_city",
        CITY,
        "Preferred City"
    )
    time.sleep(0.5)

    driver.save_screenshot("preferences_filled.png")
    click_next_or_save(driver, "Preferences")
    time.sleep(WAIT_LONG)
    driver.save_screenshot("onboarding_complete.png")
    print(Fore.GREEN + f"[✓] Onboarding selesai! URL akhir: {driver.current_url}")


# ============================================================
#  ONBOARDING — Main Controller (Personal Details -> Next Steps)
# ============================================================
def fill_onboarding(driver):
    print(Fore.CYAN + "\n[*] mulai onboarding profil (Personal Details)...")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "#phone, input[name='phone_primary'], input[type='tel'], #current_city"
            ))
        )
    except Exception:
        print(Fore.YELLOW + "[~] Timeout menunggu elemen spesifik, lanjut mencoba isi...")

    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("onboarding_start.png")
    print(Fore.YELLOW + f"[i] URL: {driver.current_url}")

    # ---- NAMA (Jaga-jaga jika first_name / last_name kosong di personal details) ----
    parts = NAME.split(maxsplit=1)
    first_name = parts[0]
    last_name  = parts[1] if len(parts) > 1 else ""
    js_fill(driver, "#first_name, input[name='first_name']", first_name, "first_name (check)")
    js_fill(driver, "#last_name, input[name='last_name']", last_name, "last_name (check)")

    # ---- PHONE ----
    js_fill(
        driver,
        "#phone, #phone_primary, input[name='phone'], input[name='phone_primary'], input[type='tel']",
        PHONE,
        "phone"
    )
    time.sleep(0.5)

    # ---- GENDER ----
    click_chip(driver, GENDER, "gender")
    time.sleep(0.5)

    # ---- CITY ----
    fill_city_autocomplete(driver, CITY)
    time.sleep(0.8)

    # ---- USER TYPE ----
    if not click_chip(driver, USER_TYPE, "user type"):
        click_chip(driver, "College student", "user type fallback")
    time.sleep(0.5)

    # ---- LANGUAGES ----
    for lang in LANGUAGES:
        click_chip(driver, lang, f"language: {lang}")
        time.sleep(0.4)

    driver.save_screenshot("onboarding_filled.png")

    # ---- NEXT / SUBMIT PERSONAL DETAILS ----
    print(Fore.CYAN + "[*] klik Next pada Personal Details...")
    click_next_or_save(driver, "Personal Details")
    time.sleep(WAIT_LONG)

    driver.save_screenshot("onboarding_after_personal.png")
    print(Fore.YELLOW + f"[i] URL setelah Personal Details: {driver.current_url}")

    # ---- LANJUT OTOMATIS KE EDUCATION & PREFERENCES ----
    for step in range(3):
        curr_url = driver.current_url.lower()
        page_src = driver.page_source.lower()

        if "dashboard" in curr_url or ("internships" in curr_url and "preference" not in curr_url):
            print(Fore.GREEN + "[✓] Sudah masuk ke halaman utama / Dashboard!")
            break
        elif any(k in curr_url for k in ["education", "academic", "qualification", "degree"]) or "college" in page_src:
            fill_education(driver)
        elif any(k in curr_url for k in ["preference", "interest", "career"]) or "areas of interest" in page_src or "looking for" in page_src:
            fill_preferences(driver)
        else:
            # Jika halaman berupa SPA tanpa perubahan URL mencolok, jalankan berurutan
            fill_education(driver)
            fill_preferences(driver)
            break

    return True


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

    if "already" in page or "exists" in page:
        print(Fore.RED + "[!] email sudah terdaftar.")
        return "already_exists"
    if is_verify_page(driver):
        print(Fore.GREEN + "[✓] masuk halaman verifikasi.")
        return "verify_email"
    if "dashboard" in current or "student" in current or "onboarding" in current or "personal_details" in current:
        print(Fore.GREEN + "[✓] langsung masuk onboarding/dashboard.")
        return "success"
    if "error" in page or "invalid" in page:
        print(Fore.RED + "[!] error di form.")
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

            if input(Fore.YELLOW + "\nLanjut akun berikutnya? (y/n): ").strip().lower() != "y":
                break

        print(Fore.GREEN + f"\n[✓] selesai. log tersimpan di: {OUTPUT_JSON}")

    except Exception as e:
        print(Fore.RED + f"[!] error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
