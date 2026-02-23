"""Flask application for food cost analysis - covers ALL 12 Excel sheets."""
import os
import sqlite3
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
DB_PATH = os.path.join(os.path.dirname(__file__), "food_cost.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def dict_row(row):
    return dict(row) if row else None


def dict_rows(rows):
    return [dict(r) for r in rows]


def recalculate_all(conn):
    """Recalculate total costs for all foods using current overhead parameters."""
    c = conn.cursor()
    c.execute("SELECT name, value, param_type, food_type FROM overhead_params")
    params = {}
    for row in c.fetchall():
        params[row["name"]] = {"value": row["value"], "type": row["param_type"], "food_type": row["food_type"]}

    fixed_t1 = sum(p["value"] for p in params.values() if p["type"] == "fixed" and p["food_type"] in (0, 1))
    fixed_t2 = sum(p["value"] for p in params.values() if p["type"] == "fixed" and p["food_type"] in (0, 2))

    ins_t1 = params.get("contract_insurance_pct_t1", {}).get("value", 8.9)
    tax_t1 = params.get("tax_pct_t1", {}).get("value", 5)
    prof_t1 = params.get("profit_margin_pct_t1", {}).get("value", 12)
    ins_t2 = params.get("contract_insurance_pct_t2", {}).get("value", 8.9)
    tax_t2 = params.get("tax_pct_t2", {}).get("value", 3)
    prof_t2 = params.get("profit_margin_pct_t2", {}).get("value", 12)

    c.execute("SELECT id, raw_cost, food_type FROM foods")
    for food in c.fetchall():
        if food["food_type"] == 1:
            base = food["raw_cost"] + fixed_t1
            pct = ins_t1 + tax_t1 + prof_t1
        else:
            base = food["raw_cost"] + fixed_t2
            pct = ins_t2 + tax_t2 + prof_t2
        total = base + (base * pct / 100)
        c.execute("UPDATE foods SET total_cost = ? WHERE id = ?", (total, food["id"]))
    conn.commit()


# ==================== Pages ====================

@app.route("/")
def index():
    return render_template("index.html")


# ==================== Dashboard API ====================

@app.route("/api/dashboard")
def api_dashboard():
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT key, value FROM settings")
    settings = {r["key"]: float(r["value"]) for r in c.fetchall()}
    sp1 = settings.get("selling_price_type1", 2150000)
    sp2 = settings.get("selling_price_type2", 2150000)

    c.execute("SELECT id, code, name, food_type, raw_cost, total_cost FROM foods ORDER BY food_type, code")
    foods = []
    tp, tl, pc, lc = 0, 0, 0, 0
    for r in c.fetchall():
        sp = sp1 if r["food_type"] == 1 else sp2
        diff = sp - r["total_cost"]
        foods.append({
            "id": r["id"], "code": r["code"], "name": r["name"],
            "food_type": r["food_type"],
            "raw_cost": round(r["raw_cost"]),
            "total_cost": round(r["total_cost"]),
            "selling_price": round(sp),
            "profit_loss": round(diff),
            "profit_loss_pct": round(diff / sp * 100, 1) if sp else 0,
            "is_profit": diff >= 0,
        })
        if diff >= 0:
            tp += diff; pc += 1
        else:
            tl += abs(diff); lc += 1

    c.execute("SELECT * FROM overhead_params ORDER BY id")
    overheads = dict_rows(c.fetchall())

    conn.close()
    return jsonify({
        "foods": foods, "overheads": overheads, "settings": settings,
        "summary": {
            "total_foods": len(foods), "profit_count": pc, "loss_count": lc,
            "total_profit": round(tp), "total_loss": round(tl),
            "avg_profit_loss": round((tp - tl) / len(foods)) if foods else 0,
        },
    })


# ==================== Ingredients API ====================

@app.route("/api/ingredients")
def api_ingredients():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM ingredients ORDER BY category, name")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"ingredients": data})


@app.route("/api/ingredients/<int:ing_id>", methods=["PUT"])
def api_update_ingredient(ing_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE ingredients SET price_per_gram=?, price_per_unit=? WHERE id=?",
              (data.get("price_per_gram", 0), data.get("price_per_unit", 0), ing_id))

    # Recalculate food ingredient costs
    c.execute("SELECT name FROM ingredients WHERE id=?", (ing_id,))
    row = c.fetchone()
    if row:
        new_ppg = data.get("price_per_gram", 0)
        c.execute("SELECT fi.id, fi.amount, fi.food_id FROM food_ingredients fi WHERE fi.ingredient_name=?",
                  (row["name"],))
        for fi in c.fetchall():
            new_cost = fi["amount"] * new_ppg
            c.execute("UPDATE food_ingredients SET unit_price=?, cost=? WHERE id=?",
                      (new_cost, new_cost, fi["id"]))
        # Recalculate raw costs
        c.execute("SELECT DISTINCT food_id FROM food_ingredients WHERE ingredient_name=?", (row["name"],))
        for frow in c.fetchall():
            c.execute("SELECT SUM(cost) FROM food_ingredients WHERE food_id=?", (frow["food_id"],))
            total_raw = c.fetchone()[0] or 0
            c.execute("UPDATE foods SET raw_cost=? WHERE id=?", (total_raw, frow["food_id"]))

    conn.commit()
    recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


# ==================== Foods API ====================

@app.route("/api/foods")
def api_foods():
    food_type = request.args.get("type", None)
    conn = get_db()
    c = conn.cursor()
    if food_type:
        c.execute("SELECT * FROM foods WHERE food_type=? ORDER BY code", (food_type,))
    else:
        c.execute("SELECT * FROM foods ORDER BY food_type, code")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"foods": data})


