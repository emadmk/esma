"""Flask application for food cost analysis and profit/loss tracking."""
import os
import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "food_cost.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- Pages ----------

@app.route("/")
def index():
    return render_template("index.html")


# ---------- API ----------

@app.route("/api/dashboard")
def api_dashboard():
    """Return dashboard summary data."""
    conn = get_db()
    c = conn.cursor()

    # Get selling prices
    c.execute("SELECT key, value FROM settings")
    settings = {row["key"]: float(row["value"]) for row in c.fetchall()}
    sp1 = settings.get("selling_price_type1", 2150000)
    sp2 = settings.get("selling_price_type2", 2150000)

    # Get all foods with profit/loss
    c.execute("SELECT id, code, name, food_type, raw_cost, total_cost FROM foods ORDER BY food_type, code")
    foods = []
    total_profit = 0
    total_loss = 0
    profit_count = 0
    loss_count = 0

    for row in c.fetchall():
        sp = sp1 if row["food_type"] == 1 else sp2
        diff = sp - row["total_cost"]
        food = {
            "id": row["id"],
            "code": row["code"],
            "name": row["name"],
            "food_type": row["food_type"],
            "raw_cost": round(row["raw_cost"]),
            "total_cost": round(row["total_cost"]),
            "selling_price": round(sp),
            "profit_loss": round(diff),
            "profit_loss_pct": round(diff / sp * 100, 1) if sp else 0,
            "is_profit": diff >= 0,
        }
        foods.append(food)
        if diff >= 0:
            total_profit += diff
            profit_count += 1
        else:
            total_loss += abs(diff)
            loss_count += 1

    # Get overhead params
    c.execute("SELECT * FROM overhead_params ORDER BY id")
    overheads = [dict(row) for row in c.fetchall()]

    conn.close()

    return jsonify({
        "foods": foods,
        "overheads": overheads,
        "settings": settings,
        "summary": {
            "total_foods": len(foods),
            "profit_count": profit_count,
            "loss_count": loss_count,
            "total_profit": round(total_profit),
            "total_loss": round(total_loss),
            "avg_profit_loss": round((total_profit - total_loss) / len(foods)) if foods else 0,
        },
    })


@app.route("/api/food/<int:food_id>")
def api_food_detail(food_id):
    """Get detailed info for a specific food."""
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM foods WHERE id = ?", (food_id,))
    food = dict(c.fetchone())

    c.execute("SELECT * FROM food_ingredients WHERE food_id = ? ORDER BY cost DESC", (food_id,))
    ingredients = [dict(row) for row in c.fetchall()]

    c.execute("SELECT key, value FROM settings")
    settings = {row["key"]: float(row["value"]) for row in c.fetchall()}

    c.execute("SELECT * FROM overhead_params ORDER BY id")
    overheads = [dict(row) for row in c.fetchall()]

    sp = settings.get(f"selling_price_type{food['food_type']}", 2150000)
    food["selling_price"] = sp
    food["profit_loss"] = sp - food["total_cost"]

    conn.close()

    return jsonify({"food": food, "ingredients": ingredients, "overheads": overheads})


@app.route("/api/ingredients")
def api_ingredients():
    """Get all ingredient base prices."""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM ingredients ORDER BY name")
    ingredients = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"ingredients": ingredients})


@app.route("/api/ingredients/<int:ingredient_id>", methods=["PUT"])
def api_update_ingredient(ingredient_id):
    """Update an ingredient's price."""
    data = request.json
    conn = get_db()
    c = conn.cursor()

    c.execute(
        "UPDATE ingredients SET price_per_gram = ?, price_per_unit = ? WHERE id = ?",
        (data.get("price_per_gram", 0), data.get("price_per_unit", 0), ingredient_id),
    )

    # Get the ingredient name
    c.execute("SELECT name FROM ingredients WHERE id = ?", (ingredient_id,))
    ing_row = c.fetchone()
    if ing_row:
        ing_name = ing_row["name"]
        new_price_per_gram = data.get("price_per_gram", 0)

        # Update all food_ingredients that use this ingredient
        c.execute("SELECT fi.id, fi.amount, fi.food_id FROM food_ingredients fi WHERE fi.ingredient_name = ?", (ing_name,))
        for fi in c.fetchall():
            new_cost = fi["amount"] * new_price_per_gram
            c.execute("UPDATE food_ingredients SET cost = ? WHERE id = ?", (new_cost, fi["id"]))

        # Recalculate raw costs for affected foods
        c.execute(
            "SELECT DISTINCT food_id FROM food_ingredients WHERE ingredient_name = ?",
            (ing_name,),
        )
        food_ids = [row["food_id"] for row in c.fetchall()]

        for fid in food_ids:
            c.execute("SELECT SUM(cost) FROM food_ingredients WHERE food_id = ?", (fid,))
            total_raw = c.fetchone()[0] or 0
            c.execute("UPDATE foods SET raw_cost = ? WHERE id = ?", (total_raw, fid))

    conn.commit()
    _recalculate_all(conn)
    conn.close()

    return jsonify({"success": True})


