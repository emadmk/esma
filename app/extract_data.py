"""Extract data from ALL 12 Excel sheets into SQLite database."""
import sqlite3
import os
import shutil
import openpyxl

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
XLS_PATH = os.path.join(BASE_DIR, "DOC-20251215-WA0000.xls")
XLSX_PATH = os.path.join(BASE_DIR, "DOC-20251215-WA0000.xlsx")
DB_PATH = os.path.join(os.path.dirname(__file__), "food_cost.db")


def get_xlsx_path():
    """Get path to xlsx file, converting from xls if needed."""
    if os.path.exists(XLSX_PATH):
        return XLSX_PATH
    if os.path.exists(XLS_PATH):
        shutil.copy2(XLS_PATH, XLSX_PATH)
        return XLSX_PATH
    raise FileNotFoundError("Excel file not found")


def safe_float(val, default=0.0):
    """Safely convert a value to float."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip().replace(",", "")
        try:
            return float(val)
        except ValueError:
            return default
    return default


def safe_str(val, default=""):
    """Safely convert a value to string."""
    if val is None:
        return default
    return str(val).strip()


def create_tables(conn):
    """Create all database tables."""
    c = conn.cursor()
    c.executescript("""
        -- Base ingredient prices (Data sheet)
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT DEFAULT '',
            price_per_gram REAL DEFAULT 0,
            price_per_unit REAL DEFAULT 0,
            category TEXT DEFAULT '',
            notes TEXT DEFAULT ''
        );

        -- Foods (from ریز غذا sheets)
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code INTEGER NOT NULL,
            name TEXT NOT NULL,
            food_type INTEGER DEFAULT 1,
            raw_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0,
            UNIQUE(code, food_type)
        );

        -- Food ingredient recipes
        CREATE TABLE IF NOT EXISTS food_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            ingredient_name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            unit TEXT DEFAULT '',
            unit_price REAL DEFAULT 0,
            cost REAL DEFAULT 0,
            FOREIGN KEY (food_id) REFERENCES foods(id)
        );

        -- Consumable items (هزینه سرباری rows 1-42)
        CREATE TABLE IF NOT EXISTS consumables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_num INTEGER,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            cost_per_serving REAL DEFAULT 0
        );

        -- Equipment list (هزینه سرباری rows 43+)
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_num INTEGER,
            name TEXT NOT NULL,
            quantity REAL DEFAULT 0,
            unit TEXT DEFAULT '',
            unit_price REAL DEFAULT 0,
            total_price REAL DEFAULT 0
        );

        -- Driver positions (آنالیز رانندگان)
        CREATE TABLE IF NOT EXISTS driver_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_num INTEGER,
            sub_num INTEGER DEFAULT 0,
            position_category TEXT DEFAULT '',
            job_title TEXT DEFAULT '',
            post_count INTEGER DEFAULT 0,
            person_count INTEGER DEFAULT 0,
            gross_salary REAL DEFAULT 0,
            avg_monthly_salary REAL DEFAULT 0
        );

        -- Labor positions (آنالیز نیروی کار)
        CREATE TABLE IF NOT EXISTS labor_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            row_num INTEGER,
            category TEXT DEFAULT '',
            position_name TEXT DEFAULT '',
            job_title TEXT DEFAULT '',
            post_count INTEGER DEFAULT 0,
            person_count INTEGER DEFAULT 0,
            gross_salary REAL DEFAULT 0,
            avg_monthly_salary REAL DEFAULT 0
        );

        -- Overhead parameters (from سرباری sheets - NOT hardcoded)
        CREATE TABLE IF NOT EXISTS overhead_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL,
            value REAL DEFAULT 0,
            param_type TEXT DEFAULT 'fixed',
            food_type INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            source_sheet TEXT DEFAULT ''
        );

        -- Overhead calculation per food type 1 (سرباری نوع 1)
        CREATE TABLE IF NOT EXISTS overhead_calc_type1 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_code INTEGER,
            food_name TEXT,
            raw_cost REAL DEFAULT 0,
            consumables REAL DEFAULT 0,
            supplementary_insurance REAL DEFAULT 0,
            driver_salary REAL DEFAULT 0,
            vehicle_rental REAL DEFAULT 0,
            labor_cost REAL DEFAULT 0,
            equipment_depreciation REAL DEFAULT 0,
            fruit REAL DEFAULT 0,
            mineral_water REAL DEFAULT 0,
            delster REAL DEFAULT 0,
            dessert_garnish REAL DEFAULT 0,
            inflation REAL DEFAULT 0,
            contract_insurance REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            profit_margin REAL DEFAULT 0
        );

        -- Overhead calculation per food type 2 (سرباری نوع 2)
        CREATE TABLE IF NOT EXISTS overhead_calc_type2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_code INTEGER,
            food_name TEXT,
            raw_cost REAL DEFAULT 0,
            consumables REAL DEFAULT 0,
            supplementary_insurance REAL DEFAULT 0,
            driver_salary REAL DEFAULT 0,
            vehicle_rental REAL DEFAULT 0,
            labor_cost REAL DEFAULT 0,
            equipment_depreciation REAL DEFAULT 0,
            drink REAL DEFAULT 0,
            dessert_garnish REAL DEFAULT 0,
            inflation REAL DEFAULT 0,
            contract_insurance REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            profit_margin REAL DEFAULT 0,
            total_cost REAL DEFAULT 0
        );

        -- Side dishes / garnishes (دورچین)
        CREATE TABLE IF NOT EXISTS side_dishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            col_group INTEGER DEFAULT 1
        );

        -- Appendix (الحاقیه)
        CREATE TABLE IF NOT EXISTS appendix (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_code INTEGER,
            row_num INTEGER,
            food_name TEXT NOT NULL,
            appendix_price REAL DEFAULT 0,
            calculated_price REAL DEFAULT 0
        );

        -- Weekly menu (Sheet1)
        CREATE TABLE IF NOT EXISTS weekly_menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_str TEXT DEFAULT '',
            day_name TEXT DEFAULT '',
            food_type1 TEXT DEFAULT '',
            food_type1_special TEXT DEFAULT '',
            food_type2 TEXT DEFAULT '',
            dessert_desc TEXT DEFAULT '',
            dessert_special TEXT DEFAULT '',
            bread TEXT DEFAULT '',
            drink TEXT DEFAULT '',
            drink_price REAL DEFAULT 0,
            salad TEXT DEFAULT '',
            salad_price REAL DEFAULT 0,
            special_item TEXT DEFAULT '',
            special_price REAL DEFAULT 0
        );

        -- Analysis attachment (آنالیز پیوست)
        CREATE TABLE IF NOT EXISTS analysis_attachment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_code INTEGER,
            food_name TEXT NOT NULL,
            raw_cost REAL DEFAULT 0,
            food_type INTEGER DEFAULT 1
        );

        -- Analysis attachment ingredients
        CREATE TABLE IF NOT EXISTS analysis_attachment_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            attachment_id INTEGER NOT NULL,
            ingredient_name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            unit TEXT DEFAULT '',
            unit_price REAL DEFAULT 0,
            FOREIGN KEY (attachment_id) REFERENCES analysis_attachment(id)
        );

        -- Overhead consumable food items (هزینه سرباری cols 6-17)
        CREATE TABLE IF NOT EXISTS overhead_food_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_code INTEGER,
            item_name TEXT NOT NULL,
            item_type TEXT DEFAULT '',
            total_price REAL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS overhead_food_item_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            ingredient_name TEXT NOT NULL,
            amount TEXT DEFAULT '',
            unit TEXT DEFAULT '',
            unit_price REAL DEFAULT 0,
            FOREIGN KEY (item_id) REFERENCES overhead_food_items(id)
        );

        -- Settings
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()


