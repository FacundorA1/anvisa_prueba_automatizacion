import os
import time
import pandas as pd
import traceback 
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.service import Service
import logging
from pathlib import Path

URL = "https://app.powerbi.com/view?r=eyJrIjoiMjg2Y2ZlNjMtNDVkZS00YTYwLTkzNTMtYTYwYTQwODRiZjk5IiwidCI6ImI2N2FmMjNmLWMzZjMtNGQzNS04MGM3LWI3MDg1ZjVlZGQ4MSJ9"


def crear_driver():
    options = Options()
    
    options.binary_location = os.getenv(
        "CHROME_BIN",
        "/usr/bin/chromium"
    )
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    service = Service(
        executable_path=os.getenv(
            "CHROMEDRIVER_PATH",
            "/usr/bin/chromedriver"
        )
    )

    driver = webdriver.Chrome(options=options, service=service)
    return driver

def scraper_registros():
    df = pd.DataFrame()  
    HOY = datetime.now().strftime("%Y-%m-%d")

    driver = crear_driver()
    try:
        driver.get(URL)
        wait = WebDriverWait(driver, 4)

        table_ex = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.visual-tableEx div.tableEx")
        ))

        grid = table_ex.find_element(By.CSS_SELECTOR, "div[role='grid'].innerContainer")
        top_viewport = table_ex.find_element(By.CSS_SELECTOR, "div.top-viewport")
        mid_viewport = table_ex.find_element(By.CSS_SELECTOR, "div.mid-viewport")

        headers = [h.get_attribute("innerText").strip()
                   for h in top_viewport.find_elements(By.CSS_SELECTOR, "[role='columnheader']")]
        headers = [h for h in headers if h]

        def read_visible_rows():
            rows = []
            row_elems = mid_viewport.find_elements(By.CSS_SELECTOR, "div[role='row'][aria-rowindex]")
            for r in row_elems:
                try:
                    cells = r.find_elements(By.CSS_SELECTOR, "div[role='gridcell']")
                    vals = [c.get_attribute("innerText").strip() for c in cells]
                    if any(vals):
                        rows.append(tuple(vals))
                except StaleElementReferenceException:
                    continue
            return rows

        try:
            total_rows = int(grid.get_attribute("aria-rowcount") or "0")
        except:
            total_rows = 0

        seen, data = set(), []
        for row in read_visible_rows():
            if row not in seen:
                seen.add(row); data.append(row)

        same_scrolls, last_top = 0, -1
        while True:
            driver.execute_script("arguments[0].scrollTop += 600;", mid_viewport)
            time.sleep(0.6)

            new = 0
            for row in read_visible_rows():
                if row not in seen:
                    seen.add(row); data.append(row); new += 1

            cur_top = driver.execute_script("return arguments[0].scrollTop;", mid_viewport)
            same_scrolls = same_scrolls + 1 if cur_top == last_top else 0
            last_top = cur_top

            if (new == 0 and same_scrolls >= 5) or (total_rows and len(data) >= (total_rows - 1)):
                break

        max_cols = max((len(r) for r in data), default=0)
        data_norm = [list(r) + [""]*(max_cols-len(r)) for r in data]
        if headers and len(headers) == max_cols:
            df = pd.DataFrame(data_norm, columns=headers)
        else:
            df = pd.DataFrame(data_norm, columns=[f"col_{i+1}" for i in range(max_cols)])

        df["fecha_extraccion"] = HOY
        if "Selección de fila" in df.columns:
            df = df.drop(columns=["Selección de fila"])
            
    finally:
        try:
            driver.quit()
        except:
                pass

    return df

def guardar_resultados(df: pd.DataFrame) -> tuple[Path, Path]:
    # En Docker será /app/output.
    # Ejecutándolo directamente en Windows será ./output.
    output_dir = Path(
        os.getenv(
            "OUTPUT_DIR",
            Path(__file__).resolve().parent / "output"
        )
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # Fecha explícitamente correspondiente a Uruguay
    hoy = datetime.now().strftime("%Y-%m-%d")

    outfile_diario = (
        output_dir /
        f"anvisa_solicitudes_{hoy}.csv"
    )

    outfile_historico = (
        output_dir /
        "anvisa_solicitudes_historico.csv"
    )

    # El archivo diario se reemplaza si ya existe
    df.to_csv(
        outfile_diario,
        index=False,
        encoding="utf-8-sig",
        sep=";"
    )

    # El histórico se crea o se agrega al final
    historico_existe = outfile_historico.exists()

    df.to_csv(
        outfile_historico,
        index=False,
        encoding="utf-8-sig",
        sep=";",
        mode="a" if historico_existe else "w",
        header=not historico_existe
    )

    return outfile_diario, outfile_historico



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s - "
            "%(levelname)s - "
            "%(message)s"
        )
    )

    try:
        logging.info(
            "Iniciando scraping diario..."
        )

        df = scraper_registros()

        filas = len(df)

        logging.info(
            f"Scraping finalizado. "
            f"Filas obtenidas: {filas}"
        )

        outfile, outfile_historico = (
            guardar_resultados(df)
        )

        print(
            f"Guardado: {outfile} "
            f"(filas={filas})"
        )

        print(
            f"Histórico actualizado: "
            f"{outfile_historico}"
        )

        logging.info(
            f"Archivo diario guardado: "
            f"{outfile}"
        )

        logging.info(
            f"Archivo histórico actualizado: "
            f"{outfile_historico}"
        )

    except Exception:
        logging.exception(
            "Error durante el scraping"
        )
        raise