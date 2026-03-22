import os
import platform
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
import re
import unicodedata
import time
import random
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


COUNTRIES_DATA = {
    "thailand": {
        "title": "Правила въезда в Таиланд для граждан РФ",
        "category": "въезд, виза, TDAC, безвиз, документы",
        "sources": [
            {
                "url": "https://www.kdmid.ru/docs/thailand/information-about-the-country",
                "source_name": "МИД РФ — общая информация",
            },
            {
                "url": "https://tdac.immigration.go.th/manual/en/index.html",
                "source_name": "TDAC manual (обязательный цифровой arrival card)",
            },
            {
                "url": "https://tdac.immigration.go.th/manual/en/faq.html",
                "source_name": "TDAC FAQ",
            },
            # immigration.go.th/?p=entry_requirements — стабильно 403 + Cloudflare; не парсится.
            {
                "url": "https://thaiconsulatela.thaiembassy.org/en/publicservice/visa-exemption-and-visa-on-arrival-to-thailand",
                "source_name": "Visa Exemption & VOA — зеркало (актуальный список 93 стран)",
            },
            {
                "url": "https://www.thaievisa.go.th/",
                "source_name": "Thai e-Visa Official Portal",
            },
        ]
    },

    "vietnam": {
        "title": "Правила въезда во Вьетнам для граждан РФ",
        "category": "въезд, виза, e-visa, безвиз",
        "sources": [
            {
                "url": "https://www.kdmid.ru/docs/vietnam/information-about-the-country",
                "source_name": "МИД РФ — общая информация",
            },
            {
                "url": "https://evisa.xuatnhapcanh.gov.vn/web/guest/khai-thi-thuc-dien-tu-cap-moi",
                "source_name": "Vietnam e-Visa official portal",
            },
        ]
    },

    "turkey": {
        "title": "Правила въезда в Турцию для граждан РФ",
        "category": "въезд, безвиз, страховка, миграционная карта",
        "sources": [
            {
                "url": "https://www.kdmid.ru/docs/turkey/information-about-the-country",
                "source_name": "МИД РФ — общая информация",
            },
            {
                "url": "https://www.mfa.gov.tr/visa-information-for-foreigners.en.mfa",
                "source_name": "MFA Turkey — Visa Information",
            },
        ]
    },

    "uae": {
        "title": "Правила въезда в ОАЭ для граждан РФ",
        "category": "въезд, виза, транзит",
        "sources": [
            {
                "url": "https://www.kdmid.ru/docs/united-arab-emirates/information-about-the-country",
                "source_name": "МИД РФ — общая информация",
            },
            {
                "url": "https://www.mofa.gov.ae/en/missions/moscow",
                "source_name": "Посольство ОАЭ в Москве (справочно)",
            },
        ]
    },

    "srilanka": {
        "title": "Правила въезда на Шри-Ланку для граждан РФ",
        "category": "въезд, виза, ETA",
        "sources": [
            {
                "url": "https://www.kdmid.ru/docs/sri-lanka/information-about-the-country",
                "source_name": "МИД РФ — общая информация",
            },
            {
                "url": "https://www.eta.gov.lk/slvisa/",
                "source_name": "ETA Sri Lanka (справочно)",
            },
        ]
    },
}


OUTPUT_DIR = Path("backend/data/knowledge")

def _chrome_executable() -> str | None:
    """Path to Chrome/Chromium. Set CHROME_BINARY if installed in a non-standard location."""
    env = os.environ.get("CHROME_BINARY", "").strip()
    if env and Path(env).is_file():
        return env
    system = platform.system()
    candidates: list[str] = []
    if system == "Darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    elif system == "Linux":
        candidates = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    elif system == "Windows":
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ]
    for p in candidates:
        if p and Path(p).is_file():
            return p
    return None


def _headless_enabled() -> bool:
    return os.environ.get("PARSING_HEADLESS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def _is_bot_or_waf_interstitial(text: str) -> bool:
    """Страница Cloudflare / антибот: много символов, но не контент для RAG."""
    if not text or len(text) < 200:
        return False
    low = text.lower()
    ru = "проверки безопасности" in low or "проверка безопасности" in low
    ru_bot = "бот" in low or "вредоносных ботов" in low
    if ru and ru_bot:
        return True
    if "security check" in low and "bot" in low:
        return True
    if "checking your browser" in low:
        return True
    if "just a moment" in low and "cloudflare" in low:
        return True
    if "cf-browser-verification" in low or "challenge-platform" in low:
        return True
    return False


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

def fetch_with_requests(url, max_retries=4):
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504, 403],
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers.update(HEADERS)

    try:
        response = session.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = extract_clean_text(soup)
        if len(text) > 500 and not _is_bot_or_waf_interstitial(text):
            return text
        if _is_bot_or_waf_interstitial(text):
            print(
                "  requests: похоже на страницу антибота/WAF, а не на контент — пропускаем"
            )
        else:
            print(
                f"  requests: мало извлечённого текста ({len(text)} симв.) — часто JS/антибот/редирект"
            )
    except Exception as e:
        print(f"  requests failed: {e}")
    return None

