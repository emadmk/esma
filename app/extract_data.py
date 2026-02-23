"""Extract data from Excel file and populate SQLite database."""
import sqlite3
import os
import openpyxl

EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "DOC-20251215-WA0000.xlsx")
DB_PATH = os.path.join(os.path.dirname(__file__), "food_cost.db")


def create_tables(conn):
    c = conn.cursor()
    c.executescript("""
        DROP TABLE IF EXISTS ingredients;
        DROP TABLE IF EXISTS foods;
        DROP TABLE IF EXISTS food_ingredients;
        DROP TABLE IF EXISTS overhead_params;
        DROP TABLE IF EXISTS settings;

        CREATE TABLE ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            unit TEXT,
            price_per_gram REAL DEFAULT 0,
            price_per_unit REAL DEFAULT 0,
            notes TEXT
        );

        CREATE TABLE foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            food_type INTEGER DEFAULT 1,  -- 1=نوع اول, 2=نوع دوم
            raw_cost REAL DEFAULT 0,
            total_cost REAL DEFAULT 0
        );

        CREATE TABLE food_ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            ingredient_name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            unit TEXT,
            cost REAL DEFAULT 0,
            FOREIGN KEY (food_id) REFERENCES foods(id)
        );

        CREATE TABLE overhead_params (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            label TEXT NOT NULL,
            value REAL DEFAULT 0,
            param_type TEXT DEFAULT 'fixed',  -- 'fixed' or 'percent'
            description TEXT
        );

        CREATE TABLE settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()


def extract_ingredients(wb, conn):
    """Extract ingredient prices from Data sheet."""
    sheet = wb["Data"]
    c = conn.cursor()
    for row in range(2, sheet.max_row + 1):
        name = sheet.cell(row, 1).value
        if not name or name.strip() == "":
            continue
        # Skip category headers
        if name in ["کنسروجات", "لبنیات", "پروتئین", "میوه و تره بار"]:
            continue
        unit = sheet.cell(row, 2).value or ""
        price_per_gram = sheet.cell(row, 3).value or 0
        price_per_unit = sheet.cell(row, 4).value or 0
        notes = sheet.cell(row, 5).value or ""

        if isinstance(price_per_gram, str):
            try:
                price_per_gram = float(price_per_gram)
            except ValueError:
                price_per_gram = 0
        if isinstance(price_per_unit, str):
            try:
                price_per_unit = float(price_per_unit)
            except ValueError:
                price_per_unit = 0

        c.execute(
            "INSERT OR REPLACE INTO ingredients (name, unit, price_per_gram, price_per_unit, notes) VALUES (?, ?, ?, ?, ?)",
            (name.strip(), unit.strip() if unit else "", price_per_gram, price_per_unit, notes.strip() if notes else ""),
        )
    conn.commit()


def extract_foods_type1(wb, conn):
    """Extract type-1 foods from ریز غذانوع 1 sheet."""
    sheet = wb["ریز غذانوع 1"]
    c = conn.cursor()

    row = 3
    while row <= sheet.max_row:
        code = sheet.cell(row, 1).value
        name = sheet.cell(row, 2).value
        raw_cost = sheet.cell(row, 3).value

        if code is None or name is None:
            row += 4
            continue

        if isinstance(raw_cost, str):
            try:
                raw_cost = float(raw_cost)
            except ValueError:
                raw_cost = 0
        raw_cost = raw_cost or 0

        c.execute(
            "INSERT INTO foods (code, name, food_type, raw_cost) VALUES (?, ?, 1, ?)",
            (int(code), name.strip(), raw_cost),
        )
        food_id = c.lastrowid

        # Read ingredients for this food (columns E onwards)
        amount_row = row + 1
        price_row = row + 3

        for col in range(5, sheet.max_column + 1):
            ing_name = sheet.cell(row, col).value
            ing_name_str = str(ing_name).strip() if ing_name else ""
            if not ing_name_str or ing_name_str == "0":
                continue
            if "افزودنی" in ing_name_str:
                break

            amount = sheet.cell(amount_row, col).value or 0
            cost = sheet.cell(price_row, col).value or 0
            unit_val = sheet.cell(row + 2, col).value or "گرم"

            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except ValueError:
                    amount = 0
            if isinstance(cost, str):
                try:
                    cost = float(cost)
                except ValueError:
                    cost = 0

            c.execute(
                "INSERT INTO food_ingredients (food_id, ingredient_name, amount, unit, cost) VALUES (?, ?, ?, ?, ?)",
                (food_id, ing_name_str, amount, str(unit_val).strip(), cost),
            )

        row += 4
    conn.commit()


def extract_foods_type2(wb, conn):
    """Extract type-2 foods from ریز غذا نوع دوم sheet."""
    sheet = wb["ریز غذا نوع دوم"]
    c = conn.cursor()

    row = 3
    while row <= sheet.max_row:
        code = sheet.cell(row, 1).value
        name = sheet.cell(row, 2).value
        raw_cost = sheet.cell(row, 3).value

        if code is None or name is None:
            row += 4
            continue

        if isinstance(raw_cost, str):
            try:
                raw_cost = float(raw_cost)
            except ValueError:
                raw_cost = 0
        raw_cost = raw_cost or 0

        c.execute(
            "INSERT INTO foods (code, name, food_type, raw_cost) VALUES (?, ?, 2, ?)",
            (int(code) + 200, name.strip(), raw_cost),
        )
        food_id = c.lastrowid

        amount_row = row + 1
        price_row = row + 3

        for col in range(5, sheet.max_column + 1):
            ing_name = sheet.cell(row, col).value
            ing_name_str = str(ing_name).strip() if ing_name else ""
            if not ing_name_str or ing_name_str == "0":
                continue
            if "افزودنی" in ing_name_str:
                break

            amount = sheet.cell(amount_row, col).value or 0
            cost = sheet.cell(price_row, col).value or 0
            unit_val = sheet.cell(row + 2, col).value or "گرم"

            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except ValueError:
                    amount = 0
            if isinstance(cost, str):
                try:
                    cost = float(cost)
                except ValueError:
                    cost = 0

            c.execute(
                "INSERT INTO food_ingredients (food_id, ingredient_name, amount, unit, cost) VALUES (?, ?, ?, ?, ?)",
                (food_id, str(ing_name).strip(), amount, str(unit_val).strip(), cost),
            )

        row += 4
    conn.commit()


def extract_overhead_params(conn):
    """Set up overhead parameters from the Excel analysis."""
    c = conn.cursor()
    params = [
        ("overhead_consumables", "هزینه سرباری و اقلام مصرفی", 95000, "fixed", "لباس کار، لیوان، شوینده، دستکش و..."),
        ("insurance_supplementary", "بیمه تکمیلی", 0, "fixed", "بیمه تکمیلی کارکنان"),
        ("driver_salary", "حقوق رانندگان تامین‌کننده", 27898.55, "fixed", "حقوق رانندگان حمل مواد غذایی"),
        ("vehicle_rental", "اجاره ماشین داخل مجتمع", 0, "fixed", "اجاره ماشین و راننده داخل حریم"),
        ("labor_cost", "نیروی انسانی", 253923.08, "fixed", "هزینه پرسنل به ازای هر پرس"),
        ("equipment_depreciation", "استهلاک تجهیزات", 0, "fixed", "استهلاک تعمیرات و نگهداری تجهیزات"),
        ("fruit_cost", "میوه", 0, "fixed", "هزینه میوه"),
        ("water_cost", "آب معدنی", 0, "fixed", "هزینه آب معدنی"),
        ("delster_cost", "دلستر", 0, "fixed", "هزینه دلستر"),
        ("dessert_cost", "دسر و دورچین", 0, "fixed", "سالاد، ماست، زیتون، خرما..."),
        ("inflation", "تورم و هزینه سرمایه", 0, "fixed", "میزان سرمایه مورد نیاز 110 میلیارد تومان"),
        ("contract_insurance_pct", "بیمه قرارداد", 8.9, "percent", "8.9 درصد کل قرارداد"),
        ("tax_pct", "مالیات عملکرد", 5, "percent", "مالیات عملکرد - نوع 1: 5%"),
        ("profit_margin_pct", "ضریب خطا و سود", 12, "percent", "ضریب خطا و سود پخت، آشپز، حسابداری و..."),
    ]
    for p in params:
        c.execute(
            "INSERT INTO overhead_params (name, label, value, param_type, description) VALUES (?, ?, ?, ?, ?)",
            p,
        )

    # Settings
    c.execute("INSERT INTO settings (key, value) VALUES ('selling_price_type1', '2150000')")
    c.execute("INSERT INTO settings (key, value) VALUES ('selling_price_type2', '2150000')")
    c.execute("INSERT INTO settings (key, value) VALUES ('tax_pct_type2', '3')")  # type 2 has 3% tax
    conn.commit()


def recalculate_total_costs(conn):
    """Recalculate total costs for all foods using current overhead parameters."""
    c = conn.cursor()

    # Get overhead params
    c.execute("SELECT name, value, param_type FROM overhead_params")
    params = {row[0]: (row[1], row[2]) for row in c.fetchall()}

    # Fixed overhead sum
    fixed_overhead = sum(v for v, t in params.values() if t == "fixed")

    c.execute("SELECT id, raw_cost, food_type FROM foods")
    foods = c.fetchall()

    for food_id, raw_cost, food_type in foods:
        base = raw_cost + fixed_overhead

        # Percentage-based costs are calculated on the base
        insurance_pct = params.get("contract_insurance_pct", (8.9, "percent"))[0]
        if food_type == 1:
            tax_pct = params.get("tax_pct", (5, "percent"))[0]
        else:
            # Type 2 uses 3% tax
            c2 = conn.cursor()
            c2.execute("SELECT value FROM settings WHERE key='tax_pct_type2'")
            row = c2.fetchone()
            tax_pct = float(row[0]) if row else 3

        profit_pct = params.get("profit_margin_pct", (12, "percent"))[0]

        insurance_cost = base * insurance_pct / 100
        tax_cost = base * tax_pct / 100
        profit_cost = base * profit_pct / 100

        total_cost = base + insurance_cost + tax_cost + profit_cost

        c.execute("UPDATE foods SET total_cost = ? WHERE id = ?", (total_cost, food_id))

    conn.commit()


def main():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    create_tables(conn)
    extract_ingredients(wb, conn)
    extract_foods_type1(wb, conn)
    extract_foods_type2(wb, conn)
    extract_overhead_params(conn)
    recalculate_total_costs(conn)

    # Print summary
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM ingredients")
    print(f"Ingredients: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM foods WHERE food_type=1")
    print(f"Type-1 foods: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM foods WHERE food_type=2")
    print(f"Type-2 foods: {c.fetchone()[0]}")
    c.execute("SELECT COUNT(*) FROM food_ingredients")
    print(f"Food-ingredient records: {c.fetchone()[0]}")

    # Show profit/loss summary
    c.execute("SELECT value FROM settings WHERE key='selling_price_type1'")
    sp1 = float(c.fetchone()[0])
    c.execute("SELECT value FROM settings WHERE key='selling_price_type2'")
    sp2 = float(c.fetchone()[0])

    print(f"\nSelling price type 1: {sp1:,.0f} Rials")
    print(f"Selling price type 2: {sp2:,.0f} Rials")
    print("\n--- Profit/Loss Summary ---")
    c.execute("SELECT code, name, food_type, raw_cost, total_cost FROM foods ORDER BY food_type, code")
    for code, name, ft, rc, tc in c.fetchall():
        sp = sp1 if ft == 1 else sp2
        diff = sp - tc
        status = "PROFIT" if diff > 0 else "LOSS"
        print(f"  [{status:6s}] {name:30s} | Raw: {rc:>12,.0f} | Total: {tc:>12,.0f} | Diff: {diff:>12,.0f}")

    conn.close()
    print(f"\nDatabase saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
