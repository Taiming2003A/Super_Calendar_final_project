from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime, date, timedelta
import calendar
from flask import jsonify

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///calendar.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "devkey"
db = SQLAlchemy(app)

# ===== 常數 =====
ITEM_TYPES = [("工作", "工作"), ("提醒", "提醒"), ("活動", "活動")]
MEAL_TYPES = [("早餐", "早餐"), ("午餐", "午餐"), ("晚餐", "晚餐"), ("點心", "點心")]

STRENGTH_CATEGORIES = {
    "胸部": ["臥推", "啞鈴飛鳥", "啞鈴胸夾", "伏地挺身"],
    "背部": ["引體向上", "槓鈴或啞鈴划船", "坐姿划船"],
    "腿部": ["深蹲", "硬舉", "弓箭步", "腿推機"],
    "臀部": ["臀推", "羅馬尼亞硬舉", "臀橋"],
    "手臂": ["二頭肌彎舉", "三頭肌撐體"],
    "核心": ["仰臥抬腿", "棒式支撐", "捲腹"],
    "肩部": ["肩推", "啞鈴飛鳥"],
}

WEEKDAY_CHOICES = [
    ("M", "星期一"),
    ("T", "星期二"),
    ("W", "星期三"),
    ("R", "星期四"),
    ("F", "星期五"),
    ("S", "星期六"),
    ("U", "星期日"),
]

SECTION_CHOICES = [
    "0","1","2","3","4","5","6","7","8","9","10","A","B","C","D"
]

# 全域營養目標用的虛擬日期
GLOBAL_GOAL_DATE = date(2000, 1, 1)

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
    __tablename__ = "strength_sets"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    body_part = db.Column(db.String(10), nullable=False)
    exercise_name = db.Column(db.String(50), nullable=False)
    weight_kg = db.Column(db.Float, default=0.0)
    reps = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=func.now())

class TimetableEntry(db.Model):
    __tablename__ = "timetable_entries"
    id = db.Column(db.Integer, primary_key=True)
    # 星期：M, T, W, R, F, S, U（對應台科大：一二三四五六日）
    weekday_code = db.Column(db.String(1), nullable=False)
    # 節次：0,1,2,3,4,5,6,7,8,9,10,A,B,C,D
    section = db.Column(db.String(2), nullable=False)
    course_name = db.Column(db.String(120), nullable=False)
    classroom = db.Column(db.String(50), nullable=True)
    teacher = db.Column(db.String(50), nullable=True)
    note = db.Column(db.String(200), nullable=True)

class DailyNutritionGoal(db.Model):
    """
    全域營養目標：只使用表中的第一筆（用 GLOBAL_GOAL_DATE 存）
    """
    __tablename__ = "daily_nutrition_goals"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    kcal_target = db.Column(db.Float, default=0.0)
    carb_target = db.Column(db.Float, default=0.0)
    protein_target = db.Column(db.Float, default=0.0)
    fat_target = db.Column(db.Float, default=0.0)

class ImportantItem(db.Model):
    __tablename__ = "important_items"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

# ===== 新增：體重紀錄表 =====
class WeightEntry(db.Model):
    __tablename__ = "weight_entries"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    weight_kg = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())

# 如果你剛加入 model，需要確保 db.create_all() 有執行（你檔案中已有 with app.app_context(): db.create_all()）

with app.app_context():
    db.create_all()

# ===== 小工具 =====
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
    return d - timedelta(days=d.weekday())

def week_range_from_start(monday: date):
    return [monday + timedelta(days=i) for i in range(7)]

def strength_dates_between(start_d: date, end_d: date):
    rows = (
        StrengthSet.query.with_entities(StrengthSet.date)
        .filter(StrengthSet.date.between(start_d, end_d))
        .group_by(StrengthSet.date)
        .all()
    )
    return {r.date for r in rows}

def get_global_nutrition_goal():
    """取得全域營養目標（如果沒有就回傳 None）"""
    return DailyNutritionGoal.query.order_by(DailyNutritionGoal.id.asc()).first()

def get_next_important():
    """取得最近一個尚未過期的重要事項與剩餘天數"""
    today = date.today()
    row = (
        ImportantItem.query
        .filter(ImportantItem.date >= today)
        .order_by(ImportantItem.date.asc())
        .first()
    )
    if row:
        days_left = (row.date - today).days
        return row, days_left
    return None, None

