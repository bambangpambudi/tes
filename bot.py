import os
import re
import json
import time
import random
import imaplib
import email as email_lib

from pathlib import Path
from dotenv import load_dotenv
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
#  LOAD .env
# ============================================================
ENV_PATH = Path(__file__).parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    print(Fore.YELLOW + f"[!] .env tidak ditemukan di {ENV_PATH}, pakai default.")
    load_dotenv()

def _env(key, default=""):
    return os.getenv(key, default).strip()

def _env_int(key, default):
    try:
        return int(os.getenv(key, default))
    except Exception:
        return default

def _env_list(key, default=""):
    raw = os.getenv(key, default)
    return [x.strip() for x in raw.split(",") if x.strip()]

# ============================================================
#  CONFIG
# ============================================================
SIGNUP_URL      = _env("URL_SIGNUP", "https://internshala.com/registration/student")
URL_STEP_1      = _env("URL_STEP_1", "https://internshala.com/student/personal_details")
PREF_STEP_2_URL = _env("URL_STEP_2", "https://internshala.com/user_preference/preferences/?referral=personal_details")
PREF_STEP_3_URL = _env("URL_STEP_3", "https://internshala.com/student/preferences")

PASSWORD = _env("PASSWORD", "Dermaga07")
NAME     = _env("NAME", "Arya Rahman")
_phone   = _env("PHONE", "")
PHONE    = _phone if _phone else f"98{random.randint(10000000, 99999999)}"
CITY     = _env("CITY", "Mumbai, Maharashtra, India")

GENDER    = _env("GENDER", "Male")
USER_TYPE = _env("USER_TYPE", "College student")
LANGUAGES = _env_list("LANGUAGES", "English,Hindi")

COLLEGE_NAME = _env("COLLEGE", "University of Mumbai")
DEGREE       = _env("DEGREE", "B.Tech")
STREAM       = _env("STREAM", "Computer Science")
START_YEAR   = _env("START_YEAR", "2022")
END_YEAR     = _env("END_YEAR", "2026")

SKILLS         = _env_list("SKILLS", "Python,JavaScript,HTML")
INTEREST_AREAS = _env_list("INTERESTS", "Web Development,Software Development,Data Science")
WORK_TYPE      = _env("WORK_TYPE", "Jobs")
WORK_MODE      = _env("WORK_MODE", "Work from home")
CAREER_GOALS   = _env_list("CAREER_GOALS",
                           "Get an online degree from a premium institute in India,"
                           "Go for study abroad,"
                           "Enroll in job bootcamp (paid training to get a job),"
                           "Prepare for government exams")

WAIT_SHORT  = _env_int("WAIT_SHORT", 2)
WAIT_LONG   = _env_int("WAIT_LONG", 5)
OUTPUT_JSON = _env("OUTPUT_JSON", "output/accounts.json")


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


def fill_input_onboarding(driver, selectors, value, label="field", label_hint="", silent=False):
    el = None
    sel_list = [s.strip() for s in selectors.split(",") if s.strip()]

    for s in sel_list:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, s)
            for e in els:
                if e.is_displayed() and e.is_enabled():
                    el = e
                    break
            if el:
                break
        except Exception:
            continue

    if not el and label_hint:
        try:
            xp = (f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                  f"'abcdefghijklmnopqrstuvwxyz'), '{label_hint.lower()}')]"
                  f"/following::input[not(@type='hidden')][1]")
            els = driver.find_elements(By.XPATH, xp)
            if els:
                el = els[0]
        except Exception:
            pass

    if not el:
        if not silent:
            print(Fore.RED + f"[!] {label} NOT FOUND")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.4)
        ActionChains(driver).move_to_element(el).pause(0.15).click().perform()
        time.sleep(0.2)
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        time.sleep(0.15)
        for ch in str(value):
            el.send_keys(ch)
            time.sleep(0.03)
        driver.execute_script("arguments[0].blur();", el)
        time.sleep(0.3)

        actual = el.get_attribute("value")
        if actual == str(value):
            print(Fore.GREEN + f"[✓] {label} = {actual!r}")
            return True

        driver.execute_script("""
            const el = arguments[0], val = arguments[1];
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(el, val);
            ['input','change','keyup','keydown','blur'].forEach(ev =>
                el.dispatchEvent(new Event(ev, {bubbles: true}))
            );
        """, el, str(value))
        time.sleep(0.3)
        actual = el.get_attribute("value")
        print(Fore.YELLOW + f"[~] {label} = {actual!r} (fallback)")
        return actual == str(value)
    except Exception as e:
        if not silent:
            print(Fore.RED + f"[!] {label} FAILED: {e}")
        return False


