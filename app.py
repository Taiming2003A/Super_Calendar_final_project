# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, date, timedelta
import calendar

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///calendar.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "devkey"
db = SQLAlchemy(app)

# ===== 常數 =====
ITEM_TYPES = [("工作", "工作"), ("提醒", "提醒"), ("活動", "活動")]
MEAL_TYPES = [("早餐", "早餐"), ("午餐", "午餐"), ("晚餐", "晚餐"), ("點心", "點心")]

# 重訓分類與運動清單（同一動作可出現在多個部位分類，例如「啞鈴飛鳥」）
STRENGTH_CATEGORIES = {
    "胸部": ["臥推", "啞鈴飛鳥", "啞鈴胸夾", "伏地挺身"],
    "背部": ["引體向上", "槓鈴或啞鈴划船", "坐姿划船"],
    "腿部": ["深蹲", "硬舉", "弓箭步", "腿推機"],
    "臀部": ["臀推", "羅馬尼亞硬舉", "臀橋"],
    "手臂": ["二頭肌彎舉", "三頭肌撐體"],
    "核心": ["仰臥抬腿", "棒式支撐", "捲腹"],
    "肩部": ["肩推", "啞鈴飛鳥"],
}

# ===== 資料表 =====
class CalendarItem(db.Model):
    __tablename__ = "calendar_items"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    item_type = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    content = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    def time_range_str(self):
        return f"{self.start_time.strftime('%H:%M')}–{self.end_time.strftime('%H:%M')}"

class DietEntry(db.Model):
    __tablename__ = "diet_entries"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    meal_type = db.Column(db.String(10), nullable=False)
    food_name = db.Column(db.String(120), nullable=False)
    kcal = db.Column(db.Float, default=0.0)
    protein_g = db.Column(db.Float, default=0.0)
    fat_g = db.Column(db.Float, default=0.0)
    carb_g = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=func.now())

class StrengthSet(db.Model):
    """
    重訓『一組』為一列：紀錄日期、部位、動作、重量(kg)、次數。
    方便統計總重量(Σ weight*reps) 與主畫面快速判斷當日是否有重訓。
    """
    __tablename__ = "strength_sets"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    body_part = db.Column(db.String(10), nullable=False)       # 胸部/背部/腿部/臀部/手臂/核心/肩部
    exercise_name = db.Column(db.String(50), nullable=False)    # 臥推/深蹲/...
    weight_kg = db.Column(db.Float, default=0.0)               # 可為 0（體重訓練）
    reps = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=func.now())

with app.app_context():
    db.create_all()

# ===== 輔助 =====
def month_range(year: int, month: int):
    first_day = date(year, month, 1)
    _, last = calendar.monthrange(year, month)
    return first_day, date(year, month, last)

