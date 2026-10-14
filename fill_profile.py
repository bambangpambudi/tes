import os
import json
import time
import random
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    ElementNotInteractableException,
)

# ============================================================
#  CONFIG
# ============================================================
PROFILE_URL = "https://internshala.com/student/personal_details"
PROFILE_DIR = str(Path("browser_profile").resolve())
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

PROFILE_DATA = {
    "phone": f"98{random.randint(10000000, 99999999)}",
    "city": "Mumbai",
}

CHIP_DATA = {
    "gender": "Male",
    "user_type": "Fresher",
    "languages": ["English", "Hindi"],
}

EDUCATION_DATA = {
    "college": "University of Mumbai",
    "degree": "B.Tech",
    "stream": "Computer Science",
    "start_year": "2022",
    "end_year": "2026",
}

PREFERENCE_DATA = {
    "work_type": "Internships",
    "work_mode": "Work from home",
    "interests": ["Web Development", "Software Development"],
    "city": "Mumbai",
}

SELECTORS = {
    "phone": [
        "input[name='phone']",
        "input[name='phone_primary']",
        "#phone",
        "#phone_primary",
        "input[type='tel']",
        "input[placeholder*='Mobile' i]",
    ],
    "city": [
        "input[name='current_city']",
        "#current_city",
        "input[placeholder*='Current location' i]",
        "input[placeholder*='city' i]",
    ],
    "college": [
        "input[name='college']",
        "#college",
        "input[placeholder*='college' i]",
        "input[placeholder*='institute' i]",
        "input[placeholder*='BITS' i]",
    ],
    "degree": [
        "input[name='degree']",
        "#degree",
        "input[placeholder*='degree' i]",
    ],
    "stream": [
        "input[name='stream']",
        "#stream",
        "input[placeholder*='stream' i]",
        "input[placeholder*='specialization' i]",
        "input[placeholder*='Computer Science' i]",
    ],
}


# ============================================================
#  DRIVER
# ============================================================
def build_driver(headless=False):
    options = Options()
    options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    options.add_argument("--window-size=1366,900")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    if headless:
        options.add_argument("--headless=new")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )
    return driver


# ============================================================
#  HELPERS
# ============================================================
def find_visible_input(driver, selectors):
    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                if (
                    element.is_displayed()
                    and element.is_enabled()
                    and element.tag_name.lower() in ("input", "textarea")
                    and element.get_attribute("type") != "hidden"
                ):
                    return element
        except StaleElementReferenceException:
            continue
        except Exception:
            continue
    return None


def fill_input(driver, selectors, value, label):
    if not value:
        print(f"[SKIP] {label}: no value configured")
        return False

    element = find_visible_input(driver, selectors)
    if element is None:
        print(f"[ERROR] {label}: input not found")
        return False

    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        WebDriverWait(driver, 10).until(
            lambda d: element.is_displayed() and element.is_enabled()
        )

        ActionChains(driver).move_to_element(element).pause(0.15).click().perform()
        time.sleep(0.2)
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)

        for ch in str(value):
            element.send_keys(ch)
            time.sleep(0.03)

        element.send_keys(Keys.TAB)
        time.sleep(0.3)

        actual = element.get_attribute("value") or ""
        if actual != str(value):
            print(f"[WARN] {label}: value mismatch (actual={actual!r})")
            return False

        print(f"[OK] {label}: {actual!r}")
        return True

    except (TimeoutException, StaleElementReferenceException,
            ElementNotInteractableException) as error:
        print(f"[ERROR] {label}: {type(error).__name__}")
        return False