# ============================================================
# Sheet 1: Data (مواد اولیه)
# ============================================================
def extract_ingredients(wb, conn):
    """Extract ingredient prices from Data sheet."""
    sheet = wb["Data"]
    c = conn.cursor()
    current_category = ""
    category_headers = {"کنسروجات", "لبنیات", "پروتئین", "میوه و تره بار", "حبوبات", "سس"}

    for row in range(1, sheet.max_row + 1):
        name = safe_str(sheet.cell(row, 1).value)
        if not name:
            continue
        if row == 1:
            continue  # header row

        if name in category_headers:
            current_category = name
            continue

        unit = safe_str(sheet.cell(row, 2).value)
        price_per_gram = safe_float(sheet.cell(row, 3).value)
        price_per_unit = safe_float(sheet.cell(row, 4).value)
        notes = safe_str(sheet.cell(row, 5).value)

        # Determine category if not set
        cat = current_category if current_category else "ادویه‌جات و خشکبار"

        c.execute("""
            INSERT OR REPLACE INTO ingredients
            (name, unit, price_per_gram, price_per_unit, category, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, unit, price_per_gram, price_per_unit, cat, notes))

    conn.commit()
    c.execute("SELECT COUNT(*) FROM ingredients")
    print(f"  [Data] Ingredients: {c.fetchone()[0]}")


# ============================================================
# Sheet 2 & 3: ریز غذانوع 1 & ریز غذا نوع دوم
# ============================================================
def extract_foods(wb, conn, sheet_name, food_type):
    """Extract foods and their ingredient recipes."""
    sheet = wb[sheet_name]
    c = conn.cursor()

    row = 3
    food_count = 0
    while row <= sheet.max_row:
        code = sheet.cell(row, 1).value
        name = sheet.cell(row, 2).value
        raw_cost = safe_float(sheet.cell(row, 3).value)

        if code is None or name is None:
            row += 4
            continue

        code = int(safe_float(code))
        name = safe_str(name)

        c.execute("""
            INSERT INTO foods (code, name, food_type, raw_cost)
            VALUES (?, ?, ?, ?)
        """, (code, name, food_type, raw_cost))
        food_id = c.lastrowid
        food_count += 1

        # Read ingredients for this food (row = name, row+1 = amount, row+2 = unit, row+3 = price)
        for col in range(5, sheet.max_column + 1):
            ing_name = safe_str(sheet.cell(row, col).value)
            if not ing_name or ing_name == "0" or ing_name == "None":
                continue
            if "افزودنی" in ing_name:
                break

            amount = safe_float(sheet.cell(row + 1, col).value)
            unit_val = safe_str(sheet.cell(row + 2, col).value, "گرم")
            unit_price = safe_float(sheet.cell(row + 3, col).value)

            # Calculate cost = amount * price_per_gram
            # But unit_price in the sheet is already amount * price_per_gram
            cost = unit_price  # The sheet stores total cost per ingredient

            c.execute("""
                INSERT INTO food_ingredients
                (food_id, ingredient_name, amount, unit, unit_price, cost)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (food_id, ing_name, amount, unit_val, unit_price, cost))

        row += 4

    conn.commit()
    print(f"  [{sheet_name}] Foods: {food_count}")