# ===== 首頁（月檢視） =====
@app.route("/")
def index():
    try:
        year = int(request.args.get("year", datetime.today().year))
        month = int(request.args.get("month", datetime.today().month))
    except ValueError:
        year, month = datetime.today().year, datetime.today().month

    first_day, last_day = month_range(year, month)

    items = (
        CalendarItem.query
        .filter(CalendarItem.date.between(first_day, last_day))
        .order_by(CalendarItem.date.asc(), CalendarItem.start_time.asc())
        .all()
    )
    items_by_date = {}
    for it in items:
        items_by_date.setdefault(it.date, []).append(it)

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)

    (prev_y, prev_m), (next_y, next_m) = month_nav(year, month)
    strength_dates = strength_dates_between(first_day, last_day)

    nutrition_goal = get_global_nutrition_goal()

    next_important, next_important_days = get_next_important()


    return render_template(
        "index.html",
        year=year,
        month=month,
        weeks=weeks,
        items_by_date=items_by_date,
        prev_year=prev_y,
        prev_month=prev_m,
        next_year=next_y,
        next_month=next_m,
        today=date.today(),
        strength_dates=strength_dates,
        nutrition_goal=nutrition_goal,
        next_important=next_important,
        next_important_days=next_important_days,
    )

@app.route("/timetable", methods=["GET"])
def timetable():
    # 依星期、節次排序顯示
    entries = (
        TimetableEntry.query
        .order_by(TimetableEntry.weekday_code.asc(), TimetableEntry.section.asc())
        .all()
    )

    # 做一個 dict，讓模板好用：key = (weekday_code, section)
    entries_by_key = {}
    for e in entries:
        entries_by_key.setdefault((e.weekday_code, e.section), []).append(e)

    # ===== 合併相同課名且時間連續的格子（用 rowspan） =====
    merged_cells = {}  # key: (weekday_code, section) -> {"entry": e, "rowspan": n}
    skip_slots = set()  # 被上方合併覆蓋掉的 (weekday_code, section)

    for weekday_code, _ in WEEKDAY_CHOICES:
        sec_list = SECTION_CHOICES
        i = 0
        while i < len(sec_list):
            sec = sec_list[i]
            key = (weekday_code, sec)
            slot_entries = entries_by_key.get(key, [])

            # 如果這一節沒有課，直接下一節
            if len(slot_entries) != 1:
                i += 1
                continue

            # 先假設只有一門課，抓第一筆當代表
            e0 = slot_entries[0]
            span = 1
            j = i + 1

            # 往下面找連續節次，判斷是否可以合併
            while j < len(sec_list):
                next_sec = sec_list[j]
                key2 = (weekday_code, next_sec)
                slot_entries2 = entries_by_key.get(key2, [])

                # 只在「下一節也只有一門課」的情況下考慮合併
                if len(slot_entries2) != 1:
                    break

                e2 = slot_entries2[0]
                # 判斷「相同課」：課名 + 教室 + 老師 + 備註 都相同就視為同一門課
                if (
                    e2.course_name == e0.course_name
                    and (e2.classroom or "") == (e0.classroom or "")
                    and (e2.teacher or "") == (e0.teacher or "")
                    and (e2.note or "") == (e0.note or "")
                ):
                    span += 1
                    skip_slots.add((weekday_code, next_sec))
                    j += 1
                else:
                    break

            # 這一節是合併區塊的起點
            merged_cells[key] = {"entry": e0, "rowspan": span}
            i = j

    return render_template(
        "timetable.html",
        WEEKDAY_CHOICES=WEEKDAY_CHOICES,
        SECTION_CHOICES=SECTION_CHOICES,
        entries_by_key=entries_by_key,
        entries=entries,
        merged_cells=merged_cells,
        skip_slots=skip_slots,
    )



@app.route("/timetable/add", methods=["POST"])
def timetable_add():
    weekday_code = request.form.get("weekday_code")
    section = request.form.get("section")
    course_name = (request.form.get("course_name") or "").strip()
    classroom = (request.form.get("classroom") or "").strip()
    teacher = (request.form.get("teacher") or "").strip()
    note = (request.form.get("note") or "").strip()

    if not course_name:
        flash("課程名稱不可為空", "warning")
        return redirect(url_for("timetable"))

    # 簡單防呆
    valid_weekdays = {w for w, _ in WEEKDAY_CHOICES}
    if weekday_code not in valid_weekdays or section not in SECTION_CHOICES:
        flash("星期或節次不正確", "warning")
        return redirect(url_for("timetable"))

    entry = TimetableEntry(
        weekday_code=weekday_code,
        section=section,
        course_name=course_name,
        classroom=classroom,
        teacher=teacher,
        note=note,
    )
    db.session.add(entry)
    db.session.commit()
    flash("已新增課表項目", "success")
    return redirect(url_for("timetable"))