def fill_autocomplete(driver, selectors, value, label):
    if not value:
        print(f"[SKIP] {label}: no value")
        return False

    element = find_visible_input(driver, selectors)
    if element is None:
        print(f"[ERROR] {label}: input not found")
        return False

    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", element
        )
        ActionChains(driver).move_to_element(element).pause(0.15).click().perform()
        time.sleep(0.2)
        element.send_keys(Keys.CONTROL, "a")
        element.send_keys(Keys.BACKSPACE)

        for ch in str(value):
            element.send_keys(ch)
            time.sleep(0.08)

        time.sleep(2.0)

        clicked = driver.execute_script("""
            const val = arguments[0].toLowerCase();
            const selectors = [
                '.ui-menu-item-wrapper', '.ui-menu-item', '.autocomplete-suggestion',
                '.pac-item', 'ul[role="listbox"] li', '.dropdown-menu li',
                '.autocomplete-items div', '.chosen-results li',
                'ul.ui-autocomplete li', 'div[class*="autocomplete"] li',
                'div[class*="dropdown"] li', 'li[role="option"]', '.option'
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
        """, value)

        if clicked:
            print(f"[OK] {label}: picked {clicked!r}")
            return True
        else:
            print(f"[OK] {label}: typed {value!r} (no dropdown)")
            return True

    except Exception as e:
        print(f"[ERROR] {label}: {e}")
        return False


def click_chip(driver, text, label=None, silent=False):
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
            print(f"[ERROR] {label} NOT FOUND")
        return False

    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target)
        time.sleep(0.3)
        ActionChains(driver).move_to_element(target).pause(0.15).click().perform()
        time.sleep(0.4)

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

        print(f"[OK] {label} clicked ({target.text!r})")
        return True
    except Exception as e:
        if not silent:
            print(f"[ERROR] {label}: {e}")
        return False


def click_next(driver, label="Next"):
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
                if (/^(next|save|continue|save & continue|submit|done)$/i.test(txt)) {
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
        print(f"[OK] {label} clicked ({clicked_txt!r})")
        return True
    print(f"[ERROR] {label} not found")
    return False


def inspect_form(driver):
    results = []
    for element in driver.find_elements(By.CSS_SELECTOR, "input, textarea, select, button"):
        try:
            if not element.is_displayed():
                continue
            results.append({
                "tag": element.tag_name,
                "id": element.get_attribute("id") or "",
                "name": element.get_attribute("name") or "",
                "type": element.get_attribute("type") or "",
                "placeholder": element.get_attribute("placeholder") or "",
                "text": (element.text or "").strip()[:80],
                "enabled": element.is_enabled(),
            })
        except StaleElementReferenceException:
            continue

    path = OUTPUT_DIR / "form_inspection.json"
    path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[INFO] Form inspection saved to {path}")
    for item in results:
        print(item)


# ============================================================
#  STEPS
# ============================================================
def fill_personal_details(driver):
    print("\n=== TAHAP 1: Personal Details ===")

    fill_input(driver, SELECTORS["phone"], PROFILE_DATA["phone"], "phone")
    time.sleep(0.5)

    fill_autocomplete(driver, SELECTORS["city"], PROFILE_DATA["city"], "current_city")
    time.sleep(0.6)

    click_chip(driver, CHIP_DATA["gender"], f"gender ({CHIP_DATA['gender']})")
    time.sleep(0.5)

    for lang in CHIP_DATA["languages"]:
        click_chip(driver, lang, f"language ({lang})")
        time.sleep(0.4)

    click_chip(driver, CHIP_DATA["user_type"], f"user_type ({CHIP_DATA['user_type']})")
    time.sleep(0.5)

    driver.save_screenshot(str(OUTPUT_DIR / "personal_filled.png"))
    print("[OK] Tahap 1 filled. Screenshot: personal_filled.png")

    click_next(driver, "Next (Personal Details)")
    time.sleep(5)
    print(f"[INFO] URL setelah Next: {driver.current_url}")


def fill_education(driver):
    print("\n=== TAHAP 2: Education ===")

    if "education" not in driver.current_url.lower() and \
       not find_visible_input(driver, SELECTORS["college"]):
        print("[SKIP] Halaman education tidak terdeteksi.")
        return False

    fill_autocomplete(driver, SELECTORS["college"],
                      EDUCATION_DATA["college"], "college")
    time.sleep(0.5)

    fill_autocomplete(driver, SELECTORS["degree"],
                      EDUCATION_DATA["degree"], "degree")
    time.sleep(0.5)

    fill_autocomplete(driver, SELECTORS["stream"],
                      EDUCATION_DATA["stream"], "stream")
    time.sleep(0.5)

    for year_key, year_label in [("start_year", "Start Year"), ("end_year", "End Year")]:
        year_val = EDUCATION_DATA[year_key]
        sel_str = (f"select[name='{year_key}'], #{year_key}, "
                   f"input[placeholder*='{year_label}' i]")
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel_str)
            for e in els:
                if e.is_displayed():
                    if e.tag_name.lower() == "select":
                        driver.execute_script("""
                            const el = arguments[0], val = arguments[1];
                            for (const opt of el.options) {
                                if (opt.text.includes(val) || opt.value === val) {
                                    el.value = opt.value;
                                    el.dispatchEvent(new Event('change', {bubbles: true}));
                                    return true;
                                }
                            }
                            return false;
                        """, e, year_val)
                        print(f"[OK] {year_label} = {year_val}")
                    else:
                        e.click()
                        e.send_keys(Keys.CONTROL, "a")
                        e.send_keys(Keys.BACKSPACE)
                        e.send_keys(year_val)
                        print(f"[OK] {year_label} = {year_val}")
                    break
        except Exception as ex:
            print(f"[WARN] {year_label}: {ex}")
        time.sleep(0.4)

    for skill in ["Python", "JavaScript", "HTML"]:
        if not click_chip(driver, skill, f"skill ({skill})", silent=True):
            fill_autocomplete(
                driver,
                ["input[placeholder*='skill' i]", "#skills"],
                skill, f"skill input ({skill})"
            )
        time.sleep(0.3)

    driver.save_screenshot(str(OUTPUT_DIR / "education_filled.png"))
    print("[OK] Tahap 2 filled. Screenshot: education_filled.png")

    click_next(driver, "Save (Education)")
    time.sleep(5)
    print(f"[INFO] URL setelah Save: {driver.current_url}")
    return True