def fetch_with_undetected(url):
    print("   → undetected-chromedriver")
    chrome_path = _chrome_executable()
    if not chrome_path:
        print(
            "  undetected skipped: не найден Google Chrome/Chromium. "
            "Установите Chrome (macOS: Chrome.app) или задайте CHROME_BINARY=/полный/путь/к/chrome"
        )
        return None

    options = uc.ChromeOptions()
    if _headless_enabled():
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument(f"--user-agent={HEADERS['User-Agent']}")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")

    driver = None
    try:
        driver = uc.Chrome(
            options=options,
            browser_executable_path=chrome_path,
            use_subprocess=True,
        )
        driver.get(url)
        time.sleep(8 + random.uniform(3, 6))

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4 + random.uniform(2, 4))

        try:
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main, article, .content, #content, body > div"))
            )
        except:
            pass

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        text = extract_clean_text(soup)
        if len(text) > 500 and not _is_bot_or_waf_interstitial(text):
            return text
        if _is_bot_or_waf_interstitial(text):
            print(
                "  undetected: страница антибота/WAF (не реальный контент) — пробуем дальше"
            )
        else:
            print(
                f"  undetected: мало текста ({len(text)} симв.) — капча, гео-блок, headless или контент в iframe"
            )
    except Exception as e:
        print(f"  undetected failed: {e}")
    finally:
        if driver is not None:
            try:
                driver.quit()
            except:
                pass
    return None

def fetch_fallback_selenium(url):
    print("   → fallback selenium + webdriver-manager")
    chrome_path = _chrome_executable()
    if not chrome_path:
        print(
            "  fallback skipped: не найден Chrome. Установите Google Chrome или задайте CHROME_BINARY"
        )
        return None

    options = webdriver.ChromeOptions()
    options.binary_location = chrome_path
    if _headless_enabled():
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--user-agent={HEADERS['User-Agent']}")

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_window_size(1920, 1080)
        driver.get(url)
        time.sleep(10 + random.uniform(3, 6))
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(4)
        html = driver.page_source
        text = extract_clean_text(BeautifulSoup(html, "html.parser"))
        if len(text) > 500 and not _is_bot_or_waf_interstitial(text):
            return text
        if _is_bot_or_waf_interstitial(text):
            print(
                "  fallback: антибот/WAF вместо контента — пробуем дальше"
            )
        else:
            print(f"  fallback: мало текста ({len(text)} симв.) после Selenium")
    except Exception as e:
        print(f"  fallback failed: {e}")
    finally:
        if 'driver' in locals():
            try:
                driver.quit()
            except:
                pass
    return None

def extract_clean_text(soup):
    unwanted = ["script", "style", "noscript", "iframe", "form", "svg", "meta", "link", "head", "footer", "nav"]
    for tag in unwanted:
        for elem in soup.find_all(tag):
            elem.decompose()

    lines = []
    for tag in soup.find_all(['h1','h2','h3','h4','h5','h6','p','li','td','th','strong','em','div','span','section','article']):
        text = tag.get_text(separator=" ", strip=True)
        if len(text) < 2:
            continue
        if tag.name.startswith('h'):
            lines.append(f"\n{text.upper()}\n{'-' * len(text)}\n")
        elif tag.name == 'li':
            lines.append(f"• {text}")
        else:
            lines.append(text)

    return "\n\n".join(lines)

def fetch_page_text(url):
    for attempt in range(1, 4):
        print(f"  Попытка {attempt}/3...")
        text = fetch_with_requests(url)
        if text:
            return text

        text = fetch_with_undetected(url)
        if text:
            return text

        text = fetch_fallback_selenium(url)
        if text:
            return text

        time.sleep(5 + random.uniform(3, 8))

    return None

def main(countries=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if countries is None:
        countries = list(COUNTRIES_DATA.keys())

    for country_code in countries:
        if country_code not in COUNTRIES_DATA:
            print(f"Страна {country_code} не найдена в конфиге!")
            continue

        data = COUNTRIES_DATA[country_code]
        title = data["title"]
        category = data.get("category", "въезд, виза")
        sources = data["sources"]

        output_file = OUTPUT_DIR / f"{country_code}_all_sources.md"

        print(f"\n=== Обрабатываем страну: {country_code.upper()} ===")
        print(f"Файл: {output_file.name}")

        with open(output_file, "w", encoding="utf-8") as f:
            # f.write(f"# {title} для граждан РФ (март 2026)\n")
            # f.write(f"last_updated: {datetime.now().strftime('%Y-%m-%d')}\n")
            # f.write(f"category: {category}\n\n")

            # f.write(f"АКТУАЛЬНО НА {datetime.now().strftime('%B %Y').upper()}:\n\n")

            for item in sources:
                url = item["url"]
                source = item["source_name"]

                print(f"\n  {source}")
                print(f"  {url}")

                text = fetch_page_text(url)

                if text:
                    f.write(f"## Источник: {source}\n")
                    f.write(f"source_url: {url}\n")
                    f.write(f"country: {country_code}\n")
                    f.write(f"date_fetched: {datetime.now().strftime('%Y-%m-%d')}\n\n")
                    f.write(text + "\n\n")
                    f.write("═" * 100 + "\n\n")
                    print(f"    OK  ({len(text):,} символов)")
                else:
                    print("    FAIL")
                    f.write(f"## {source} — НЕ УДАЛОСЬ ЗАГРУЗИТЬ\n")
                    f.write(f"source_url: {url}\n\n")

        print(f"Готово для {country_code}: {output_file.absolute()}\n")

if __name__ == "__main__":
    main()