def fill_autocomplete_onboarding(driver, selectors, text_value, label="autocomplete",
                                  label_hint="", silent=False, prefer_startswith=True):
    el = None
    sel_list = [s.strip() for s in selectors.split(",") if s.strip()]
    for s in sel_list:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, s)
            for e in els:
                if e.is_displayed() and e.is_enabled():
                    el = e
                    break
            if el:
                break
        except Exception:
            continue

    if not el and label_hint:
        try:
            xp = (f"//label[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', "
                  f"'abcdefghijklmnopqrstuvwxyz'), '{label_hint.lower()}')]"
                  f"/following::input[not(@type='hidden')][1]")
            els = driver.find_elements(By.XPATH, xp)
            if els:
                el = els[0]
        except Exception:
            pass

    if not el:
        if not silent:
            print(Fore.YELLOW + f"[~] {label} tidak ditemukan")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        time.sleep(0.3)
        ActionChains(driver).move_to_element(el).pause(0.15).click().perform()
        time.sleep(0.2)
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        time.sleep(0.15)
        for ch in str(text_value):
            el.send_keys(ch)
            time.sleep(0.08)
        time.sleep(2.5)

        clicked = driver.execute_script("""
            const val = arguments[0].toLowerCase().trim();
            const preferStart = arguments[1];
            const sels = [
                '.ui-menu-item', '.ui-menu-item-wrapper', '.autocomplete-suggestion',
                '.pac-item', 'ul[role="listbox"] li', '.city-dropdown li',
                '.dropdown-menu li', '.autocomplete-items div', '.chosen-results li',
                'ul.ui-autocomplete li', 'div[class*="autocomplete"] li',
                'div[class*="dropdown"] li', 'li[role="option"]',
                'div[class*="suggestion"]', '.option', '.result-item'
            ];
            const items = [];
            for (const s of sels) {
                for (const el of document.querySelectorAll(s)) {
                    if (el.offsetParent === null) continue;
                    const t = (el.textContent || '').trim();
                    if (!t) continue;
                    const tl = t.toLowerCase();
                    if (!tl.includes(val)) continue;
                    const starts = tl.startsWith(val);
                    items.push({
                        el: el,
                        text: t,
                        starts: starts ? 1 : 0,
                        len: t.length
                    });
                }
            }
            if (!items.length) return null;
            items.sort((a, b) => {
                if (preferStart && a.starts !== b.starts) return b.starts - a.starts;
                return a.len - b.len;
            });
            const winner = items[0].el;
            winner.scrollIntoView({block: 'nearest'});
            winner.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
            winner.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
            winner.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
            winner.click();
            return items[0].text;
        """, text_value, prefer_startswith)

        if clicked:
            print(Fore.GREEN + f"[✓] {label} dipilih: {clicked!r}")
            return True
        else:
            driver.execute_script("""
                const el = arguments[0], val = arguments[1];
                const setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(el, val);
                ['input','change','keyup','blur'].forEach(ev =>
                    el.dispatchEvent(new Event(ev, {bubbles: true}))
                );
            """, el, str(text_value))
            print(Fore.GREEN + f"[✓] {label} diisi (no dropdown): {text_value}")
            return True
    except Exception as e:
        if not silent:
            print(Fore.RED + f"[!] {label} autocomplete FAILED: {e}")
        return False


