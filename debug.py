import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.add_argument("--headless=new")
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1366,900")
opts.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=opts
)

print("[*] buka signup...")
driver.get("https://internshala.com/registration/student")
time.sleep(6)

# simpan HTML
with open("debug.html", "w", encoding="utf-8") as f:
    f.write(driver.page_source)
print("[✓] debug.html tersimpan")

# simpan screenshot
driver.save_screenshot("debug.png")
print("[✓] debug.png tersimpan")

# daftar semua input/button/select
print("\n=== FORM ELEMENTS DI HALAMAN ===")
for tag in ["input", "button", "select", "a"]:
    els = driver.find_elements(By.TAG_NAME, tag)
    for i, el in enumerate(els):
        try:
            el_id = el.get_attribute("id")
            el_name = el.get_attribute("name")
            el_class = el.get_attribute("class")
            el_type = el.get_attribute("type")
            el_ph = el.get_attribute("placeholder")
            el_text = (el.text or "")[:60]
            if el_id or el_name or el_ph:
                print(f"[{tag}] id={el_id!r} name={el_name!r} type={el_type!r} "
                      f"placeholder={el_ph!r} class={el_class!r} text={el_text!r}")
        except Exception:
            pass

print("\n[i] URL akhir:", driver.current_url)
print("[i] Title:", driver.title)

driver.quit()
