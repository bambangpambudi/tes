import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

URL = "https://internshala.com/registration/student"

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1366,900")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=opts
)

print("[*] buka halaman...")
driver.get(URL)
time.sleep(6)

with open("debug.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
driver.save_screenshot("debug.png")
print("[✓] debug.html + debug.png tersimpan")

print("\n=== FORM ELEMENTS ===")
for tag in ["input", "button", "select", "a", "textarea"]:
    for el in driver.find_elements(By.TAG_NAME, tag):
        try:
            el_id = el.get_attribute("id")
            el_name = el.get_attribute("name")
            el_type = el.get_attribute("type")
            el_ph = el.get_attribute("placeholder")
            el_cls = el.get_attribute("class")
            el_txt = (el.text or "")[:60]
            if el_id or el_name or el_ph:
                print(f"[{tag}] id={el_id!r} name={el_name!r} type={el_type!r} "
                      f"placeholder={el_ph!r} class={el_cls!r} text={el_txt!r}")
        except Exception:
            pass

print(f"\n[i] URL: {driver.current_url}")
print(f"[i] Title: {driver.title}")

driver.quit()
