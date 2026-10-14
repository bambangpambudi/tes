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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

init(autoreset=True)

# ============================================================
#  CONFIG — Indian Data
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
    """Persis fungsi js_fill kode awal Anda untuk halaman Signup & OTP."""
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


def find_visible_input(driver, selectors, label_hint=""):
    """
    Mencari elemen <input> yang sedang tampil di halaman Onboarding ('Let's get started').
    """
    return driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim()).filter(Boolean);
        const hint = (arguments[1] || '').toLowerCase();

        for (const s of sels) {
            const nodes = document.querySelectorAll(s);
            for (const n of nodes) {
                const rect = n.getBoundingClientRect();
                if ((n.offsetParent !== null || rect.width > 20) && !n.disabled && n.type !== 'hidden') {
                    return n;
                }
            }
        }

        if (hint) {
            const labels = Array.from(document.querySelectorAll('label, div, span, p'));
            for (const lb of labels) {
                const txt = (lb.textContent || '').trim().toLowerCase();
                if (txt === hint || (txt.startsWith(hint) && txt.length < hint.length + 15)) {
                    const container = lb.closest('.form-group, .input-group, div') || lb.parentElement;
                    if (container) {
                        const inp = container.querySelector('input:not([type="hidden"]):not([disabled])') ||
                                    (container.parentElement && container.parentElement.querySelector('input:not([type="hidden"]):not([disabled])'));
                        if (inp) {
                            const r = inp.getBoundingClientRect();
                            if (r.width > 20) return inp;
                        }
                    }
                }
            }
        }
        return null;
    """, selectors, label_hint)


def fill_input_onboarding(driver, selectors, value, label="field", label_hint=""):
    """
    Mengisi input di halaman 'Let's get started' (seperti Mobile number)
    menggunakan kombinasi klik, send_keys, dan React/Vue native value setter.
    """
    el = find_visible_input(driver, selectors, label_hint)
    if not el:
        print(Fore.RED + f"[!] {label} NOT FOUND")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        ActionChains(driver).move_to_element(el).click().perform()
        el.clear()
        el.send_keys(str(value))
    except Exception:
        pass

    final_val = driver.execute_script("""
        const el = arguments[0], val = arguments[1];
        el.focus();
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        if (setter) setter.call(el, val);
        else el.value = val;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
        el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
        el.dispatchEvent(new Event('blur', {bubbles: true}));
        return el.value;
    """, el, str(value))

    print(Fore.GREEN + f"[✓] {label} = {final_val}")
    return True


def fill_autocomplete_onboarding(driver, selectors, text_value, label="autocomplete", label_hint=""):
    """
    Mengisi field Autocomplete seperti 'Current location' (Current city), College, Degree, Stream.
    Mengetik per huruf lalu mengeklik pilihan yang muncul di dropdown.
    """
    el = find_visible_input(driver, selectors, label_hint)
    if not el:
        print(Fore.RED + f"[!] {label} NOT FOUND")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.3)
        ActionChains(driver).move_to_element(el).click().perform()
        el.clear()
        driver.execute_script("arguments[0].value = '';", el)

        for ch in text_value:
            el.send_keys(ch)
            driver.execute_script("""
                const el = arguments[0];
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keydown', {bubbles: true}));
                el.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            """, el)
            time.sleep(0.08)

        time.sleep(2.0)

        clicked = driver.execute_script("""
            const val = arguments[0].toLowerCase();
            const selectors = [
                '.ui-menu-item', '.ui-menu-item-wrapper', '.autocomplete-suggestion',
                '.pac-item', 'ul[role="listbox"] li', '.city-dropdown li',
                '.dropdown-menu li', '.autocomplete-items div', '.chosen-results li',
                'ul.ui-autocomplete li', 'div[class*="autocomplete"] li', 'div[class*="dropdown"] li',
                'li[role="option"]'
            ];
            const items = Array.from(document.querySelectorAll(selectors.join(', ')));
            for (const item of items) {
                const rect = item.getBoundingClientRect();
                if ((item.offsetParent !== null || rect.width > 10) && item.textContent.toLowerCase().includes(val)) {
                    item.scrollIntoView({block: 'nearest'});
                    item.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    item.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                    item.click();
                    return item.textContent.trim();
                }
            }
            return null;
        """, text_value)

        if clicked:
            print(Fore.GREEN + f"[✓] {label} dipilih dari dropdown: {clicked!r}")
            return True
        else:
            el.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.4)
            el.send_keys(Keys.ENTER)
            time.sleep(0.3)
            print(Fore.YELLOW + f"[~] {label} diisi via ARROW_DOWN + ENTER: {text_value}")
            return True

    except Exception as e:
        print(Fore.RED + f"[!] Gagal isi {label}: {e}")
        return False


def click_chip(driver, text, label=None):
    """
    Mengeklik pill/chip di halaman 'Let's get started' (Male, English +, Hindi +, Fresher).
    """
    label = label or text
    el = driver.execute_script(r"""
        const rawTarget = arguments[0].toLowerCase().trim();
        const cleanTarget = rawTarget.replace(/[^a-z0-9]+/g, '');

        const nodes = Array.from(document.querySelectorAll(
            'label, button, span, div, li, a, input[type="button"], input[type="submit"]'
        ));

        const exact = [];
        const partial = [];

        for (const n of nodes) {
            const rect = n.getBoundingClientRect();
            if (rect.width < 15 || rect.height < 15 || rect.height > 85) continue;
            if (n.offsetParent === null && rect.top === 0) continue;

            let raw = (n.textContent || n.value || '').trim();
            if (!raw || raw.length > 40) continue;

            let clean = raw.toLowerCase().replace(/[^a-z0-9]+/g, '');
            if (!clean) continue;

            const childrenCount = n.children.length;

            if (clean === cleanTarget) {
                exact.push({el: n, childrenCount, len: raw.length});
            } else if (raw.toLowerCase().includes(rawTarget) && raw.length <= rawTarget.length + 6) {
                partial.push({el: n, childrenCount, len: raw.length});
            }
        }

        const pool = exact.length ? exact : partial;
        if (!pool.length) return null;

        pool.sort((a, b) => (a.childrenCount - b.childrenCount) || (a.len - b.len));
        let targetEl = pool[0].el;

        const wrapper = targetEl.closest('label, button, [role="button"], .chip, .pill');
        return wrapper || targetEl;
    """, text)

    if not el:
        print(Fore.RED + f"[!] {label} NOT FOUND")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.2)
        ActionChains(driver).move_to_element(el).click().perform()
    except Exception:
        pass

    matched_text = driver.execute_script("""
        const el = arguments[0];
        el.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
        el.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
        el.click();

        const inp = el.querySelector('input[type="radio"], input[type="checkbox"]') ||
                    (el.control ? el.control : null);
        if (inp && !inp.checked) {
            inp.checked = true;
            inp.dispatchEvent(new Event('change', {bubbles: true}));
            inp.dispatchEvent(new Event('input', {bubbles: true}));
            inp.click();
        }
        return (el.textContent || el.value || '').trim();
    """, el)

    print(Fore.GREEN + f"[✓] {label} clicked (matched: {matched_text!r})")
    return True


def select_dropdown_or_chip(driver, selectors, value, label="dropdown"):
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
        print(Fore.YELLOW + "\n[i] Cek email. Copy OTP 6 digit atau paste link verifikasi (jangan diklik di HP).")
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
#  ONBOARDING — Let's Get Started, Education, & Preferences
# ============================================================
def click_next_button(driver, label="Next"):
    """Mengeklik tombol biru 'Next' di kanan bawah."""
    el = driver.execute_script("""
        const btns = document.querySelectorAll(
            '#personal_details_submit, #education_submit, #preferences_submit, button[type="submit"], input[type="submit"], .btn-primary, button'
        );
        for (const b of btns) {
            const rect = b.getBoundingClientRect();
            if ((b.offsetParent !== null || rect.width > 20) && !b.disabled) {
                const txt = (b.textContent || b.value || '').trim();
                if (/^(next|continue|save|submit|done|find)/i.test(txt)) {
                    return b;
                }
            }
        }
        return null;
    """)
    if el:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.2)
            ActionChains(driver).move_to_element(el).click().perform()
        except Exception:
            pass
        driver.execute_script("arguments[0].click();", el)
        print(Fore.GREEN + f"[✓] Tombol {label} diklik")
        return True
    return click_chip(driver, "next", label)


def fill_education(driver):
    print(Fore.CYAN + "\n[*] memeriksa / mengisi halaman Education...")
    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("education_start.png")

    click_chip(driver, "Graduation", "Education Type (Graduation)")
    time.sleep(0.5)

    fill_autocomplete_onboarding(
        driver,
        "#college, input[name='college'], input[placeholder*='college' i], input[placeholder*='institute' i]",
        COLLEGE_NAME,
        "College",
        label_hint="college"
    )
    time.sleep(0.5)

    if not fill_autocomplete_onboarding(
        driver,
        "#degree, input[name='degree'], input[placeholder*='degree' i]",
        DEGREE,
        "Degree",
        label_hint="degree"
    ):
        click_chip(driver, DEGREE, "Degree Chip")
    time.sleep(0.5)

    if not fill_autocomplete_onboarding(
        driver,
        "#stream, input[name='stream'], input[placeholder*='stream' i], input[placeholder*='specialization' i]",
        STREAM,
        "Stream",
        label_hint="stream"
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
    print(Fore.CYAN + "\n[*] memeriksa / mengisi halaman Preferences...")
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
    print(Fore.CYAN + "\n[*] mulai onboarding profil ('Let's get started')...")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "input[placeholder*='Mobile' i], input[placeholder*='location' i], #phone, #current_city"
            ))
        )
    except Exception:
        print(Fore.YELLOW + "[~] Menunggu render halaman Personal Details...")

    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("onboarding_start.png")
    print(Fore.YELLOW + f"[i] URL: {driver.current_url}")

    # 1. PHONE (placeholder="Mobile number" di bawah label "Contact number")
    fill_input_onboarding(
        driver,
        "input[placeholder*='Mobile number' i], input[placeholder*='Mobile' i], #phone, #phone_primary, input[name='phone'], input[name='phone_primary'], input[type='tel']",
        PHONE,
        "Contact number (Phone)",
        label_hint="contact number"
    )
    time.sleep(0.5)

    # 2. CURRENT CITY (placeholder="Current location" di bawah label "Current city")
    fill_autocomplete_onboarding(
        driver,
        "input[placeholder*='Current location' i], input[placeholder*='location' i], #current_city, input[name='current_city'], input[placeholder*='city' i]",
        CITY,
        "Current city",
        label_hint="current city"
    )
    time.sleep(0.6)

    # 3. GENDER ('🙋‍♂️ Male' / '🙋‍♀️ Female')
    click_chip(driver, GENDER, f"Gender ({GENDER})")
    time.sleep(0.5)

    # 4. LANGUAGES YOU KNOW ('English +', 'Hindi +')
    for lang in LANGUAGES:
        click_chip(driver, lang, f"Language ({lang})")
        time.sleep(0.4)

    # 5. TYPE ('Fresher' / 'College student')
    if not click_chip(driver, USER_TYPE, f"Type ({USER_TYPE})"):
        click_chip(driver, "College student", "Type (College student)")
    time.sleep(0.5)

    driver.save_screenshot("onboarding_filled.png")

    # 6. KLIK TOMBOL BIRU 'Next'
    print(Fore.CYAN + "[*] klik Next...")
    click_next_button(driver, "Next (Personal Details)")
    time.sleep(WAIT_LONG)

    driver.save_screenshot("onboarding_done.png")
    print(Fore.YELLOW + f"[i] URL setelah Next: {driver.current_url}")

    # 7. Lanjut ke Education & Preferences
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
            break

    return True


# ============================================================
#  SIGNUP (Persis kode awal Anda tanpa auto-login)
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
    if "dashboard" in current or ("student" in current and "registration" not in current):
        print(Fore.GREEN + "[✓] langsung masuk onboarding/dashboard.")
        return "success"
    if "already" in page or "exists" in page:
        print(Fore.RED + "[!] email sudah terdaftar.")
        return "already_exists"
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

            if input(Fore.YELLOW + "\nLanjut? (y/n): ").strip().lower() != "y":
                break

        print(Fore.GREEN + f"\n[✓] selesai. log: {OUTPUT_JSON}")

    except Exception as e:
        print(Fore.RED + f"[!] error: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