@app.route("/timetable/delete/<int:entry_id>", methods=["POST"])
def timetable_delete(entry_id):
    entry = TimetableEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash("已刪除課表項目", "info")
    return redirect(url_for("timetable"))

# ===== 全域營養目標設定頁（含建議計算） =====
@app.route("/nutrition_goal", methods=["GET", "POST"])
def nutrition_goal_page():
    goal = get_global_nutrition_goal()

    suggestion = None
    calc_input = {
        "weight_kg": "",
        "sex": "male",
        "age": "",
        "goal_type": "maintain",
    }

    if request.method == "POST" and request.form.get("action") == "calc":
        # 取使用者輸入
        weight_str = (request.form.get("calc_weight") or "").strip()
        sex = request.form.get("calc_sex") or "male"
        age_str = (request.form.get("calc_age") or "").strip()
        goal_type = request.form.get("calc_goal") or "maintain"

        calc_input["weight_kg"] = weight_str
        calc_input["sex"] = sex
        calc_input["age"] = age_str
        calc_input["goal_type"] = goal_type

        try:
            weight_kg = float(weight_str)
            age = int(age_str) if age_str else 30
            if weight_kg <= 0:
                raise ValueError("體重需大於 0")
        except Exception:
            flash("請輸入有效的體重與年齡。", "warning")
            return render_template(
                "nutrition_goal.html",
                nutrition_goal=goal,
                suggestion=None,
                calc_input=calc_input,
            )

        # 1. 維持熱量估計（kcal/kg）
        if sex == "female":
            base_per_kg = 29.0
        else:
            base_per_kg = 31.0

        # 年齡微調
        if age <= 25:
            base_per_kg += 1.0
        elif age >= 50:
            base_per_kg -= 2.0

        maintenance_kcal = base_per_kg * weight_kg

        # 2. 依目標調整總熱量
        if goal_type == "lose":
            target_kcal = maintenance_kcal - 500.0
        elif goal_type == "gain":
            target_kcal = maintenance_kcal + 250.0
        else:
            target_kcal = maintenance_kcal

        # 不要太低
        if target_kcal < 1000:
            target_kcal = 1000.0

        # 3. 蛋白質（g/kg）
        if goal_type == "lose":
            protein_per_kg = 2.0
        elif goal_type == "gain":
            protein_per_kg = 1.8
        else:
            protein_per_kg = 1.6

        protein_g = protein_per_kg * weight_kg

        # 4. 脂肪（g/kg）
        fat_per_kg = 0.8
        fat_g = fat_per_kg * weight_kg

        # 5. 碳水：用剩餘熱量計算
        kcal_from_protein = protein_g * 4.0
        kcal_from_fat = fat_g * 9.0
        carb_kcal = max(target_kcal - (kcal_from_protein + kcal_from_fat), 0.0)
        carb_g = carb_kcal / 4.0

        suggestion = {
            "kcal": target_kcal,
            "maintenance_kcal": maintenance_kcal,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carb_g": carb_g,
        }

    return render_template(
        "nutrition_goal.html",
        nutrition_goal=goal,
        suggestion=suggestion,
        calc_input=calc_input,
    )

# ===== 週檢視 =====
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
        strength_dates=strength_dates,
    )