def click_chip(driver, text, label=None, silent=False):
    """
    Klik chip dengan strip emoji/symbol. Match exact setelah normalisasi.
    """
    label = label or text
    clean_text = text.strip().lower()

    for attempt in range(4):
        try:
            clicked = driver.execute_script("""
                const target = arguments[0].toLowerCase().trim();
                const navFilter = 'nav,header,footer,.navbar,.footer,.header,.sidebar';

                // normalisasi: hapus symbol, emoji, whitespace ekstra
                function normalize(s) {
                    return s
                        .replace(/[\\+×✕✅✔️]/g, '')
                        // hapus emoji (unicode ranges)
                        .replace(/[\\u{1F300}-\\u{1FAFF}]/gu, '')
                        .replace(/[\\u{2600}-\\u{27BF}]/gu, '')
                        .replace(/[\\u{1F000}-\\u{1F02F}]/gu, '')
                        .replace(/\\s+/g, ' ')
                        .trim()
                        .toLowerCase();
                }

                const candidates = [];
                for (const tag of ['button', 'label', 'div', 'span', 'a']) {
                    for (const el of document.querySelectorAll(tag)) {
                        if (el.offsetParent === null) continue;
                        if (el.closest(navFilter)) continue;
                        const raw = (el.textContent || '').trim();
                        if (!raw || raw.length > 80) continue;

                        const clean = normalize(raw);
                        if (!clean) continue;
                        if (clean !== target) continue;

                        candidates.push({
                            el: el,
                            children: el.children.length,
                            len: raw.length,
                            raw: raw
                        });
                    }
                }

                if (!candidates.length) return null;
                candidates.sort((a, b) => (a.children - b.children) || (a.len - b.len));
                const winner = candidates[0].el;

                winner.scrollIntoView({block: 'center'});
                winner.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                winner.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                winner.click();

                const parent = winner.closest('button, label, [role="button"], .chip, .pill');
                if (parent && parent !== winner) {
                    parent.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    parent.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                    parent.click();
                }

                const wrapper = winner.closest('label') || winner.parentElement;
                if (wrapper) {
                    let inp = wrapper.querySelector('input[type="radio"], input[type="checkbox"]');
                    if (!inp && wrapper.tagName === 'LABEL' && wrapper.htmlFor) {
                        inp = document.getElementById(wrapper.htmlFor);
                    }
                    if (inp && !inp.checked) {
                        inp.checked = true;
                        inp.dispatchEvent(new Event('input', {bubbles: true}));
                        inp.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                }
                return candidates[0].raw;
            """, clean_text)

            if clicked:
                time.sleep(0.7)
                # verifikasi state (chip jadi selected: ada ×, tidak ada +)
                is_selected = driver.execute_script("""
                    const target = arguments[0].toLowerCase().trim();
                    const navFilter = 'nav,header,footer,.navbar,.footer,.header,.sidebar';
                    function normalize(s) {
                        return s
                            .replace(/[\\+×✕✅✔️]/g, '')
                            .replace(/[\\u{1F300}-\\u{1FAFF}]/gu, '')
                            .replace(/[\\u{2600}-\\u{27BF}]/gu, '')
                            .replace(/\\s+/g, ' ')
                            .trim()
                            .toLowerCase();
                    }
                    for (const tag of ['button', 'label', 'div', 'span']) {
                        for (const el of document.querySelectorAll(tag)) {
                            if (el.offsetParent === null) continue;
                            if (el.closest(navFilter)) continue;
                            const raw = (el.textContent || '').trim();
                            const clean = normalize(raw);
                            if (clean !== target) continue;
                            // kalau masih ada '+', belum selected
                            if (/\\+\\s*$/.test(raw.trim())) continue;
                            return true;
                        }
                    }
                    return false;
                """, clean_text)

                if is_selected:
                    print(Fore.GREEN + f"[✓] {label} clicked & selected ({clicked!r})")
                    return True
                else:
                    print(Fore.YELLOW + f"[~] {label} clicked ({clicked!r}), retry...")
                    if attempt < 3:
                        time.sleep(0.6)
                        continue
                    return True

        except Exception as e:
            if "stale" in str(e).lower() and attempt < 3:
                print(Fore.YELLOW + f"[~] {label} stale, retry {attempt+1}/3...")
                time.sleep(0.8)
                continue
            if not silent:
                print(Fore.RED + f"[!] {label} FAILED: {e}")
            return False

    if not silent:
        print(Fore.RED + f"[!] {label} gagal setelah 4 attempt")
    return False