def month_nav(year: int, month: int):
    this = date(year, month, 1)
    prev_month = (this.replace(day=1) - timedelta(days=1)).replace(day=1)
    next_month = (this.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (prev_month.year, prev_month.month), (next_month.year, next_month.month)

def week_start(d: date):
    return d - timedelta(days=d.weekday())  # 以週一為首

def week_range_from_start(monday: date):
    return [monday + timedelta(days=i) for i in range(7)]

def strength_dates_between(start_d: date, end_d: date):
    """回傳在區間內『有至少一組重訓』的日期 set"""
    rows = (
        StrengthSet.query.with_entities(StrengthSet.date)
        .filter(StrengthSet.date.between(start_d, end_d))
        .group_by(StrengthSet.date)
        .all()
    )
    return {r.date for r in rows}

# ===== 路由：月檢視 =====
@app.route("/")
def index():
    try:
        year = int(request.args.get("year", datetime.today().year))
        month = int(request.args.get("month", datetime.today().month))
    except ValueError:
        year, month = datetime.today().year, datetime.today().month

    first_day, last_day = month_range(year, month)

    items = (
        CalendarItem.query.filter(CalendarItem.date.between(first_day, last_day))
        .order_by(CalendarItem.date.asc(), CalendarItem.start_time.asc())
        .all()
    )
    items_by_date = {}
    for it in items:
        items_by_date.setdefault(it.date, []).append(it)

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    prev_y, prev_m = month_nav(year, month)[0]
    next_y, next_m = month_nav(year, month)[1]

    # 這個月哪些日期有重訓 → 主畫面小圖示用
    strength_dates = strength_dates_between(first_day, last_day)

    return render_template(
        "index.html",
        year=year, month=month, weeks=weeks,
        items_by_date=items_by_date,
        prev_year=prev_y, prev_month=prev_m,
        next_year=next_y, next_month=next_m,
        today=date.today(),
        strength_dates=strength_dates,  # 傳給模板
    )

# ===== 路由：週檢視 =====
@app.route("/week")
def week_view():
    start_str = request.args.get("start")
    if start_str:
        try:
            monday = datetime.strptime(start_str, "%Y-%m-%d").date()
        except ValueError:
            monday = week_start(date.today())
    else:
        monday = week_start(date.today())

    days = week_range_from_start(monday)
    start_d, end_d = days[0], days[-1]

    items = (
        CalendarItem.query
        .filter(CalendarItem.date.between(start_d, end_d))
        .order_by(CalendarItem.date.asc(), CalendarItem.start_time.asc())
        .all()
    )
    items_by_date = {}
    for it in items:
        items_by_date.setdefault(it.date, []).append(it)

    # 這週哪些日期有重訓
    strength_dates = strength_dates_between(start_d, end_d)

    prev_week = monday - timedelta(days=7)
    next_week = monday + timedelta(days=7)

    return render_template(
        "week.html",
        days=days,
        items_by_date=items_by_date,
        monday=monday,
        prev_start=prev_week.strftime("%Y-%m-%d"),
        next_start=next_week.strftime("%Y-%m-%d"),
        today=date.today(),
        strength_dates=strength_dates,  # 傳給模板
    )

# ===== 路由：日檢視（含飲食＋重訓） =====
@app.route("/day/<string:datestr>")
def day_view(datestr):
    try:
        d = datetime.strptime(datestr, "%Y-%m-%d").date()
    except ValueError:
        flash("日期格式錯誤", "warning")
        return redirect(url_for("index"))

    # 行事項
    items = (
        CalendarItem.query
        .filter(CalendarItem.date == d)
        .order_by(CalendarItem.start_time.asc())
        .all()
    )

    # 飲食
    diets = DietEntry.query.filter(DietEntry.date == d).order_by(DietEntry.created_at.asc()).all()
    totals_diet = {
        "kcal": sum(x.kcal or 0 for x in diets),
        "protein_g": sum(x.protein_g or 0 for x in diets),
        "fat_g": sum(x.fat_g or 0 for x in diets),
        "carb_g": sum(x.carb_g or 0 for x in diets),
    }
    diets_by_meal = {}
    for de in diets:
        diets_by_meal.setdefault(de.meal_type, []).append(de)

    # 重訓（每組一列）
    sets_ = (
        StrengthSet.query
        .filter(StrengthSet.date == d)
        .order_by(StrengthSet.created_at.asc())
        .all()
    )
    # 總重量(kg) = Σ(weight * reps)
    total_weight = sum((s.weight_kg or 0) * (s.reps or 0) for s in sets_)

    # 依「部位 → 動作」分組
    by_part = {}
    for s in sets_:
        by_part.setdefault(s.body_part, {})
        by_part[s.body_part].setdefault(s.exercise_name, []).append(s)

    prev_day, next_day = d - timedelta(days=1), d + timedelta(days=1)

    return render_template(
        "day.html",
        d=d, items=items,
        diets_by_meal=diets_by_meal, totals_diet=totals_diet, MEAL_TYPES=MEAL_TYPES,
        strength_by_part=by_part, total_weight=total_weight,
        STRENGTH_CATEGORIES=STRENGTH_CATEGORIES,
        prev_day=prev_day, next_day=next_day
    )

# ===== 飲食：新增/刪除 =====
@app.route("/diet/add", methods=["POST"])
def diet_add():
    try:
        d = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        meal_type = request.form["meal_type"]
        food_name = request.form["food_name"].strip()
        kcal = float(request.form.get("kcal", 0) or 0)
        protein_g = float(request.form.get("protein_g", 0) or 0)
        fat_g = float(request.form.get("fat_g", 0) or 0)
        carb_g = float(request.form.get("carb_g", 0) or 0)

        if meal_type not in [t for t in dict(MEAL_TYPES)]:
            flash("餐別不支援", "warning")
            return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))
        if not food_name:
            flash("食品名稱不可為空", "warning")
            return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))

        db.session.add(DietEntry(date=d, meal_type=meal_type, food_name=food_name,
                                 kcal=kcal, protein_g=protein_g, fat_g=fat_g, carb_g=carb_g))
        db.session.commit()
        flash("已新增飲食紀錄", "success")
    except Exception as e:
        flash(f"新增失敗：{e}", "danger")

    return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))

@app.route("/diet/delete/<int:diet_id>", methods=["POST"])
def diet_delete(diet_id):
    de = DietEntry.query.get_or_404(diet_id)
    d = de.date
    db.session.delete(de)
    db.session.commit()
    flash("已刪除飲食紀錄", "info")
    return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))