@app.route("/api/overhead/<int:overhead_id>", methods=["PUT"])
def api_update_overhead(overhead_id):
    """Update an overhead parameter."""
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE overhead_params SET value = ? WHERE id = ?", (data.get("value", 0), overhead_id))
    conn.commit()
    _recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


@app.route("/api/settings", methods=["PUT"])
def api_update_settings():
    """Update settings (selling prices, etc)."""
    data = request.json
    conn = get_db()
    c = conn.cursor()
    for key, value in data.items():
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    _recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Simulate profit/loss with temporary price changes without saving."""
    data = request.json
    conn = get_db()
    c = conn.cursor()

    ingredient_changes = data.get("ingredient_changes", {})
    overhead_changes = data.get("overhead_changes", {})
    selling_price = data.get("selling_price", None)

    # Get current overhead params
    c.execute("SELECT name, value, param_type FROM overhead_params")
    params = {}
    for row in c.fetchall():
        val = overhead_changes.get(row["name"], row["value"])
        params[row["name"]] = (float(val), row["param_type"])

    fixed_overhead = sum(v for v, t in params.values() if t == "fixed")

    c.execute("SELECT key, value FROM settings")
    settings = {row["key"]: float(row["value"]) for row in c.fetchall()}
    sp1 = selling_price if selling_price else settings.get("selling_price_type1", 2150000)
    sp2 = selling_price if selling_price else settings.get("selling_price_type2", 2150000)

    c.execute("SELECT id, code, name, food_type, raw_cost FROM foods ORDER BY food_type, code")
    results = []

    for food in c.fetchall():
        # Calculate adjusted raw cost
        c2 = conn.cursor()
        c2.execute("SELECT ingredient_name, amount, cost FROM food_ingredients WHERE food_id = ?", (food["id"],))
        raw_cost = 0
        for fi in c2.fetchall():
            if fi["ingredient_name"] in ingredient_changes:
                new_ppg = float(ingredient_changes[fi["ingredient_name"]])
                raw_cost += fi["amount"] * new_ppg
            else:
                raw_cost += fi["cost"]

        base = raw_cost + fixed_overhead
        insurance_pct = params.get("contract_insurance_pct", (8.9, "percent"))[0]

        if food["food_type"] == 1:
            tax_pct = params.get("tax_pct", (5, "percent"))[0]
        else:
            tax_pct = float(overhead_changes.get("tax_pct_type2", settings.get("tax_pct_type2", 3)))

        profit_pct = params.get("profit_margin_pct", (12, "percent"))[0]
        total_cost = base * (1 + (insurance_pct + tax_pct + profit_pct) / 100)

        sp = sp1 if food["food_type"] == 1 else sp2
        diff = sp - total_cost

        results.append({
            "id": food["id"],
            "code": food["code"],
            "name": food["name"],
            "food_type": food["food_type"],
            "raw_cost": round(raw_cost),
            "total_cost": round(total_cost),
            "selling_price": round(sp),
            "profit_loss": round(diff),
            "is_profit": diff >= 0,
        })

    conn.close()
    return jsonify({"foods": results})


def _recalculate_all(conn):
    """Recalculate total costs for all foods."""
    c = conn.cursor()
    c.execute("SELECT name, value, param_type FROM overhead_params")
    params = {row["name"]: (row["value"], row["param_type"]) for row in c.fetchall()}

    fixed_overhead = sum(v for v, t in params.values() if t == "fixed")

    c.execute("SELECT key, value FROM settings")
    settings = {row["key"]: float(row["value"]) for row in c.fetchall()}

    c.execute("SELECT id, raw_cost, food_type FROM foods")
    for food in c.fetchall():
        base = food["raw_cost"] + fixed_overhead
        insurance_pct = params.get("contract_insurance_pct", (8.9, "percent"))[0]

        if food["food_type"] == 1:
            tax_pct = params.get("tax_pct", (5, "percent"))[0]
        else:
            tax_pct = float(settings.get("tax_pct_type2", 3))

        profit_pct = params.get("profit_margin_pct", (12, "percent"))[0]
        total_cost = base * (1 + (insurance_pct + tax_pct + profit_pct) / 100)

        c.execute("UPDATE foods SET total_cost = ? WHERE id = ?", (total_cost, food["id"]))

    conn.commit()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