def select_dropdown_or_chip(driver, selectors, value, label="dropdown", silent=False):
    selected = driver.execute_script("""
        const sels = arguments[0].split(',').map(s => s.trim());
        const val = arguments[1].toLowerCase();
        for (const s of sels) {
            const el = document.querySelector(s);
            if (el && el.tagName === 'SELECT' && el.offsetParent !== null) {
                for (const opt of el.options) {
                    if (opt.text.toLowerCase().includes(val)
                        || opt.value.toLowerCase() === val) {
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
    if fill_autocomplete_onboarding(driver, selectors, str(value), label, silent=True):
        return True
    return click_chip(driver, str(value), label, silent=silent)


def click_next_or_save(driver, label="Next / Save"):
    clicked_txt = driver.execute_script("""
        const specificIds = [
            '#personal_details_submit', '#education_submit', '#preferences_submit',
            '#save_preferences', '#submit_button', 'button[type="submit"]',
            'input[type="submit"]'
        ];
        for (const sel of specificIds) {
            const btns = document.querySelectorAll(sel);
            for (const b of btns) {
                if (b.closest('nav, header, footer, .navbar')) continue;
                const rect = b.getBoundingClientRect();
                if ((b.offsetParent !== null || rect.width > 20) && !b.disabled) {
                    const txt = (b.textContent || b.value || '').trim();
                    if (!/course|login|register/i.test(txt)) {
                        b.scrollIntoView({block: 'center'});
                        b.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                        b.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                        b.click();
                        return txt || sel;
                    }
                }
            }
        }
        const allBtns = document.querySelectorAll(
            'button, input[type="button"], input[type="submit"], a.btn, .btn-primary'
        );
        for (const b of allBtns) {
            if (b.closest('nav, header, footer, .navbar')) continue;
            const rect = b.getBoundingClientRect();
            if ((b.offsetParent !== null || rect.width > 20) && !b.disabled) {
                const txt = (b.textContent || b.value || '').trim();
                if (/^(next|save|continue|save & continue|save and continue|submit|done|let's go|find me opportunities|find opportunities)$/i.test(txt)) {
                    b.scrollIntoView({block: 'center'});
                    b.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    b.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                    b.click();
                    return txt;
                }
            }
        }
        return null;
    """)
    if clicked_txt:
        print(Fore.GREEN + f"[✓] Tombol {label} diklik ({clicked_txt!r})")
        return True
    return click_chip(driver, "Next", label, silent=True) or \
           click_chip(driver, "Save", label, silent=True)


def get_form_errors(driver):
    return driver.execute_script("""
        const errSelectors = [
            '.help-block', '.error', '.field-error', '.invalid-feedback',
            '[id$="-error"]', '.toast-message', '.alert-danger'
        ];
        const msgs = [];
        for (const sel of errSelectors) {
            for (const el of document.querySelectorAll(sel)) {
                if (el.offsetParent !== null) {
                    const t = (el.textContent || '').trim();
                    if (t && !msgs.includes(t)) msgs.push(t);
                }
            }
        }
        return msgs.join(' | ');
    """) or ""


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
    return any(k in url for k in keywords_url) or \
           any(k in page for k in keywords_page)


def handle_verification(driver, email, mode, gmail_user=None, gmail_pass=None):
    print(Fore.CYAN + "\n[*] halaman verifikasi terdeteksi.")
    driver.save_screenshot("verify_page.png")
    print(Fore.YELLOW + f"[i] URL verify: {driver.current_url}")

    print(Fore.CYAN + "\n=== FORM ELEMENTS DI HALAMAN VERIFY ===")
    for tag in ["input", "button", "a", "form"]:
        for el in driver.find_elements(By.TAG_NAME, tag):
            try:
                el_id   = el.get_attribute("id")
                el_name = el.get_attribute("name")
                el_type = el.get_attribute("type")
                el_ph   = el.get_attribute("placeholder")
                el_text = (el.text or "")[:40]
                if el_id or el_name or el_ph or el_text:
                    print(f"[{tag}] id={el_id!r} name={el_name!r} "
                          f"type={el_type!r} placeholder={el_ph!r} text={el_text!r}")
            except Exception:
                pass
    print("=== END DUMP ===\n")

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

    while not otp:
        print(Fore.YELLOW + "\n[i] Cek email. Copy OTP 6 digit atau paste link.")
        user_input = input(Fore.CYAN + "OTP / Link: ").strip()
        if user_input.startswith("http"):
            driver.get(user_input)
            time.sleep(WAIT_LONG)
            return True
        if len(user_input) < 6:
            print(Fore.RED + f"[!] OTP minimal 6 digit (baru {len(user_input)}).")
            continue
        otp = user_input

    print(Fore.CYAN + f"[*] isi OTP: {otp}")

    filled = False
    otp_candidates = [
        "input[name='otp']", "input#otp", "input[name='verification_code']",
        "input[placeholder*='OTP' i]", "input[placeholder*='code' i]",
        "input[type='tel']", "input[type='number']", "input[type='text']"
    ]
    for sel in otp_candidates:
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            for e in els:
                if e.is_displayed() and e.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", e)
                    time.sleep(0.3)
                    ActionChains(driver).move_to_element(e).pause(0.15).click().perform()
                    time.sleep(0.2)
                    e.send_keys(Keys.CONTROL, "a")
                    e.send_keys(Keys.DELETE)
                    for ch in str(otp):
                        e.send_keys(ch)
                        time.sleep(0.05)
                    driver.execute_script("arguments[0].blur();", e)
                    print(Fore.GREEN + f"[✓] OTP diisi via {sel}")
                    filled = True
                    break
            if filled:
                break
        except Exception:
            continue

    if not filled:
        print(Fore.RED + "[!] gagal isi OTP")
        return False

    driver.save_screenshot("otp_filled.png")
    time.sleep(1)

    print(Fore.CYAN + "[*] klik tombol verifikasi...")
    clicked = False
    for btn_text in ["Verify", "Submit", "Continue", "Confirm", "Next"]:
        if click_chip(driver, btn_text, f"Button ({btn_text})", silent=True):
            clicked = True
            break

    if not clicked:
        try:
            btns = driver.find_elements(
                By.CSS_SELECTOR,
                "button[type='submit'], button.btn-primary"
            )
            for b in btns:
                if b.is_displayed() and b.is_enabled():
                    ActionChains(driver).move_to_element(b).pause(0.15).click().perform()
                    print(Fore.GREEN + "[✓] klik button[type=submit]")
                    clicked = True
                    break
        except Exception:
            pass

    time.sleep(WAIT_LONG + 3)

    print(Fore.YELLOW + f"\n[i] URL setelah submit OTP: {driver.current_url}")
    driver.save_screenshot("after_otp_submit.png")

    cur_lower = driver.current_url.lower()
    page_lower = driver.page_source.lower()

    still_verify = any(k in cur_lower for k in ["verify", "otp", "confirm"]) or \
                   any(k in page_lower for k in ["enter otp", "verification code",
                                                  "invalid otp", "incorrect otp"])
    if still_verify:
        print(Fore.RED + "[!] masih di halaman verifikasi setelah submit.")
        return False

    print(Fore.GREEN + "[✓] verifikasi berhasil.")
    return True


# ============================================================
#  ONBOARDING — STEP 1
# ============================================================
def fill_onboarding(driver):
    print(Fore.CYAN + f"\n[*] TAHAP 1: Personal Details — {URL_STEP_1}")

    if "personal_details" not in driver.current_url.lower():
        driver.get(URL_STEP_1)
        time.sleep(WAIT_LONG)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "input[placeholder*='Mobile' i], input[placeholder*='location' i], "
                "#phone, #current_city"
            ))
        )
    except Exception:
        pass

    time.sleep(3)
    close_modals(driver)
    driver.save_screenshot("onboarding_start.png")
    print(Fore.YELLOW + f"[i] URL: {driver.current_url}")

    # ---- PHONE ----
    fill_input_onboarding(
        driver,
        "input[placeholder*='Mobile number' i], input[placeholder*='Mobile' i], "
        "#phone, #phone_primary, input[name='phone'], "
        "input[name='phone_primary'], input[type='tel']",
        PHONE, "Contact number", label_hint="contact number"
    )
    time.sleep(1.0)

    # ---- CITY ----
    fill_autocomplete_onboarding(
        driver,
        "input[placeholder*='Current location' i], input[placeholder*='location' i], "
        "#current_city, input[name='current_city'], input[placeholder*='city' i]",
        CITY, "Current city", label_hint="current city", prefer_startswith=True
    )
    time.sleep(2.5)

    # ---- GENDER ----
    click_chip(driver, GENDER, f"Gender ({GENDER})")
    time.sleep(1.0)

    # ---- LANGUAGES ----
    for lang in LANGUAGES:
        click_chip(driver, lang, f"Language ({lang})")
        time.sleep(0.8)

    # ---- USER TYPE ----
    if not click_chip(driver, USER_TYPE, f"Type ({USER_TYPE})"):
        alt = "College student" if USER_TYPE.lower() == "fresher" else "Fresher"
        print(Fore.YELLOW + f"[~] Type {USER_TYPE} gagal, fallback ke {alt}")
        click_chip(driver, alt, f"Type (fallback {alt})")
    time.sleep(1.0)

    # ---- COURSE ----
    course_map = {
        "B.Tech": "B.Tech", "BTech": "B.Tech", "BE": "BE",
        "B.Com": "B.Com", "B.Com.": "B.Com", "MBA": "MBA",
        "BBA": "BBA", "BCA": "BCA", "BA": "B.A", "B.Sc": "B.Sc",
        "M.Tech": "M.Tech", "MCA": "MCA", "M.Com": "M.Com",
        "PhD": "PhD", "Diploma": "Diploma",
    }
    course_chip = course_map.get(DEGREE, DEGREE)
    click_chip(driver, course_chip, f"Course chip ({course_chip})", silent=True)
    time.sleep(0.8)

    # ---- COLLEGE ----
    fill_autocomplete_onboarding(
        driver,
        "input[placeholder*='College name' i], input[placeholder*='college' i], "
        "input[placeholder*='institute' i], input[name='college'], #college",
        COLLEGE_NAME, "College", label_hint="college name", prefer_startswith=True
    )
    time.sleep(1.5)

    # ---- STREAM (placeholder "Eg. Computer Science") ----
    stream_el = None
    for sel in [
        "input[placeholder*='Computer Science' i]",
        "input[placeholder*='stream' i]",
        "input[placeholder*='Eg.' i]",
        "#stream",
        "input[name='stream']",
    ]:
        try:
            for e in driver.find_elements(By.CSS_SELECTOR, sel):
                if e.is_displayed() and e.is_enabled():
                    stream_el = e
                    break
            if stream_el:
                break
        except Exception:
            continue

    if stream_el:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", stream_el)
            time.sleep(0.3)
            ActionChains(driver).move_to_element(stream_el).pause(0.15).click().perform()
            time.sleep(0.2)
            stream_el.send_keys(Keys.CONTROL, "a")
            stream_el.send_keys(Keys.DELETE)
            for ch in STREAM:
                stream_el.send_keys(ch)
                time.sleep(0.04)
            driver.execute_script("arguments[0].blur();", stream_el)
            print(Fore.GREEN + f"[✓] Stream = {stream_el.get_attribute('value')!r}")
        except Exception as e:
            print(Fore.YELLOW + f"[~] Stream FAILED: {e}")
    else:
        print(Fore.YELLOW + "[~] Stream field gak ketemu")
    time.sleep(0.8)

    # ---- START_YEAR / END_YEAR ----
    for yr_key, yr_val, yr_label in [
        ("start_year", START_YEAR, "Start year"),
        ("end_year",   END_YEAR,   "End year"),
    ]:
        selected = driver.execute_script("""
            const key = arguments[0], val = arguments[1];
            const sels = [
                `select[name='${key}']`,
                `#${key}`,
                `select[id*='${key.replace('_', '')}']`
            ];
            for (const s of sels) {
                const el = document.querySelector(s);
                if (!el || el.tagName !== 'SELECT' || el.offsetParent === null) continue;
                for (const opt of el.options) {
                    if (opt.text.trim() === val || opt.value.trim() === val) {
                        el.value = opt.value;
                        el.dispatchEvent(new Event('change', {bubbles: true}));
                        return opt.text;
                    }
                }
            }
            return null;
        """, yr_key, str(yr_val))
        if selected:
            print(Fore.GREEN + f"[✓] {yr_label} = {selected}")
        else:
            print(Fore.YELLOW + f"[~] {yr_label} dropdown gak ketemu")
        time.sleep(0.6)

    driver.save_screenshot("onboarding_filled.png")

    err = get_form_errors(driver)
    if err:
        print(Fore.YELLOW + f"[~] Validasi sebelum Next: {err}")

    print(Fore.CYAN + "[*] klik Next...")
    click_next_or_save(driver, "Next (Personal Details)")
    time.sleep(WAIT_LONG + 2)

    print(Fore.YELLOW + f"[i] URL setelah Next: {driver.current_url}")
    driver.save_screenshot("after_step1_next.png")

    # ---- TAHAP 2 ----
    if "user_preference" in driver.current_url.lower():
        fill_step2_interests(driver)
    else:
        driver.get(PREF_STEP_2_URL)
        time.sleep(WAIT_LONG)
        if "user_preference" in driver.current_url.lower():
            fill_step2_interests(driver)

    # ---- TAHAP 3 ----
    if "/student/preferences" in driver.current_url.lower():
        fill_step3_preferences(driver)
    else:
        driver.get(PREF_STEP_3_URL)
        time.sleep(WAIT_LONG)
        if "/student/preferences" in driver.current_url.lower():
            fill_step3_preferences(driver)

    driver.save_screenshot("onboarding_complete.png")
    print(Fore.GREEN + f"[✓] Onboarding selesai! URL: {driver.current_url}")
    return True


# ============================================================
#  TAHAP 2 — Areas of Interest
# ============================================================
def fill_step2_interests(driver):
    print(Fore.CYAN + f"\n[*] TAHAP 2: Areas of Interest — {driver.current_url}")
    time.sleep(2.5)
    close_modals(driver)
    driver.save_screenshot("step2_start.png")

    print(Fore.CYAN + "[*] isi Area(s) of interest...")
    for interest in INTEREST_AREAS:
        ok = click_chip(driver, interest, f"interest chip ({interest})", silent=True)
        if not ok:
            print(Fore.YELLOW + f"[~] {interest}: bukan chip, coba autocomplete...")
            fill_autocomplete_onboarding(
                driver,
                "input[placeholder*='interest' i], input[placeholder*='learn' i], "
                "input[placeholder*='work in' i], #preferences_search, "
                "input[name*='interest' i]",
                interest, f"interest search ({interest})",
                label_hint="area", silent=True, prefer_startswith=True
            )
        time.sleep(0.6)

    print(Fore.CYAN + "\n[i] Chip ter-selected:")
    chips = driver.execute_script("""
        const navFilter = 'nav,header,footer,.navbar,.footer,.header,.sidebar';
        const seen = new Set();
        const out = [];
        for (const el of document.querySelectorAll('button, label, div, span')) {
            if (el.offsetParent === null) continue;
            if (el.closest(navFilter)) continue;
            const raw = (el.textContent || '').trim();
            if (!raw || raw.length > 50) continue;
            if (el.children.length > 2) continue;
            if (!/×$/.test(raw)) continue;
            const clean = raw.replace(/[\\+×✕]/g, '').trim();
            if (!clean || seen.has(clean)) continue;
            seen.add(clean);
            out.push(clean);
        }
        return out;
    """) or []
    for c in chips:
        print(f"    [selected] {c}")

    driver.save_screenshot("step2_filled.png")

    print(Fore.CYAN + "\n[*] klik Next...")
    click_next_or_save(driver, "Next (Tahap 2)")
    time.sleep(WAIT_LONG + 2)

    print(Fore.YELLOW + f"[i] URL setelah Next: {driver.current_url}")
    driver.save_screenshot("step2_done.png")
    return True


# ============================================================
#  TAHAP 3 — Student Preferences
# ============================================================
def fill_step3_preferences(driver):
    print(Fore.CYAN + f"\n[*] TAHAP 3: Student Preferences — {driver.current_url}")
    time.sleep(2.5)
    close_modals(driver)
    driver.save_screenshot("step3_start.png")

    # 1. Currently looking for
    print(Fore.CYAN + f"[*] Currently looking for -> {WORK_TYPE}")
    ok = click_chip(driver, WORK_TYPE, f"work type ({WORK_TYPE})", silent=True)
    if not ok:
        alt = "Internships" if WORK_TYPE.lower() == "jobs" else "Jobs"
        click_chip(driver, alt, f"work type alt ({alt})", silent=True)
    time.sleep(1.0)

    # 2. Work mode
    print(Fore.CYAN + f"[*] Work mode -> {WORK_MODE}")
    ok = click_chip(driver, WORK_MODE, f"work mode ({WORK_MODE})", silent=True)
    if not ok:
        alt = "In-office" if "home" in WORK_MODE.lower() else "Work from home"
        click_chip(driver, alt, f"work mode alt ({alt})", silent=True)
    time.sleep(1.0)

    # 3. Career goals
    print(Fore.CYAN + f"[*] Career goals -> {len(CAREER_GOALS)} checkbox")
    for goal in CAREER_GOALS:
        clicked = driver.execute_script("""
            const target = arguments[0].toLowerCase().trim();
            const navFilter = 'nav,header,footer,.navbar,.footer,.header,.sidebar';
            for (const tag of ['label', 'div', 'span']) {
                for (const el of document.querySelectorAll(tag)) {
                    if (el.offsetParent === null) continue;
                    if (el.closest(navFilter)) continue;
                    const raw = (el.textContent || '').trim();
                    if (!raw || raw.length > 120) continue;
                    if (!raw.toLowerCase().includes(target)) continue;

                    let cb = el.querySelector('input[type="checkbox"]');
                    if (!cb && el.tagName === 'LABEL' && el.htmlFor) {
                        cb = document.getElementById(el.htmlFor);
                    }
                    if (!cb) {
                        const p = el.closest('label, div');
                        if (p) cb = p.querySelector('input[type="checkbox"]');
                    }
                    if (!cb) continue;

                    if (!cb.checked) {
                        cb.scrollIntoView({block: 'center'});
                        cb.click();
                        cb.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                    return { ok: true, goal: raw };
                }
            }
            return { ok: false };
        """, goal)

        if clicked and clicked.get("ok"):
            print(Fore.GREEN + f"[✓] career goal: {clicked['goal'][:60]!r}")
        else:
            print(Fore.YELLOW + f"[~] career goal gak ketemu: {goal[:50]}")
        time.sleep(0.5)

    # 4. dump state
    print(Fore.CYAN + "\n[i] State step 3:")
    state = driver.execute_script("""
        const navFilter = 'nav,header,footer,.navbar,.footer,.header,.sidebar';
        const out = { chips: [], checks: [] };
        for (const el of document.querySelectorAll('button, label, div, span')) {
            if (el.offsetParent === null) continue;
            if (el.closest(navFilter)) continue;
            const raw = (el.textContent || '').trim();
            if (!raw || raw.length > 60) continue;
            if (el.children.length > 2) continue;
            if (/×$/.test(raw)) out.chips.push(raw);
        }
        for (const cb of document.querySelectorAll('input[type="checkbox"]')) {
            if (cb.offsetParent === null) continue;
            const lbl = cb.closest('label') || cb.parentElement;
            const txt = lbl ? (lbl.textContent || '').trim().slice(0, 50) : '';
            out.checks.push(`[${cb.checked ? 'x' : ' '}] ${txt}`);
        }
        return out;
    """) or {}
    for c in state.get("chips", []):
        print(f"    chip  {c}")
    for c in state.get("checks", []):
        print(f"    check {c}")

    driver.save_screenshot("step3_filled.png")

    # 5. Find me opportunities
    print(Fore.CYAN + "\n[*] klik 'Find me opportunities'...")
    clicked_btn = driver.execute_script("""
        const navFilter = 'nav,header,footer,.navbar,.footer';
        for (const b of document.querySelectorAll('button, a.btn, .btn-primary')) {
            if (b.offsetParent === null) continue;
            if (b.closest(navFilter)) continue;
            const txt = (b.textContent || '').trim().toLowerCase();
            if (/find me opportunities|find opportunities|submit|done|finish/.test(txt)) {
                b.scrollIntoView({block: 'center'});
                b.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                b.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                b.click();
                return txt;
            }
        }
        return null;
    """)

    if clicked_btn:
        print(Fore.GREEN + f"[✓] tombol diklik ({clicked_btn!r})")
    else:
        click_chip(driver, "Find me opportunities", "Find me opportunities", silent=True)

    time.sleep(WAIT_LONG + 3)
    print(Fore.YELLOW + f"[i] URL setelah submit: {driver.current_url}")
    driver.save_screenshot("step3_done.png")
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
    os.makedirs(os.path.dirname(OUTPUT_JSON) or ".", exist_ok=True)
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
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + "   INTERNSHALA SEMI-AUTO SIGNUP (India) — .env")
    print(Fore.CYAN + "=" * 60)
    print(Fore.CYAN + f"   Signup URL : {SIGNUP_URL}")
    print(Fore.CYAN + f"   Step 1 URL : {URL_STEP_1}")
    print(Fore.CYAN + f"   Step 2 URL : {PREF_STEP_2_URL}")
    print(Fore.CYAN + f"   Step 3 URL : {PREF_STEP_3_URL}")
    print(Fore.CYAN + "-" * 60)
    print(Fore.CYAN + f"   Nama       : {NAME}")
    print(Fore.CYAN + f"   Password   : {PASSWORD}")
    print(Fore.CYAN + f"   Phone      : +91 {PHONE}")
    print(Fore.CYAN + f"   City       : {CITY}")
    print(Fore.CYAN + f"   Gender     : {GENDER}")
    print(Fore.CYAN + f"   Type       : {USER_TYPE}")
    print(Fore.CYAN + f"   Languages  : {', '.join(LANGUAGES)}")
    print(Fore.CYAN + f"   Education  : {DEGREE} ({STREAM}) — {COLLEGE_NAME}")
    print(Fore.CYAN + f"   Years      : {START_YEAR} - {END_YEAR}")
    print(Fore.CYAN + f"   Work Type  : {WORK_TYPE} / {WORK_MODE}")
    print(Fore.CYAN + f"   Interests  : {', '.join(INTEREST_AREAS)}")
    print(Fore.CYAN + "=" * 60)

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