def fill_preferences(driver):
    print("\n=== TAHAP 3: Preferences ===")

    if "preference" not in driver.current_url.lower():
        print("[SKIP] Halaman preferences tidak terdeteksi.")
        return False

    click_chip(driver, PREFERENCE_DATA["work_type"],
               f"work type ({PREFERENCE_DATA['work_type']})", silent=True)
    time.sleep(0.5)

    click_chip(driver, PREFERENCE_DATA["work_mode"],
               f"work mode ({PREFERENCE_DATA['work_mode']})", silent=True)
    time.sleep(0.5)

    for interest in PREFERENCE_DATA["interests"]:
        click_chip(driver, interest, f"interest ({interest})", silent=True)
        time.sleep(0.5)

    click_chip(driver, PREFERENCE_DATA["city"],
               f"preferred city ({PREFERENCE_DATA['city']})", silent=True)
    time.sleep(0.5)

    driver.save_screenshot(str(OUTPUT_DIR / "preferences_filled.png"))
    print("[OK] Tahap 3 filled. Screenshot: preferences_filled.png")

    click_next(driver, "Save (Preferences)")
    time.sleep(5)
    print(f"[INFO] URL akhir: {driver.current_url}")
    return True


# ============================================================
#  MAIN
# ============================================================
def main():
    driver = build_driver(headless=False)

    try:
        driver.get(PROFILE_URL)
        print("[INFO] Internshala Personal Details dibuka.")

        input("[ACTION] Login manual kalau belum. Buka halaman Personal Details. "
              "Tekan Enter kalau sudah siap: ")

        print(f"[INFO] Current URL: {driver.current_url}")
        print(f"[INFO] Page title: {driver.title}")

        if "personal_details" not in driver.current_url.lower():
            print("[WARN] URL bukan Personal Details. Cek login/navigasi dulu.")

        inspect_form(driver)

        fill_personal_details(driver)
        fill_education(driver)
        fill_preferences(driver)

        driver.save_screenshot(str(OUTPUT_DIR / "final_state.png"))
        print(f"\n[INFO] Screenshot akhir: output/final_state.png")
        print(f"[INFO] URL akhir: {driver.current_url}")

        input("[ACTION] Review browser. Tekan Enter untuk tutup: ")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