# ===== 日檢視 =====
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
    diets = (
        DietEntry.query
        .filter(DietEntry.date == d)
        .order_by(DietEntry.created_at.asc())
        .all()
    )
    totals_diet = {
        "kcal": sum(x.kcal or 0 for x in diets),
        "protein_g": sum(x.protein_g or 0 for x in diets),
        "fat_g": sum(x.fat_g or 0 for x in diets),
        "carb_g": sum(x.carb_g or 0 for x in diets),
    }
    diets_by_meal = {}
    for de in diets:
        diets_by_meal.setdefault(de.meal_type, []).append(de)

    # 全域營養目標
    goal = get_global_nutrition_goal()
    nutrition_goal = goal
    nutrition_diff = None
    nutrition_percent = None
    if goal:
        nutrition_diff = {}
        nutrition_percent = {}

        def handle(actual, target):
            target = target or 0.0
            diff = actual - target
            width_pct = None
            if target > 0:
                width_pct = min(100.0, (actual / target) * 100.0)
            return diff, width_pct

        nutrition_diff["kcal"], nutrition_percent["kcal"] = handle(
            totals_diet["kcal"], goal.kcal_target
        )
        nutrition_diff["carb"], nutrition_percent["carb"] = handle(
            totals_diet["carb_g"], goal.carb_target
        )
        nutrition_diff["protein"], nutrition_percent["protein"] = handle(
            totals_diet["protein_g"], goal.protein_target
        )
        nutrition_diff["fat"], nutrition_percent["fat"] = handle(
            totals_diet["fat_g"], goal.fat_target
        )

    # 重訓
    sets_ = (
        StrengthSet.query
        .filter(StrengthSet.date == d)
        .order_by(StrengthSet.created_at.asc())
        .all()
    )
    total_weight = sum((s.weight_kg or 0) * (s.reps or 0) for s in sets_)

    strength_by_part = {}
    by_exercise = {}
    for s in sets_:
        strength_by_part.setdefault(s.body_part, {}).setdefault(s.exercise_name, []).append(s)
        by_exercise.setdefault(s.exercise_name, []).append(s)

    exercise_best_set_id = {}
    for ex_name, lst in by_exercise.items():
        best = max(lst, key=lambda s: ((s.weight_kg or 0) * (s.reps or 0)))
        exercise_best_set_id[ex_name] = best.id

    prev_total_date = None
    prev_total_weight = None
    total_diff_vs_prev = None
    prev_row = (
        db.session.query(
            StrengthSet.date,
            func.sum(StrengthSet.weight_kg * StrengthSet.reps)
        )
        .filter(StrengthSet.date < d)
        .group_by(StrengthSet.date)
        .order_by(StrengthSet.date.desc())
        .first()
    )
    if prev_row:
        prev_total_date = prev_row[0]
        prev_total_weight = float(prev_row[1] or 0.0)
        total_diff_vs_prev = total_weight - prev_total_weight

    last_max_weight = {}
    rows = (
        db.session.query(
            StrengthSet.exercise_name,
            StrengthSet.date,
            func.max(StrengthSet.weight_kg),
        )
        .filter(StrengthSet.date < d)
        .group_by(StrengthSet.exercise_name, StrengthSet.date)
        .all()
    )
    for ex_name, ex_date, max_w in rows:
        entry = last_max_weight.get(ex_name)
        if entry is None or ex_date > entry["date"]:
            last_max_weight[ex_name] = {"date": ex_date, "weight": float(max_w or 0.0)}
    last_max_weight_simple = {name: v["weight"] for name, v in last_max_weight.items()}

    prev_day = d - timedelta(days=1)
    next_day = d + timedelta(days=1)

    return render_template(
        "day.html",
        d=d,
        items=items,
        diets_by_meal=diets_by_meal,
        totals_diet=totals_diet,
        MEAL_TYPES=MEAL_TYPES,
        nutrition_goal=nutrition_goal,
        nutrition_diff=nutrition_diff,
        nutrition_percent=nutrition_percent,
        strength_by_part=strength_by_part,
        total_weight=total_weight,
        exercise_best_set_id=exercise_best_set_id,
        last_max_weight=last_max_weight_simple,
        prev_total_weight=prev_total_weight,
        prev_total_date=prev_total_date,
        total_diff_vs_prev=total_diff_vs_prev,
        STRENGTH_CATEGORIES=STRENGTH_CATEGORIES,
        prev_day=prev_day,
        next_day=next_day,
    )

@app.route("/important", methods=["GET", "POST"])
def important():
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        date_str = request.form.get("date") or ""
        description = (request.form.get("description") or "").strip()

        if not title:
            flash("標題不可為空", "warning")
            return redirect(url_for("important"))

        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("日期格式錯誤", "warning")
            return redirect(url_for("important"))

        item = ImportantItem(title=title, date=d, description=description)
        db.session.add(item)
        db.session.commit()
        flash("已新增重要事項", "success")
        return redirect(url_for("important"))

    items = ImportantItem.query.order_by(ImportantItem.date.asc()).all()
    today = date.today()
    items_with_delta = []
    for it in items:
        days_left = (it.date - today).days
        items_with_delta.append((it, days_left))

    next_item, next_days = get_next_important()

    return render_template(
        "important.html",
        items_with_delta=items_with_delta,
        today=today,
        next_item=next_item,
        next_days=next_days,
    )


@app.route("/important/delete/<int:item_id>", methods=["POST"])
def important_delete(item_id):
    item = ImportantItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    flash("已刪除重要事項", "info")
    return redirect(url_for("important"))