# ===== 重訓：新增/刪除 =====
@app.route("/strength/add", methods=["POST"])
def strength_add():
    try:
        d = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        body_part = request.form["body_part"]
        exercise_name = request.form["exercise_name"]
        weight_kg = float(request.form.get("weight_kg", 0) or 0)
        reps = int(request.form.get("reps", 0) or 0)

        # 驗證分類與動作
        valid = body_part in STRENGTH_CATEGORIES and exercise_name in sum(STRENGTH_CATEGORIES.values(), [])
        if not valid:
            flash("重訓分類/動作不支援", "warning")
            return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))
        if exercise_name not in STRENGTH_CATEGORIES[body_part]:
            # 允許「同一動作可屬於多分類」→ 若使用者選了不同分類也合理，但仍提示
            flash("提示：此動作通常歸於其他部位分類，但仍已記錄。", "info")

        db.session.add(StrengthSet(date=d, body_part=body_part, exercise_name=exercise_name,
                                   weight_kg=weight_kg, reps=reps))
        db.session.commit()
        flash("已新增重訓一組", "success")
    except Exception as e:
        flash(f"新增失敗：{e}", "danger")

    return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))

@app.route("/strength/delete/<int:set_id>", methods=["POST"])
def strength_delete(set_id):
    s = StrengthSet.query.get_or_404(set_id)
    d = s.date
    db.session.delete(s)
    db.session.commit()
    flash("已刪除重訓組數", "info")
    return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))

# ===== 行事項 CRUD（原樣） =====
@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        try:
            title = request.form["title"].strip()
            item_type = request.form["item_type"]
            date_str = request.form["date"]
            start_str = request.form["start_time"]
            end_str = request.form["end_time"]
            content = request.form.get("content", "").strip()

            if not title:
                flash("標題不可為空", "warning")
                return redirect(request.url)
            if item_type not in [t for t in dict(ITEM_TYPES)]:
                flash("不支援的項目類型", "warning")
                return redirect(request.url)

            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            st = datetime.strptime(start_str, "%H:%M").time()
            et = datetime.strptime(end_str, "%H:%M").time()
            if et <= st:
                flash("結束時間必須晚於開始時間", "warning")
                return redirect(request.url)

            db.session.add(CalendarItem(title=title, item_type=item_type, date=d,
                                        start_time=st, end_time=et, content=content))
            db.session.commit()
            flash("已新增項目", "success")
            return redirect(url_for("index", year=d.year, month=d.month))
        except Exception as e:
            flash(f"發生錯誤：{e}", "danger")
            return redirect(request.url)

    default_date = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    return render_template("form.html", mode="add", ITEM_TYPES=ITEM_TYPES, default_date=default_date)

@app.route("/edit/<int:item_id>", methods=["GET", "POST"])
def edit(item_id):
    it = CalendarItem.query.get_or_404(item_id)
    if request.method == "POST":
        try:
            title = request.form["title"].strip()
            item_type = request.form["item_type"]
            date_str = request.form["date"]
            start_str = request.form["start_time"]
            end_str = request.form["end_time"]
            content = request.form.get("content", "").strip()

            if not title:
                flash("標題不可為空", "warning")
                return redirect(request.url)
            if item_type not in [t for t in dict(ITEM_TYPES)]:
                flash("不支援的項目類型", "warning")
                return redirect(request.url)

            it.title = title
            it.item_type = item_type
            it.date = datetime.strptime(date_str, "%Y-%m-%d").date()
            it.start_time = datetime.strptime(start_str, "%H:%M").time()
            it.end_time = datetime.strptime(end_str, "%H:%M").time()
            it.content = content

            if it.end_time <= it.start_time:
                flash("結束時間必須晚於開始時間", "warning")
                return redirect(request.url)

            db.session.commit()
            flash("已更新項目", "success")
            return redirect(url_for("index", year=it.date.year, month=it.date.month))
        except Exception as e:
            flash(f"發生錯誤：{e}", "danger")
            return redirect(request.url)

    return render_template("form.html", mode="edit", ITEM_TYPES=ITEM_TYPES, item=it)

@app.route("/delete/<int:item_id>", methods=["POST"])
def delete(item_id):
    it = CalendarItem.query.get_or_404(item_id)
    y, m = it.date.year, it.date.month
    db.session.delete(it)
    db.session.commit()
    flash("已刪除項目", "info")
    return redirect(url_for("index", year=y, month=m))

if __name__ == "__main__":
    app.run(debug=True)
