import os
import re
import json
import time
import random
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
SIGNUP_URL      = "https://internshala.com/registration/student"
PREF_STEP_2_URL = "https://internshala.com/user_preference/preferences/?referral=personal_details"
PREF_STEP_3_URL = "https://internshala.com/student/preferences"

PASSWORD  = "Dermaga07"
NAME      = "Arya Rahman"
PHONE     = f"98{random.randint(10000000, 99999999)}"
CITY      = "Mumbai"
GENDER    = "Male"
USER_TYPE = "Fresher"
LANGUAGES = ["English", "Hindi"]

COLLEGE_NAME   = "University of Mumbai"
DEGREE         = "B.Tech"
STREAM         = "Computer Science"
START_YEAR     = "2022"
END_YEAR       = "2026"

SKILLS         = ["Python", "JavaScript", "HTML"]
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
    """Isi input signup/OTP via JS (cocok untuk form biasa)."""
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
    """
    Isi input via NATIVE Selenium click + send_keys + ActionChains.
    Fallback ke JS setter kalau native gagal — trigger semua event React.
    """
    el = None
    sel_list = [s.strip() for s in selectors.split(",") if s.strip()]

    # --- cari elemen visible pertama ---
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

    # --- fallback via label ---
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

        # native click via ActionChains
        ActionChains(driver).move_to_element(el).pause(0.15).click().perform()
        time.sleep(0.2)

        # clear
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.DELETE)
        time.sleep(0.15)

        # ketik per karakter
        for ch in str(value):
            el.send_keys(ch)
            time.sleep(0.03)

        # blur → commit React state
        driver.execute_script("arguments[0].blur();", el)
        time.sleep(0.3)

        actual = el.get_attribute("value")
        if actual == str(value):
            print(Fore.GREEN + f"[✓] {label} = {actual!r}")
            return True

        # fallback paksa native setter + semua event
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
                                  label_hint="", silent=False):
    """Isi field autocomplete (city, college, skills, interest)."""
    # cari elemen
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

        time.sleep(2.0)

        # klik saran dropdown
        clicked = driver.execute_script("""
            const val = arguments[0].toLowerCase();
            const selectors = [
                '.ui-menu-item', '.ui-menu-item-wrapper', '.autocomplete-suggestion',
                '.pac-item', 'ul[role="listbox"] li', '.city-dropdown li',
                '.dropdown-menu li', '.autocomplete-items div', '.chosen-results li',
                'ul.ui-autocomplete li', 'div[class*="autocomplete"] li',
                'div[class*="dropdown"] li', 'li[role="option"]',
                'div[class*="suggestion"]', '.option', '.result-item'
            ];
            const items = Array.from(document.querySelectorAll(selectors.join(', ')));
            for (const item of items) {
                const rect = item.getBoundingClientRect();
                if ((item.offsetParent !== null || rect.width > 10)
                    && item.textContent.toLowerCase().includes(val)) {
                    item.scrollIntoView({block: 'nearest'});
                    item.dispatchEvent(new MouseEvent('mouseover', {bubbles: true}));
                    item.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}));
                    item.dispatchEvent(new MouseEvent('mouseup', {bubbles: true}));
                    item.click();
                    return item.textContent.trim();
                }
            }
            return null;
        """, text_value)

        if clicked:
            print(Fore.GREEN + f"[✓] {label} dipilih: {clicked!r}")
            return True
        else:
            # gak ada dropdown — paksa commit value
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
    Klik chip pakai ActionChains — trigger React onClick real.
    """
    label = label or text
    target = None

    xpaths = [
        f"//button[normalize-space(.)='{text}']",
        f"//label[normalize-space(.)='{text}']",
        f"//div[normalize-space(.)='{text}']",
        f"//span[normalize-space(.)='{text}']",
        f"//*[contains(normalize-space(.), '{text}') and "
        f"string-length(normalize-space(.)) < {len(text)+10}]",
    ]

    for xp in xpaths:
        try:
            els = driver.find_elements(By.XPATH, xp)
            for e in els:
                if e.is_displayed() and e.is_enabled():
                    try:
                        in_nav = driver.execute_script(
                            "return !!arguments[0].closest('nav,header,footer,.navbar,.footer');",
                            e
                        )
                        if in_nav:
                            continue
                    except Exception:
                        pass
                    target = e
                    break
            if target:
                break
        except Exception:
            continue

    if not target:
        if not silent:
            print(Fore.RED + f"[!] {label} NOT FOUND")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
        time.sleep(0.3)
        ActionChains(driver).move_to_element(target).pause(0.15).click().perform()
        time.sleep(0.4)

        # klik parent wrapper (label/button) juga
        try:
            parent = target.find_element(
                By.XPATH,
                "./ancestor::label[1] | ./ancestor::button[1]"
            )
            if parent and parent != target:
                ActionChains(driver).move_to_element(parent).pause(0.1).click().perform()
                time.sleep(0.2)
        except Exception:
            pass

        print(Fore.GREEN + f"[✓] {label} clicked ({target.text!r})")
        return True
    except Exception as e:
        if not silent:
            print(Fore.RED + f"[!] {label} click FAILED: {e}")
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
                if (/^(next|save|continue|save & continue|save and continue|submit|done|let's go)$/i.test(txt)) {
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
            print(Fore.RED + f"[!] OTP harus 6 digit (baru {len(user_input)}).")
            continue
        otp = user_input

    print(Fore.CYAN + f"[*] isi OTP: {otp}")
    ok = js_fill(
        driver,
        "input[name='otp'], input#otp, input[name='verification_code'], "
        "input[type='text'], input[type='number']",
        otp,
        "otp"
    )
    if not ok:
        print(Fore.RED + "[!] gagal isi OTP")
        return False

    time.sleep(1)
    click_chip(driver, "verify", "verify", silent=True)
    if is_verify_page(driver):
        click_chip(driver, "submit", "submit", silent=True)
    time.sleep(WAIT_LONG)

    if is_verify_page(driver):
        print(Fore.RED + "[!] masih di halaman verifikasi.")
        return False

    print(Fore.GREEN + "[✓] verifikasi berhasil.")
    return True


# ============================================================
#  ONBOARDING SECTIONS
# ============================================================
def fill_skills_and_education_section(driver):
    print(Fore.CYAN + "\n[*] memeriksa bagian Education / #skills-section...")
    time.sleep(2)
    close_modals(driver)

    click_chip(driver, "Graduation", "Education Type (Graduation)", silent=True)
    fill_autocomplete_onboarding(
        driver,
        "#college, input[name='college'], "
        "input[placeholder*='college' i], input[placeholder*='institute' i]",
        COLLEGE_NAME, "College", label_hint="college", silent=True
    )
    fill_autocomplete_onboarding(
        driver,
        "#degree, input[name='degree'], input[placeholder*='degree' i]",
        DEGREE, "Degree", label_hint="degree", silent=True
    )
    fill_autocomplete_onboarding(
        driver,
        "#stream, input[name='stream'], input[placeholder*='stream' i], "
        "input[placeholder*='specialization' i]",
        STREAM, "Stream", label_hint="stream", silent=True
    )
    select_dropdown_or_chip(
        driver,
        "#start_year, select[name='start_year'], input[name='start_year'], "
        "input[placeholder*='start year' i]",
        START_YEAR, "Start Year", silent=True
    )
    select_dropdown_or_chip(
        driver,
        "#end_year, select[name='end_year'], input[name='end_year'], "
        "input[placeholder*='end year' i]",
        END_YEAR, "End Year", silent=True
    )

    for skill in SKILLS:
        if not click_chip(driver, skill, f"Skill Chip ({skill})", silent=True):
            fill_autocomplete_onboarding(
                driver,
                "input[placeholder*='skill' i], #skills, input[name*='skill' i]",
                skill, f"Skill Input ({skill})", label_hint="skills", silent=True
            )
        time.sleep(0.3)

    driver.save_screenshot("step1_skills_education.png")
    click_next_or_save(driver, "Next (Skills/Education)")
    time.sleep(WAIT_LONG)


def fill_user_preferences_step(driver, step_label="Preferences"):
    print(Fore.CYAN + f"\n[*] mengisi halaman {step_label} ({driver.current_url})...")
    time.sleep(2.5)
    close_modals(driver)
    driver.save_screenshot(f"{step_label.lower().replace(' ', '_')}_start.png")

    click_chip(driver, WORK_TYPE, f"Looking for ({WORK_TYPE})", silent=True)
    time.sleep(0.5)

    click_chip(driver, WORK_MODE, f"Work Mode ({WORK_MODE})", silent=True)
    time.sleep(0.5)

    for interest in INTEREST_AREAS:
        if not click_chip(driver, interest, f"Interest Chip ({interest})", silent=True):
            fill_autocomplete_onboarding(
                driver,
                "input[placeholder*='interest' i], input[placeholder*='category' i], "
                "input[placeholder*='domain' i], input[placeholder*='search' i], "
                "input[placeholder*='profile' i], #preferences_search",
                interest, f"Interest Search ({interest})",
                label_hint="interest", silent=True
            )
        time.sleep(0.5)

    if not click_chip(driver, CITY, f"Preferred City Chip ({CITY})", silent=True):
        fill_autocomplete_onboarding(
            driver,
            "input[placeholder*='city' i], input[placeholder*='location' i], "
            "#preferred_city",
            CITY, "Preferred City", label_hint="location", silent=True
        )
    time.sleep(0.5)

    driver.save_screenshot(f"{step_label.lower().replace(' ', '_')}_filled.png")
    click_next_or_save(driver, f"Save/Next ({step_label})")
    time.sleep(WAIT_LONG)
    print(Fore.YELLOW + f"[i] URL setelah {step_label}: {driver.current_url}")


def fill_onboarding(driver):
    print(Fore.CYAN + "\n[*] TAHAP 1: Mengisi Personal Details ('Let's get started')...")

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.CSS_SELECTOR,
                "input[placeholder*='Mobile' i], input[placeholder*='location' i], "
                "#phone, #current_city"
            ))
        )
    except Exception:
        print(Fore.YELLOW + "[~] Menunggu render halaman Personal Details...")

    time.sleep(2)
    close_modals(driver)
    driver.save_screenshot("onboarding_start.png")
    print(Fore.YELLOW + f"[i] URL Tahap 1: {driver.current_url}")

    # 1. PHONE
    fill_input_onboarding(
        driver,
        "input[placeholder*='Mobile number' i], input[placeholder*='Mobile' i], "
        "#phone, #phone_primary, input[name='phone'], "
        "input[name='phone_primary'], input[type='tel']",
        PHONE, "Contact number (Phone)", label_hint="contact number"
    )
    time.sleep(0.5)

    # 2. CURRENT CITY
    fill_autocomplete_onboarding(
        driver,
        "input[placeholder*='Current location' i], input[placeholder*='location' i], "
        "#current_city, input[name='current_city'], input[placeholder*='city' i]",
        CITY, "Current city", label_hint="current city"
    )
    time.sleep(0.6)

    # 3. GENDER
    click_chip(driver, GENDER, f"Gender ({GENDER})")
    time.sleep(0.5)

    # 4. LANGUAGES
    for lang in LANGUAGES:
        click_chip(driver, lang, f"Language ({lang})")
        time.sleep(0.4)

    # 5. TYPE
    if not click_chip(driver, USER_TYPE, f"Type ({USER_TYPE})"):
        click_chip(driver, "College student", "Type (College student)")
    time.sleep(0.5)

    driver.save_screenshot("onboarding_filled.png")

    # 6. Next
    print(Fore.CYAN + "[*] klik Next pada Personal Details...")
    click_next_or_save(driver, "Next (Personal Details)")
    time.sleep(WAIT_LONG)

    err = get_form_errors(driver)
    if err:
        print(Fore.YELLOW + f"[~] Validasi Tahap 1: {err}")
        new_phone = f"99{random.randint(10000000, 99999999)}"
        fill_input_onboarding(
            driver,
            "input[placeholder*='Mobile number' i], input[placeholder*='Mobile' i], "
            "#phone, #phone_primary, input[type='tel']",
            new_phone, "Contact number (Retry)", label_hint="contact number"
        )
        time.sleep(0.5)
        click_next_or_save(driver, "Next (Retry)")
        time.sleep(WAIT_LONG)

    print(Fore.YELLOW + f"[i] URL setelah Next pertama: {driver.current_url}")
    driver.save_screenshot("after_step1_next.png")

    if "skills-section" in driver.current_url.lower() or "college" in driver.page_source.lower():
        fill_skills_and_education_section(driver)
        print(Fore.YELLOW + f"[i] URL setelah Skills/Education: {driver.current_url}")

    if "user_preference" in driver.current_url.lower():
        fill_user_preferences_step(driver, "Tahap 2 - User Preferences")
    elif "personal_details" not in driver.current_url.lower():
        driver.get(PREF_STEP_2_URL)
        time.sleep(WAIT_LONG)
        if "user_preference" in driver.current_url.lower():
            fill_user_preferences_step(driver, "Tahap 2 - User Preferences")

    if "student/preferences" in driver.current_url.lower():
        fill_user_preferences_step(driver, "Tahap 3 - Student Preferences")
    elif "personal_details" not in driver.current_url.lower() \
         and "dashboard" not in driver.current_url.lower():
        driver.get(PREF_STEP_3_URL)
        time.sleep(WAIT_LONG)
        if "student/preferences" in driver.current_url.lower():
            fill_user_preferences_step(driver, "Tahap 3 - Student Preferences")

    driver.save_screenshot("onboarding_complete.png")
    print(Fore.GREEN + f"[✓] Onboarding selesai! URL akhir: {driver.current_url}")
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