# ===== 全域營養目標儲存 =====
@app.route("/nutrition_goal/save", methods=["POST"])
def save_nutrition_goal():
    def parse_float(name):
        val = (request.form.get(name, "") or "").strip()
        if not val:
            return 0.0
        try:
            return float(val)
        except ValueError:
            return 0.0

    kcal_t = parse_float("kcal_target")
    carb_t = parse_float("carb_target")
    protein_t = parse_float("protein_target")
    fat_t = parse_float("fat_target")

    goal = get_global_nutrition_goal()
    if not goal:
        goal = DailyNutritionGoal(date=GLOBAL_GOAL_DATE)
        db.session.add(goal)

    goal.kcal_target = kcal_t
    goal.carb_target = carb_t
    goal.protein_target = protein_t
    goal.fat_target = fat_t

    db.session.commit()
    flash("已更新全域營養目標", "success")
    return redirect(url_for("nutrition_goal_page"))

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

        db.session.add(DietEntry(
            date=d,
            meal_type=meal_type,
            food_name=food_name,
            kcal=kcal,
            protein_g=protein_g,
            fat_g=fat_g,
            carb_g=carb_g,
        ))
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

        all_exercises = set(sum(STRENGTH_CATEGORIES.values(), []))
        if body_part not in STRENGTH_CATEGORIES or exercise_name not in all_exercises:
            flash("重訓分類/動作不支援", "warning")
            return redirect(url_for("day_view", datestr=d.strftime("%Y-%m-%d")))

        db.session.add(StrengthSet(
            date=d,
            body_part=body_part,
            exercise_name=exercise_name,
            weight_kg=weight_kg,
            reps=reps,
        ))
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

# ===== 行事曆項目：新增 / 編輯 / 刪除 =====
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

            db.session.add(CalendarItem(
                title=title,
                item_type=item_type,
                date=d,
                start_time=st,
                end_time=et,
                content=content,
            ))
            db.session.commit()
            flash("已新增項目", "success")
            return redirect(url_for("index", year=d.year, month=d.month))
        except Exception as e:
            flash(f"發生錯誤：{e}", "danger")
            return redirect(request.url)

    default_date = request.args.get("date", date.today().strftime("%Y-%m-%d"))
    return render_template("form.html", mode="add", ITEM_TYPES=ITEM_TYPES,
                           default_date=default_date)

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

@app.route("/rest_timer")
def rest_timer():
    return render_template("rest_timer.html")


@app.route("/progress/<exercise_name>")
def progress(exercise_name):
    conn = get_db()
    cursor = conn.cursor()

    # 取每日該動作的最大重量
    cursor.execute("""
        SELECT date, MAX(weight_kg) 
        FROM strength
        WHERE exercise_name = ?
        GROUP BY date
        ORDER BY date
    """, (exercise_name,))
    rows = cursor.fetchall()

    dates = [r[0] for r in rows]
    max_weights = [r[1] for r in rows]

    return render_template(
        "progress.html",
        exercise_name=exercise_name,
        dates=dates,
        weights=max_weights
    )

@app.route("/weight", methods=["GET", "POST"])
def weight_page():
    """
    顯示體重列表、表單新增，以及顯示進步曲線（以 Chart.js 繪圖）。
    GET: 顯示頁面
    POST: 新增一筆體重紀錄 (date, weight_kg) 然後 redirect 回 /weight
    """
    if request.method == "POST":
        # 取值並簡單驗證
        date_str = (request.form.get("date") or "").strip()
        weight_str = (request.form.get("weight_kg") or "").strip()
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            w = float(weight_str)
            entry = WeightEntry(date=d, weight_kg=w)
            db.session.add(entry)
            db.session.commit()
            flash("已新增體重紀錄", "success")
        except Exception as e:
            flash(f"新增失敗：{e}", "danger")
        return redirect(url_for("weight_page"))

    # GET: 讀出所有體重紀錄（按日期排序）並傳給 template
    rows = (
        WeightEntry.query
        .order_by(WeightEntry.date.asc())
        .all()
    )
    # template 偏好 arrays of strings/floats
    dates = [r.date.strftime("%Y-%m-%d") for r in rows]
    weights = [r.weight_kg for r in rows]

    return render_template(
        "weight.html",
        rows=rows,
        dates=dates,
        weights=weights,
    )

@app.route("/weight/delete/<int:entry_id>", methods=["POST"])
def weight_delete(entry_id):
    w = WeightEntry.query.get_or_404(entry_id)
    db.session.delete(w)
    db.session.commit()
    flash("已刪除體重紀錄", "info")
    return redirect(url_for("weight_page"))

    
if __name__ == "__main__":
    app.run(debug=True)

print(app.url_map)