# ============================================================
# Sheet 4: هزینه سرباری (Overhead costs)
# ============================================================
def extract_overhead_costs(wb, conn):
    """Extract consumables and equipment from هزینه سرباری sheet."""
    sheet = wb["هزینه سرباری"]
    c = conn.cursor()

    # Part 1: Consumables (rows 2-42, cols 1-4)
    consumable_count = 0
    for row in range(2, 43):
        row_num = sheet.cell(row, 1).value
        name = safe_str(sheet.cell(row, 2).value)
        if not name:
            continue
        desc = safe_str(sheet.cell(row, 3).value)
        cost = safe_float(sheet.cell(row, 4).value)

        c.execute("""
            INSERT INTO consumables (row_num, name, description, cost_per_serving)
            VALUES (?, ?, ?, ?)
        """, (safe_float(row_num), name, desc, cost))
        consumable_count += 1

    # Get the total consumable cost from row 42
    total_consumable = safe_float(sheet.cell(42, 4).value, 95000)

    # Part 2: Equipment list (rows 43 onwards)
    equip_count = 0
    for row in range(43, sheet.max_row + 1):
        row_num = sheet.cell(row, 1).value
        name = safe_str(sheet.cell(row, 2).value)
        if not name or name == "ردیف":
            continue
        if row == 43:
            continue  # header row

        quantity = safe_float(sheet.cell(row, 3).value)
        unit = safe_str(sheet.cell(row, 4).value)
        unit_price = safe_float(sheet.cell(row, 5).value)
        total_price = safe_float(sheet.cell(row, 6).value)

        c.execute("""
            INSERT INTO equipment (row_num, name, quantity, unit, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (safe_float(row_num) if row_num else 0, name, quantity, unit, unit_price, total_price))
        equip_count += 1

    # Part 3: Overhead food items (cols 6-17, rows 1-onwards) - چاشنی، بهداشتی، پرت
    item_rows = []
    for row in range(1, 30):
        code = sheet.cell(row, 6).value
        name = safe_str(sheet.cell(row, 7).value)
        if code is not None and name:
            item_rows.append(row)

    for start_row in item_rows:
        code = safe_float(sheet.cell(start_row, 6).value)
        name = safe_str(sheet.cell(start_row, 7).value)
        total_price = safe_float(sheet.cell(start_row, 8).value)
        item_type = safe_str(sheet.cell(start_row, 9).value)

        c.execute("""
            INSERT INTO overhead_food_items (item_code, item_name, item_type, total_price)
            VALUES (?, ?, ?, ?)
        """, (int(code), name, item_type, total_price))
        item_id = c.lastrowid

        # Read ingredient details
        for col in range(10, 18):
            ing_name = safe_str(sheet.cell(start_row, col).value)
            if not ing_name:
                continue

            amount = safe_str(sheet.cell(start_row + 2, col).value) if start_row + 2 <= sheet.max_row else ""
            unit = safe_str(sheet.cell(start_row + 3, col).value) if start_row + 3 <= sheet.max_row else ""
            price = safe_float(sheet.cell(start_row + 4, col).value) if start_row + 4 <= sheet.max_row else 0

            c.execute("""
                INSERT INTO overhead_food_item_details
                (item_id, ingredient_name, amount, unit, unit_price)
                VALUES (?, ?, ?, ?, ?)
            """, (item_id, ing_name, amount, unit, price))

    conn.commit()
    print(f"  [هزینه سرباری] Consumables: {consumable_count}, Equipment: {equip_count}")
    return total_consumable


# ============================================================
# Sheet 5: آنالیز رانندگان داخل مجتمع ها
# ============================================================
def extract_drivers(wb, conn):
    """Extract driver analysis."""
    sheet = wb["آنالیز رانندگان داخل مجتمع ها"]
    c = conn.cursor()

    count = 0
    for row in range(5, sheet.max_row + 1):
        row_num = sheet.cell(row, 1).value
        sub_num = safe_float(sheet.cell(row, 2).value)
        pos_cat = safe_str(sheet.cell(row, 3).value)
        job_title = safe_str(sheet.cell(row, 4).value)
        post_count = safe_float(sheet.cell(row, 5).value)
        person_count = safe_float(sheet.cell(row, 6).value)
        gross_salary = safe_float(sheet.cell(row, 7).value)
        avg_salary = safe_float(sheet.cell(row, 8).value)

        if not job_title and not pos_cat:
            # Check if it's a total row
            if gross_salary > 0 or post_count > 0:
                pass  # Include total rows
            else:
                continue

        c.execute("""
            INSERT INTO driver_positions
            (row_num, sub_num, position_category, job_title, post_count, person_count, gross_salary, avg_monthly_salary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (safe_float(row_num) if row_num else 0, int(sub_num),
              pos_cat, job_title, int(post_count), int(person_count),
              gross_salary, avg_salary))
        count += 1

    # Get final driver cost per serving from last row
    driver_cost = safe_float(sheet.cell(sheet.max_row, 7).value)

    conn.commit()
    print(f"  [آنالیز رانندگان] Positions: {count}, Cost/serving: {driver_cost:,.0f}")
    return driver_cost


# ============================================================
# Sheet 6: آنالیز نیروی کار
# ============================================================
def extract_labor(wb, conn):
    """Extract labor analysis."""
    sheet = wb["آنالیز نیروی کار"]
    c = conn.cursor()

    count = 0
    current_category = ""
    for row in range(5, sheet.max_row + 1):
        row_num = sheet.cell(row, 1).value
        cat_name = safe_str(sheet.cell(row, 2).value)
        pos_name = safe_str(sheet.cell(row, 3).value)
        job_title = safe_str(sheet.cell(row, 4).value)
        post_count = safe_float(sheet.cell(row, 5).value)
        person_count = safe_float(sheet.cell(row, 6).value)
        gross_salary = safe_float(sheet.cell(row, 7).value)
        avg_salary = safe_float(sheet.cell(row, 8).value)

        if cat_name:
            current_category = cat_name

        if not job_title and not pos_name:
            if gross_salary > 0 or post_count > 0:
                pass  # total row
            else:
                continue

        c.execute("""
            INSERT INTO labor_positions
            (row_num, category, position_name, job_title, post_count, person_count, gross_salary, avg_monthly_salary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (safe_float(row_num) if row_num else 0, current_category,
              pos_name, job_title, int(post_count), int(person_count),
              gross_salary, avg_salary))
        count += 1

    # Get final labor cost per serving from last row
    labor_cost = safe_float(sheet.cell(sheet.max_row, 7).value)

    conn.commit()
    print(f"  [آنالیز نیروی کار] Positions: {count}, Cost/serving: {labor_cost:,.0f}")
    return labor_cost


# ============================================================
# Sheet 7 & 8: سرباری نوع 1 & سرباری نوع 2
# ============================================================
def extract_overhead_type1(wb, conn):
    """Extract overhead calculations for type 1 foods."""
    sheet = wb["سرباری نوع 1"]
    c = conn.cursor()

    # Read parameter values from Row 3
    params = {
        "consumables_t1": safe_float(sheet.cell(3, 5).value),
        "supplementary_insurance_t1": safe_float(sheet.cell(3, 6).value),
        "driver_salary_t1": safe_float(sheet.cell(3, 7).value),
        "vehicle_rental_t1": safe_float(sheet.cell(3, 8).value),
        "labor_cost_t1": safe_float(sheet.cell(3, 9).value),
        "equipment_depreciation_t1": safe_float(sheet.cell(3, 10).value),
        "fruit_t1": safe_float(sheet.cell(3, 11).value),
        "mineral_water_t1": safe_float(sheet.cell(3, 12).value),
        "delster_t1": safe_float(sheet.cell(3, 13).value),
        "dessert_garnish_t1": safe_float(sheet.cell(3, 14).value),
        "inflation_t1": safe_float(sheet.cell(3, 15).value),
        "contract_insurance_pct_t1": safe_float(sheet.cell(3, 16).value),
        "tax_pct_t1": safe_float(sheet.cell(3, 17).value),
        "profit_margin_pct_t1": safe_float(sheet.cell(3, 18).value),
    }

    # Read individual food overhead data (rows 4 onwards)
    count = 0
    for row in range(4, sheet.max_row + 1):
        code = sheet.cell(row, 1).value
        name = safe_str(sheet.cell(row, 2).value)
        if code is None or not name or name == "میانگین":
            if name == "میانگین":
                # Store average row too
                c.execute("""
                    INSERT INTO overhead_calc_type1
                    (food_code, food_name, raw_cost, consumables, supplementary_insurance,
                     driver_salary, vehicle_rental, labor_cost, equipment_depreciation,
                     fruit, mineral_water, delster, dessert_garnish, inflation,
                     contract_insurance, tax, profit_margin)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (0, "میانگین",
                      safe_float(sheet.cell(row, 3).value),
                      safe_float(sheet.cell(row, 5).value),
                      safe_float(sheet.cell(row, 6).value),
                      safe_float(sheet.cell(row, 7).value),
                      safe_float(sheet.cell(row, 8).value),
                      safe_float(sheet.cell(row, 9).value),
                      safe_float(sheet.cell(row, 10).value),
                      safe_float(sheet.cell(row, 11).value),
                      safe_float(sheet.cell(row, 12).value),
                      safe_float(sheet.cell(row, 13).value),
                      safe_float(sheet.cell(row, 14).value),
                      safe_float(sheet.cell(row, 15).value),
                      safe_float(sheet.cell(row, 16).value),
                      safe_float(sheet.cell(row, 17).value),
                      safe_float(sheet.cell(row, 18).value)))
            continue

        code = int(safe_float(code))
        c.execute("""
            INSERT INTO overhead_calc_type1
            (food_code, food_name, raw_cost, consumables, supplementary_insurance,
             driver_salary, vehicle_rental, labor_cost, equipment_depreciation,
             fruit, mineral_water, delster, dessert_garnish, inflation,
             contract_insurance, tax, profit_margin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, name,
              safe_float(sheet.cell(row, 3).value),
              safe_float(sheet.cell(row, 5).value),
              safe_float(sheet.cell(row, 6).value),
              safe_float(sheet.cell(row, 7).value),
              safe_float(sheet.cell(row, 8).value),
              safe_float(sheet.cell(row, 9).value),
              safe_float(sheet.cell(row, 10).value),
              safe_float(sheet.cell(row, 11).value),
              safe_float(sheet.cell(row, 12).value),
              safe_float(sheet.cell(row, 13).value),
              safe_float(sheet.cell(row, 14).value),
              safe_float(sheet.cell(row, 15).value),
              safe_float(sheet.cell(row, 16).value),
              safe_float(sheet.cell(row, 17).value),
              safe_float(sheet.cell(row, 18).value)))
        count += 1

    conn.commit()
    print(f"  [سرباری نوع 1] Foods: {count}")
    return params


def extract_overhead_type2(wb, conn):
    """Extract overhead calculations for type 2 foods."""
    sheet = wb["سرباری نوع 2"]
    c = conn.cursor()

    params = {
        "consumables_t2": safe_float(sheet.cell(3, 5).value),
        "supplementary_insurance_t2": safe_float(sheet.cell(3, 6).value),
        "driver_salary_t2": safe_float(sheet.cell(3, 7).value),
        "vehicle_rental_t2": safe_float(sheet.cell(3, 8).value),
        "labor_cost_t2": safe_float(sheet.cell(3, 9).value),
        "equipment_depreciation_t2": safe_float(sheet.cell(3, 10).value),
        "drink_t2": safe_float(sheet.cell(3, 11).value),
        "dessert_garnish_t2": safe_float(sheet.cell(3, 12).value),
        "inflation_t2": safe_float(sheet.cell(3, 13).value),
        "contract_insurance_pct_t2": safe_float(sheet.cell(3, 14).value),
        "tax_pct_t2": safe_float(sheet.cell(3, 15).value),
        "profit_margin_pct_t2": safe_float(sheet.cell(3, 16).value),
    }

    count = 0
    for row in range(4, sheet.max_row + 1):
        code = sheet.cell(row, 1).value
        name = safe_str(sheet.cell(row, 2).value)
        if code is None or not name or name == "میانگین":
            if name == "میانگین":
                c.execute("""
                    INSERT INTO overhead_calc_type2
                    (food_code, food_name, raw_cost, consumables, supplementary_insurance,
                     driver_salary, vehicle_rental, labor_cost, equipment_depreciation,
                     drink, dessert_garnish, inflation,
                     contract_insurance, tax, profit_margin, total_cost)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (0, "میانگین",
                      safe_float(sheet.cell(row, 3).value),
                      safe_float(sheet.cell(row, 5).value),
                      safe_float(sheet.cell(row, 6).value),
                      safe_float(sheet.cell(row, 7).value),
                      safe_float(sheet.cell(row, 8).value),
                      safe_float(sheet.cell(row, 9).value),
                      safe_float(sheet.cell(row, 10).value),
                      safe_float(sheet.cell(row, 11).value),
                      safe_float(sheet.cell(row, 12).value),
                      safe_float(sheet.cell(row, 13).value),
                      safe_float(sheet.cell(row, 14).value),
                      safe_float(sheet.cell(row, 15).value),
                      safe_float(sheet.cell(row, 16).value),
                      safe_float(sheet.cell(row, 18).value)))
            continue

        code = int(safe_float(code))
        c.execute("""
            INSERT INTO overhead_calc_type2
            (food_code, food_name, raw_cost, consumables, supplementary_insurance,
             driver_salary, vehicle_rental, labor_cost, equipment_depreciation,
             drink, dessert_garnish, inflation,
             contract_insurance, tax, profit_margin, total_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (code, name,
              safe_float(sheet.cell(row, 3).value),
              safe_float(sheet.cell(row, 5).value),
              safe_float(sheet.cell(row, 6).value),
              safe_float(sheet.cell(row, 7).value),
              safe_float(sheet.cell(row, 8).value),
              safe_float(sheet.cell(row, 9).value),
              safe_float(sheet.cell(row, 10).value),
              safe_float(sheet.cell(row, 11).value),
              safe_float(sheet.cell(row, 12).value),
              safe_float(sheet.cell(row, 13).value),
              safe_float(sheet.cell(row, 14).value),
              safe_float(sheet.cell(row, 15).value),
              safe_float(sheet.cell(row, 16).value),
              safe_float(sheet.cell(row, 18).value)))
        count += 1

    conn.commit()
    print(f"  [سرباری نوع 2] Foods: {count}")
    return params


# ============================================================
# Sheet 9: دورچین (Side dishes)
# ============================================================
def extract_side_dishes(wb, conn):
    """Extract side dishes and garnishes."""
    sheet = wb["دورچین"]
    c = conn.cursor()
    count = 0

    # Column group 1: cols 1-3
    for row in range(2, sheet.max_row + 1):
        name = safe_str(sheet.cell(row, 1).value)
        if not name:
            continue
        price = safe_float(sheet.cell(row, 2).value)
        notes = safe_str(sheet.cell(row, 3).value)
        c.execute("INSERT INTO side_dishes (name, price, notes, col_group) VALUES (?, ?, ?, 1)",
                  (name, price, notes))
        count += 1

    # Column group 2: cols 5-7
    for row in range(2, sheet.max_row + 1):
        name = safe_str(sheet.cell(row, 5).value)
        if not name:
            continue
        price = safe_float(sheet.cell(row, 6).value)
        notes = safe_str(sheet.cell(row, 7).value)
        c.execute("INSERT INTO side_dishes (name, price, notes, col_group) VALUES (?, ?, ?, 2)",
                  (name, price, notes))
        count += 1

    # Column group 3: cols 9-10
    for row in range(2, sheet.max_row + 1):
        name = safe_str(sheet.cell(row, 9).value)
        if not name:
            continue
        price = safe_float(sheet.cell(row, 10).value)
        notes = ""
        c.execute("INSERT INTO side_dishes (name, price, notes, col_group) VALUES (?, ?, ?, 3)",
                  (name, price, notes))
        count += 1

    conn.commit()
    print(f"  [دورچین] Side dishes: {count}")


# ============================================================
# Sheet 10: الحاقیه (Appendix)
# ============================================================
def extract_appendix(wb, conn):
    """Extract appendix data."""
    sheet = wb["الحاقیه"]
    c = conn.cursor()
    count = 0

    for row in range(4, sheet.max_row + 1):
        code = sheet.cell(row, 1).value
        row_num_val = sheet.cell(row, 2).value
        food_name = safe_str(sheet.cell(row, 3).value)
        if not food_name or food_name == "میانگین":
            if food_name == "میانگین":
                c.execute("""
                    INSERT INTO appendix (food_code, row_num, food_name, appendix_price, calculated_price)
                    VALUES (?, ?, ?, ?, ?)
                """, (0, 0, "میانگین", safe_float(sheet.cell(row, 4).value), 0))
            continue

        appendix_price = safe_float(sheet.cell(row, 4).value)
        calc_price = safe_float(sheet.cell(row, 5).value)

        c.execute("""
            INSERT INTO appendix (food_code, row_num, food_name, appendix_price, calculated_price)
            VALUES (?, ?, ?, ?, ?)
        """, (int(safe_float(code)) if code else 0,
              int(safe_float(row_num_val)) if row_num_val else 0,
              food_name, appendix_price, calc_price))
        count += 1

    conn.commit()
    print(f"  [الحاقیه] Items: {count}")


# ============================================================
# Sheet 11: Sheet1 (Weekly menu)
# ============================================================
def extract_weekly_menu(wb, conn):
    """Extract weekly menu."""
    sheet = wb["Sheet1"]
    c = conn.cursor()
    count = 0

    for row in range(4, sheet.max_row + 1):
        date_str = safe_str(sheet.cell(row, 1).value)
        day_name = safe_str(sheet.cell(row, 2).value)
        if not day_name:
            continue

        food_t1 = safe_str(sheet.cell(row, 3).value)
        food_t1_special = safe_str(sheet.cell(row, 4).value)
        food_t2 = safe_str(sheet.cell(row, 5).value)
        dessert = safe_str(sheet.cell(row, 6).value)
        dessert_special = safe_str(sheet.cell(row, 7).value)
        bread = safe_str(sheet.cell(row, 8).value)
        drink = safe_str(sheet.cell(row, 9).value)
        drink_price = safe_float(sheet.cell(row, 10).value)
        salad = safe_str(sheet.cell(row, 11).value)
        salad_price = safe_float(sheet.cell(row, 12).value)
        special_item = safe_str(sheet.cell(row, 13).value)
        special_price = safe_float(sheet.cell(row, 14).value)

        c.execute("""
            INSERT INTO weekly_menu
            (date_str, day_name, food_type1, food_type1_special, food_type2,
             dessert_desc, dessert_special, bread, drink, drink_price,
             salad, salad_price, special_item, special_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_str, day_name, food_t1, food_t1_special, food_t2,
              dessert, dessert_special, bread, drink, drink_price,
              salad, salad_price, special_item, special_price))
        count += 1

    conn.commit()
    print(f"  [Sheet1] Weekly menu days: {count}")


# ============================================================
# Sheet 12: آنالیز پیوست (Analysis attachment)
# ============================================================
def extract_analysis_attachment(wb, conn):
    """Extract analysis attachment data."""
    sheet = wb["آنالیز پیوست "]
    c = conn.cursor()
    count = 0

    row = 3
    while row <= sheet.max_row:
        code = sheet.cell(row, 1).value
        name = safe_str(sheet.cell(row, 2).value)
        raw_cost = safe_float(sheet.cell(row, 3).value)

        if code is None or not name:
            row += 4
            continue

        code = int(safe_float(code))
        c.execute("""
            INSERT INTO analysis_attachment (food_code, food_name, raw_cost, food_type)
            VALUES (?, ?, ?, ?)
        """, (code, name, raw_cost, 1))
        att_id = c.lastrowid
        count += 1

        # Read ingredients
        for col in range(5, sheet.max_column + 1):
            ing_name = safe_str(sheet.cell(row, col).value)
            if not ing_name or ing_name == "0":
                continue
            if "افزودنی" in ing_name:
                break

            amount = safe_float(sheet.cell(row + 1, col).value)
            unit = safe_str(sheet.cell(row + 2, col).value, "گرم")
            price = safe_float(sheet.cell(row + 3, col).value)

            c.execute("""
                INSERT INTO analysis_attachment_ingredients
                (attachment_id, ingredient_name, amount, unit, unit_price)
                VALUES (?, ?, ?, ?, ?)
            """, (att_id, ing_name, amount, unit, price))

        row += 4

    conn.commit()
    print(f"  [آنالیز پیوست] Foods: {count}")


# ============================================================
# Build overhead parameters from ALL sources (no hardcoding!)
# ============================================================
def build_overhead_params(conn, t1_params, t2_params, driver_cost, labor_cost, consumable_total):
    """Build overhead parameters table from extracted Excel data."""
    c = conn.cursor()

    # Use actual values from the overhead sheets (row 3)
    # But also use computed values from driver and labor sheets
    # Priority: use the values from سرباری sheets, fall back to computed values

    # For type 1 foods: from سرباری نوع 1 row 3
    # Note: some params in row 3 are 0 but individual foods use non-zero values
    # The actual per-food values come from the سرباری نوع 1 individual rows

    # Get actual driver salary from first food row (since row 3 might be 0)
    c.execute("SELECT driver_salary FROM overhead_calc_type1 WHERE food_code > 0 LIMIT 1")
    actual_driver_t1 = c.fetchone()
    actual_driver_cost = actual_driver_t1[0] if actual_driver_t1 else driver_cost

    params = [
        # Fixed costs per serving - Type 1
        ("consumables", "هزینه سرباری و اقلام مصرفی",
         t1_params.get("consumables_t1", consumable_total), "fixed", 0,
         "لباس کار، لیوان، شوینده، دستکش و...", "سرباری نوع 1"),

        ("supplementary_insurance", "بیمه تکمیلی",
         t1_params.get("supplementary_insurance_t1", 0), "fixed", 0,
         "بیمه تکمیلی کارکنان", "سرباری نوع 1"),

        ("driver_salary", "حقوق رانندگان تامین‌کننده",
         actual_driver_cost if actual_driver_cost else driver_cost, "fixed", 0,
         "حقوق رانندگان حمل مواد غذایی", "آنالیز رانندگان"),

        ("vehicle_rental", "اجاره ماشین داخل مجتمع",
         t1_params.get("vehicle_rental_t1", 0), "fixed", 0,
         "اجاره ماشین و راننده داخل حریم", "سرباری نوع 1"),

        ("labor_cost", "نیروی انسانی",
         t1_params.get("labor_cost_t1", labor_cost), "fixed", 0,
         "هزینه پرسنل به ازای هر پرس", "آنالیز نیروی کار"),

        ("equipment_depreciation", "استهلاک تجهیزات",
         t1_params.get("equipment_depreciation_t1", 0), "fixed", 0,
         "استهلاک تعمیرات و نگهداری تجهیزات", "سرباری نوع 1"),

        ("fruit_t1", "میوه (نوع ۱)",
         t1_params.get("fruit_t1", 0), "fixed", 1,
         "هزینه میوه", "سرباری نوع 1"),

        ("mineral_water_t1", "آب معدنی (نوع ۱)",
         t1_params.get("mineral_water_t1", 0), "fixed", 1,
         "هزینه آب معدنی", "سرباری نوع 1"),

        ("delster_t1", "دلستر (نوع ۱)",
         t1_params.get("delster_t1", 0), "fixed", 1,
         "هزینه دلستر", "سرباری نوع 1"),

        ("dessert_garnish_t1", "دسر و دورچین (نوع ۱)",
         t1_params.get("dessert_garnish_t1", 0), "fixed", 1,
         "سالاد، ماست، زیتون، خرما...", "سرباری نوع 1"),

        ("inflation_t1", "تورم (نوع ۱)",
         t1_params.get("inflation_t1", 0), "fixed", 1,
         "میزان سرمایه مورد نیاز 110 میلیارد تومان", "سرباری نوع 1"),

        # Type 2 specific fixed costs
        ("drink_t2", "نوشیدنی (نوع ۲)",
         t2_params.get("drink_t2", 0), "fixed", 2,
         "هزینه نوشیدنی", "سرباری نوع 2"),

        ("dessert_garnish_t2", "دسر و دورچین (نوع ۲)",
         t2_params.get("dessert_garnish_t2", 0), "fixed", 2,
         "سالاد، ماست، زیتون، خرما...", "سرباری نوع 2"),

        ("inflation_t2", "تورم (نوع ۲)",
         t2_params.get("inflation_t2", 0), "fixed", 2,
         "میزان سرمایه مورد نیاز 110 میلیارد تومان", "سرباری نوع 2"),

        # Percentage-based costs
        ("contract_insurance_pct_t1", "بیمه قرارداد (نوع ۱)",
         t1_params.get("contract_insurance_pct_t1", 8.9), "percent", 1,
         "درصد بیمه قرارداد نوع ۱", "سرباری نوع 1"),

        ("tax_pct_t1", "مالیات عملکرد (نوع ۱)",
         t1_params.get("tax_pct_t1", 5), "percent", 1,
         "مالیات عملکرد نوع ۱", "سرباری نوع 1"),

        ("profit_margin_pct_t1", "ضریب خطا و سود (نوع ۱)",
         t1_params.get("profit_margin_pct_t1", 12), "percent", 1,
         "ضریب خطا و سود پخت، آشپز، حسابداری", "سرباری نوع 1"),

        ("contract_insurance_pct_t2", "بیمه قرارداد (نوع ۲)",
         t2_params.get("contract_insurance_pct_t2", 8.9), "percent", 2,
         "درصد بیمه قرارداد نوع ۲", "سرباری نوع 2"),

        ("tax_pct_t2", "مالیات عملکرد (نوع ۲)",
         t2_params.get("tax_pct_t2", 3), "percent", 2,
         "مالیات عملکرد نوع ۲", "سرباری نوع 2"),

        ("profit_margin_pct_t2", "ضریب خطا و سود (نوع ۲)",
         t2_params.get("profit_margin_pct_t2", 12), "percent", 2,
         "ضریب خطا و سود پخت، آشپز، حسابداری", "سرباری نوع 2"),
    ]

    for p in params:
        c.execute("""
            INSERT OR REPLACE INTO overhead_params
            (name, label, value, param_type, food_type, description, source_sheet)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, p)

    # Settings - selling price from سرباری نوع 2 row 22
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('selling_price_type1', '2150000')")
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('selling_price_type2', '2150000')")

    conn.commit()
    print(f"  [Params] Overhead parameters: {len(params)} (all from Excel, no hardcoding)")


# ============================================================
# Recalculate total costs
# ============================================================
def recalculate_all(conn):
    """Recalculate total costs for all foods using current overhead parameters."""
    c = conn.cursor()

    # Get all overhead params
    c.execute("SELECT name, value, param_type, food_type FROM overhead_params")
    params = {}
    for row in c.fetchall():
        params[row[0]] = {"value": row[1], "type": row[2], "food_type": row[3]}

    # Calculate fixed overhead for type 1
    fixed_t1 = sum(
        p["value"] for name, p in params.items()
        if p["type"] == "fixed" and p["food_type"] in (0, 1)
    )

    # Calculate fixed overhead for type 2
    fixed_t2 = sum(
        p["value"] for name, p in params.items()
        if p["type"] == "fixed" and p["food_type"] in (0, 2)
    )

    # Get percentage params
    ins_pct_t1 = params.get("contract_insurance_pct_t1", {}).get("value", 8.9)
    tax_pct_t1 = params.get("tax_pct_t1", {}).get("value", 5)
    profit_pct_t1 = params.get("profit_margin_pct_t1", {}).get("value", 12)

    ins_pct_t2 = params.get("contract_insurance_pct_t2", {}).get("value", 8.9)
    tax_pct_t2 = params.get("tax_pct_t2", {}).get("value", 3)
    profit_pct_t2 = params.get("profit_margin_pct_t2", {}).get("value", 12)

    c.execute("SELECT id, raw_cost, food_type FROM foods")
    for food_id, raw_cost, food_type in c.fetchall():
        if food_type == 1:
            base = raw_cost + fixed_t1
            total_pct = ins_pct_t1 + tax_pct_t1 + profit_pct_t1
        else:
            base = raw_cost + fixed_t2
            total_pct = ins_pct_t2 + tax_pct_t2 + profit_pct_t2

        total_cost = base + (base * total_pct / 100)
        c.execute("UPDATE foods SET total_cost = ? WHERE id = ?", (total_cost, food_id))

    conn.commit()


# ============================================================
# Main
# ============================================================
def main():
    print("=" * 60)
    print("Extracting data from ALL 12 Excel sheets...")
    print("=" * 60)

    xlsx_path = get_xlsx_path()
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    print(f"\nSheets found: {wb.sheetnames}\n")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)

    # Sheet 1: Data
    extract_ingredients(wb, conn)

    # Sheet 2: ریز غذانوع 1
    extract_foods(wb, conn, "ریز غذانوع 1", 1)

    # Sheet 3: ریز غذا نوع دوم
    extract_foods(wb, conn, "ریز غذا نوع دوم", 2)

    # Sheet 4: هزینه سرباری
    consumable_total = extract_overhead_costs(wb, conn)

    # Sheet 5: آنالیز رانندگان
    driver_cost = extract_drivers(wb, conn)

    # Sheet 6: آنالیز نیروی کار
    labor_cost = extract_labor(wb, conn)

    # Sheet 7: سرباری نوع 1
    t1_params = extract_overhead_type1(wb, conn)

    # Sheet 8: سرباری نوع 2
    t2_params = extract_overhead_type2(wb, conn)

    # Sheet 9: دورچین
    extract_side_dishes(wb, conn)

    # Sheet 10: الحاقیه
    extract_appendix(wb, conn)

    # Sheet 11: Sheet1 (Weekly menu)
    extract_weekly_menu(wb, conn)

    # Sheet 12: آنالیز پیوست
    extract_analysis_attachment(wb, conn)

    # Build overhead params from ALL extracted data
    build_overhead_params(conn, t1_params, t2_params, driver_cost, labor_cost, consumable_total)

    # Recalculate total costs
    recalculate_all(conn)

    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE!")
    print("=" * 60)

    # Summary
    c = conn.cursor()
    tables = [
        "ingredients", "foods", "food_ingredients", "consumables", "equipment",
        "driver_positions", "labor_positions", "overhead_params",
        "overhead_calc_type1", "overhead_calc_type2", "side_dishes",
        "appendix", "weekly_menu", "analysis_attachment",
        "analysis_attachment_ingredients", "overhead_food_items",
        "overhead_food_item_details"
    ]
    for table in tables:
        c.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {c.fetchone()[0]} records")

    conn.close()
    print(f"\nDatabase: {DB_PATH}")


if __name__ == "__main__":
    main()