@app.route("/api/foods/<int:food_id>")
def api_food_detail(food_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM foods WHERE id=?", (food_id,))
    food = dict_row(c.fetchone())
    c.execute("SELECT * FROM food_ingredients WHERE food_id=? ORDER BY cost DESC", (food_id,))
    ingredients = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"food": food, "ingredients": ingredients})


@app.route("/api/food_ingredients/<int:fi_id>", methods=["PUT"])
def api_update_food_ingredient(fi_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE food_ingredients SET amount=?, unit_price=?, cost=? WHERE id=?",
              (data.get("amount", 0), data.get("unit_price", 0), data.get("cost", 0), fi_id))
    # Recalculate raw cost
    c.execute("SELECT food_id FROM food_ingredients WHERE id=?", (fi_id,))
    row = c.fetchone()
    if row:
        c.execute("SELECT SUM(cost) FROM food_ingredients WHERE food_id=?", (row["food_id"],))
        total = c.fetchone()[0] or 0
        c.execute("UPDATE foods SET raw_cost=? WHERE id=?", (total, row["food_id"]))
    conn.commit()
    recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


# ==================== Overhead Params API ====================

@app.route("/api/overhead_params")
def api_overhead_params():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM overhead_params ORDER BY food_type, id")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"params": data})


@app.route("/api/overhead_params/<int:pid>", methods=["PUT"])
def api_update_overhead_param(pid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE overhead_params SET value=? WHERE id=?", (data.get("value", 0), pid))
    conn.commit()
    recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


# ==================== Consumables API ====================

@app.route("/api/consumables")
def api_consumables():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM consumables ORDER BY id")
    data = dict_rows(c.fetchall())
    c.execute("SELECT SUM(cost_per_serving) as total FROM consumables")
    total = c.fetchone()["total"] or 0
    conn.close()
    return jsonify({"consumables": data, "total": round(total)})


@app.route("/api/consumables/<int:cid>", methods=["PUT"])
def api_update_consumable(cid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE consumables SET name=?, description=?, cost_per_serving=? WHERE id=?",
              (data.get("name", ""), data.get("description", ""), data.get("cost_per_serving", 0), cid))
    # Update the consumables overhead param with new total
    c.execute("SELECT SUM(cost_per_serving) FROM consumables")
    total = c.fetchone()[0] or 0
    c.execute("UPDATE overhead_params SET value=? WHERE name='consumables'", (total,))
    conn.commit()
    recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


# ==================== Equipment API ====================

@app.route("/api/equipment")
def api_equipment():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM equipment ORDER BY id")
    data = dict_rows(c.fetchall())
    c.execute("SELECT SUM(total_price) as total FROM equipment")
    total = c.fetchone()["total"] or 0
    conn.close()
    return jsonify({"equipment": data, "total": round(total)})


@app.route("/api/equipment/<int:eid>", methods=["PUT"])
def api_update_equipment(eid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE equipment SET name=?, quantity=?, unit=?, unit_price=?, total_price=? WHERE id=?",
              (data.get("name", ""), data.get("quantity", 0), data.get("unit", ""),
               data.get("unit_price", 0), data.get("total_price", 0), eid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== Drivers API ====================

@app.route("/api/drivers")
def api_drivers():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM driver_positions ORDER BY id")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"positions": data})


@app.route("/api/drivers/<int:did>", methods=["PUT"])
def api_update_driver(did):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("""UPDATE driver_positions SET job_title=?, post_count=?, person_count=?,
              gross_salary=?, avg_monthly_salary=? WHERE id=?""",
              (data.get("job_title", ""), data.get("post_count", 0), data.get("person_count", 0),
               data.get("gross_salary", 0), data.get("avg_monthly_salary", 0), did))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== Labor API ====================

@app.route("/api/labor")
def api_labor():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM labor_positions ORDER BY id")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"positions": data})


@app.route("/api/labor/<int:lid>", methods=["PUT"])
def api_update_labor(lid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("""UPDATE labor_positions SET job_title=?, post_count=?, person_count=?,
              gross_salary=?, avg_monthly_salary=? WHERE id=?""",
              (data.get("job_title", ""), data.get("post_count", 0), data.get("person_count", 0),
               data.get("gross_salary", 0), data.get("avg_monthly_salary", 0), lid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== Overhead Calc API ====================

@app.route("/api/overhead_calc")
def api_overhead_calc():
    food_type = request.args.get("type", "1")
    conn = get_db()
    c = conn.cursor()
    if food_type == "1":
        c.execute("SELECT * FROM overhead_calc_type1 ORDER BY food_code")
    else:
        c.execute("SELECT * FROM overhead_calc_type2 ORDER BY food_code")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"data": data, "food_type": int(food_type)})


# ==================== Side Dishes API ====================

@app.route("/api/side_dishes")
def api_side_dishes():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM side_dishes ORDER BY col_group, id")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"side_dishes": data})


@app.route("/api/side_dishes/<int:sid>", methods=["PUT"])
def api_update_side_dish(sid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE side_dishes SET name=?, price=?, notes=? WHERE id=?",
              (data.get("name", ""), data.get("price", 0), data.get("notes", ""), sid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== Appendix API ====================

@app.route("/api/appendix")
def api_appendix():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM appendix ORDER BY food_code")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"items": data})


@app.route("/api/appendix/<int:aid>", methods=["PUT"])
def api_update_appendix(aid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE appendix SET appendix_price=?, calculated_price=? WHERE id=?",
              (data.get("appendix_price", 0), data.get("calculated_price", 0), aid))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== Weekly Menu API ====================

@app.route("/api/weekly_menu")
def api_weekly_menu():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM weekly_menu ORDER BY id")
    data = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"menu": data})


@app.route("/api/weekly_menu/<int:mid>", methods=["PUT"])
def api_update_weekly_menu(mid):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    fields = ["date_str", "day_name", "food_type1", "food_type1_special", "food_type2",
              "dessert_desc", "dessert_special", "bread", "drink", "drink_price",
              "salad", "salad_price", "special_item", "special_price"]
    sets = ", ".join(f"{f}=?" for f in fields)
    vals = [data.get(f, "") for f in fields] + [mid]
    c.execute(f"UPDATE weekly_menu SET {sets} WHERE id=?", vals)
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# ==================== Analysis Attachment API ====================

@app.route("/api/analysis_attachment")
def api_analysis_attachment():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM analysis_attachment ORDER BY food_code")
    foods = dict_rows(c.fetchall())
    for f in foods:
        c.execute("SELECT * FROM analysis_attachment_ingredients WHERE attachment_id=?", (f["id"],))
        f["ingredients"] = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"foods": foods})


# ==================== Overhead Food Items API ====================

@app.route("/api/overhead_food_items")
def api_overhead_food_items():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM overhead_food_items ORDER BY id")
    items = dict_rows(c.fetchall())
    for item in items:
        c.execute("SELECT * FROM overhead_food_item_details WHERE item_id=?", (item["id"],))
        item["details"] = dict_rows(c.fetchall())
    conn.close()
    return jsonify({"items": items})


# ==================== Settings API ====================

@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    data = {r["key"]: r["value"] for r in c.fetchall()}
    conn.close()
    return jsonify({"settings": data})


@app.route("/api/settings", methods=["PUT"])
def api_update_settings():
    data = request.json
    conn = get_db()
    c = conn.cursor()
    for key, value in data.items():
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    recalculate_all(conn)
    conn.close()
    return jsonify({"success": True})


# ==================== Simulator API ====================

@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    data = request.json
    conn = get_db()
    c = conn.cursor()

    ingredient_changes = data.get("ingredient_changes", {})
    overhead_changes = data.get("overhead_changes", {})
    selling_price_t1 = data.get("selling_price_t1")
    selling_price_t2 = data.get("selling_price_t2")

    # Get overhead params
    c.execute("SELECT name, value, param_type, food_type FROM overhead_params")
    params = {}
    for r in c.fetchall():
        val = overhead_changes.get(r["name"], r["value"])
        params[r["name"]] = {"value": float(val), "type": r["param_type"], "food_type": r["food_type"]}

    fixed_t1 = sum(p["value"] for p in params.values() if p["type"] == "fixed" and p["food_type"] in (0, 1))
    fixed_t2 = sum(p["value"] for p in params.values() if p["type"] == "fixed" and p["food_type"] in (0, 2))

    ins_t1 = params.get("contract_insurance_pct_t1", {}).get("value", 8.9)
    tax_t1 = params.get("tax_pct_t1", {}).get("value", 5)
    prof_t1 = params.get("profit_margin_pct_t1", {}).get("value", 12)
    ins_t2 = params.get("contract_insurance_pct_t2", {}).get("value", 8.9)
    tax_t2 = params.get("tax_pct_t2", {}).get("value", 3)
    prof_t2 = params.get("profit_margin_pct_t2", {}).get("value", 12)

    c.execute("SELECT key, value FROM settings")
    settings = {r["key"]: float(r["value"]) for r in c.fetchall()}
    sp1 = float(selling_price_t1) if selling_price_t1 else settings.get("selling_price_type1", 2150000)
    sp2 = float(selling_price_t2) if selling_price_t2 else settings.get("selling_price_type2", 2150000)

    c.execute("SELECT id, code, name, food_type FROM foods ORDER BY food_type, code")
    results = []
    for food in c.fetchall():
        c2 = conn.cursor()
        c2.execute("SELECT ingredient_name, amount, cost FROM food_ingredients WHERE food_id=?", (food["id"],))
        raw_cost = 0
        for fi in c2.fetchall():
            if fi["ingredient_name"] in ingredient_changes:
                raw_cost += fi["amount"] * float(ingredient_changes[fi["ingredient_name"]])
            else:
                raw_cost += fi["cost"]

        if food["food_type"] == 1:
            base = raw_cost + fixed_t1
            pct = ins_t1 + tax_t1 + prof_t1
        else:
            base = raw_cost + fixed_t2
            pct = ins_t2 + tax_t2 + prof_t2
        total_cost = base + (base * pct / 100)
        sp = sp1 if food["food_type"] == 1 else sp2
        diff = sp - total_cost
        results.append({
            "id": food["id"], "code": food["code"], "name": food["name"],
            "food_type": food["food_type"],
            "raw_cost": round(raw_cost), "total_cost": round(total_cost),
            "selling_price": round(sp), "profit_loss": round(diff),
            "is_profit": diff >= 0,
        })

    conn.close()
    return jsonify({"foods": results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
