from flask import Flask, request, Response
import mysql.connector
import hashlib
import base64
import gzip
import io
import time
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per minute"]
)

@app.errorhandler(429)
def rate_limit_handler(e):
    return "RATE LIMITED ツ Please dont sent a gazillion requests", 429

# ---------------- DB ----------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="geometrydash"
    )

SECRET_LOGIN = "Wmfv3899gc9"
SECRET_INFO = "Wmfd2893gb7"
SECRET_COMMENT = "Wmfd2893gb7"
geometrydash = get_db()
db = get_db()

@app.route('/downloadGJLevel22.php', methods=['POST'])
def download_gj_level_22():
    import time

    level_id = request.form.get("levelID")
    game_version = int(request.form.get("gameVersion", 1))
    extras = request.form.get("extras") is not None
    inc = request.form.get("inc") is not None
    ip = request.remote_addr or "127.0.0.1"
    binary_version = int(request.form.get("binaryVersion", 0))

    if not level_id or not level_id.isnumeric():
        return "-1"

    level_id = int(level_id)

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM levels WHERE levelID=%s", (level_id,))
    level = cursor.fetchone()

    if not level:
        cursor.close()
        db.close()
        return "-1"

    # user info
    cursor.execute("SELECT userName, userID FROM users WHERE userID=%s", (level["userID"],))
    user = cursor.fetchone()

    username = user["userName"] if user else "Unknown"

    # downloads + anti spam
    cursor.execute(
        "SELECT COUNT(*) FROM actions_downloads WHERE levelID=%s AND ip=INET6_ATON(%s)",
        (level_id, ip)
    )
    already = cursor.fetchone()["COUNT(*)"]

    if inc and already < 2:
        cursor.execute("UPDATE levels SET downloads = downloads + 1 WHERE levelID=%s", (level_id,))
        cursor.execute(
            "INSERT INTO actions_downloads (levelID, ip) VALUES (%s, INET6_ATON(%s))",
            (level_id, ip)
        )

    db.commit()

    # level string (IMPORTANT FIX)
    level_string = None

    file_path = f"data/levels/{level_id}"
    try:
        with open(file_path, "r") as f:
            level_string = f.read().strip()
    except:
        level_string = level.get("levelString", "")

    # DO NOT decompress or re-encode here (GD expects kS1/raw stored format)

    upload_date = int(level.get("uploadDate", int(time.time())))
    update_date = int(level.get("updateDate", int(time.time())))

    desc = level.get("levelDesc", "")
    password = level.get("password", "0")

    response = (
        f"1:{level['levelID']}"
        f":2:{level['levelName']}"
        f":3:{desc}"
        f":4:{level_string}"
        f":5:{level['levelVersion']}"
        f":6:{level['userID']}"
        f":8:10"
        f":9:{level['starDifficulty']}"
        f":10:{level['downloads']}"
        f":11:1"
        f":12:{level['audioTrack']}"
        f":13:{level['gameVersion']}"
        f":14:{level['likes']}"
        f":17:{level['starDemon']}"
        f":43:{level['starDemonDiff']}"
        f":25:{level['starAuto']}"
        f":18:{level['starStars']}"
        f":19:{level['starFeatured']}"
        f":42:{level['starEpic']}"
        f":45:{level['objects']}"
        f":15:{level['levelLength']}"
        f":30:{level['original']}"
        f":31:{level['twoPlayer']}"
        f":28:{upload_date}"
        f":29:{update_date}"
        f":35:{level['songID']}"
        f":36:{level['extraString']}"
        f":37:{level['coins']}"
        f":38:{level['starCoins']}"
        f":39:{level['requestedStars']}"
        f":40:{level['isLDM']}"
        f":27:{password}"
        f"#LEVELHASH#"
        f"#USERHASH#"
    )

    cursor.close()
    db.close()

    return response

@app.route('/uploadGJLevel21.php', methods=['POST'])
def upload_gj_level_21():

    game_version = request.form.get("gameVersion")
    binary_version = request.form.get("binaryVersion", 0)

    account_id = request.form.get("accountID")
    gjp2 = request.form.get("gjp2")
    username = request.form.get("userName")

    level_id = request.form.get("levelID")

    level_name = request.form.get("levelName")
    level_desc = request.form.get("levelDesc")
    level_version = request.form.get("levelVersion")
    level_length = request.form.get("levelLength")

    audio_track = request.form.get("audioTrack")
    auto = request.form.get("auto")
    password = request.form.get("password")
    original = request.form.get("original")
    two_player = request.form.get("twoPlayer")

    song_id = request.form.get("songID")
    objects = request.form.get("objects")
    coins = request.form.get("coins")
    requested_stars = request.form.get("requestedStars")

    unlisted = request.form.get("unlisted")
    ldm = request.form.get("ldm")

    level_string = request.form.get("levelString")
    extra_string = request.form.get("extraString", "")
    level_info = request.form.get("levelInfo", "")
    wt = request.form.get("wt", 0)
    wt2 = request.form.get("wt2", 0)
    ts = request.form.get("ts", 0)

    secret = request.form.get("secret")

    if secret != "Wmfd2893gb7":
        return "-1"

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # ---------------- ACCOUNT CHECK ----------------
    cursor.execute(
        "SELECT accountID, password FROM accounts WHERE accountID=%s",
        (account_id,)
    )
    acc = cursor.fetchone()

    if not acc:
        cursor.close()
        db.close()
        return "-1"

    def gen_gjp2(p):
        return hashlib.sha1((p + "mI29fmAnxgTs").encode()).hexdigest()

    if gjp2 != gen_gjp2(acc["password"]):
        cursor.close()
        db.close()
        return "-11"

    def i(x):
        try:
            return int(x)
        except:
            return 0

    # ---------------- DECODE LEVEL DESC ----------------
    try:
        desc = base64.urlsafe_b64decode(level_desc.encode()).decode()
    except:
        desc = ""

    # ---------------- FIX: DECODE LEVEL STRING PROPERLY ----------------
    try:
        raw = base64.urlsafe_b64decode(level_string.encode())
        level_string = gzip.decompress(raw).decode()   # 🔥 IMPORTANT FIX
    except:
        cursor.close()
        db.close()
        return "-1"

    now = int(time.time())

    LEVEL_DIR = "data/levels"
    os.makedirs(LEVEL_DIR, exist_ok=True)

    # ---------------- UPDATE ----------------
    if level_id and str(level_id) != "0":

        cursor.execute("""
            UPDATE levels SET
                levelName=%s,
                levelDesc=%s,
                levelVersion=%s,
                levelLength=%s,
                audioTrack=%s,
                auto=%s,
                password=%s,
                original=%s,
                twoPlayer=%s,
                songID=%s,
                objects=%s,
                coins=%s,
                requestedStars=%s,
                extraString=%s,
                levelString=%s,
                levelInfo=%s,
                unlisted=%s,
                isLDM=%s,
                wt=%s,
                wt2=%s,
                ts=%s,
                updateDate=%s
            WHERE levelID=%s AND userID=%s
        """, (
            level_name, desc, i(level_version), i(level_length),
            i(audio_track), i(auto), i(password), i(original),
            i(two_player), i(song_id), i(objects), i(coins),
            i(requested_stars), extra_string, level_string,
            level_info, i(unlisted), i(ldm),
            i(wt), i(wt2), i(ts), now,
            level_id, account_id
        ))

        new_id = level_id

    # ---------------- INSERT ----------------
    else:

        cursor.execute("""
            INSERT INTO levels (
                gameVersion, binaryVersion, userName,
                levelName, levelDesc, levelVersion, levelLength,
                audioTrack, auto, password, original, twoPlayer,
                songID, objects, coins, requestedStars,
                extraString, levelString, levelInfo,
                secret, userID, extID, unlisted, isLDM,
                uploadDate, updateDate, wt, wt2, ts, hostname
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            i(game_version), i(binary_version), username,
            level_name, desc, i(level_version), i(level_length),
            i(audio_track), i(auto), i(password), i(original),
            i(two_player), i(song_id), i(objects), i(coins),
            i(requested_stars), extra_string, level_string,
            level_info, secret, account_id, account_id,
            i(unlisted), i(ldm), now, now,
            i(wt), i(wt2), i(ts), "localhost"
        ))

        new_id = cursor.lastrowid

    # ---------------- SAVE LEVEL FILE ----------------
    with open(f"{LEVEL_DIR}/{new_id}", "w") as f:
        f.write(level_string)   # RAW kS1 STRING ONLY

    db.commit()
    cursor.close()
    db.close()

    return str(new_id)

@app.route('/getGJLevels21.php', methods=['POST'])
def get_gj_levels_21():
    secret = request.form.get("secret")
    if secret != "Wmfd2893gb7":
        return "-1"

    search = request.form.get("str", "")
    page = int(request.form.get("page", 0))
    type_ = int(request.form.get("type", 2))

    diff = request.form.get("diff")
    length = request.form.get("len")
    featured = request.form.get("featured")
    two_player = request.form.get("twoPlayer")
    coins = request.form.get("coins")
    epic = request.form.get("epic")
    star = request.form.get("star")
    no_star = request.form.get("noStar")

    account_id = request.form.get("accountID")

    offset = page * 10

    db = get_db()
    cursor = db.cursor(dictionary=True)

    query = "SELECT * FROM levels WHERE isDeleted=0"
    params = []

    # ---------------- TYPE ----------------
    if type_ == 0 and search:
        query += " AND levelName LIKE %s"
        params.append(search + "%")

    elif type_ == 1:
        query += " ORDER BY downloads DESC"

    elif type_ == 2:
        query += " ORDER BY likes DESC"

    elif type_ == 3:
        query += " ORDER BY likes DESC"

    elif type_ == 4:
        query += " ORDER BY levelID DESC"

    elif type_ == 5:
        if search and search.isdigit():
            query += " AND userID=%s"
            params.append(search)

    elif type_ == 10:
        if search:
            ids = [x for x in search.split(",") if x.isdigit()]
            if ids:
                query += " AND levelID IN (" + ",".join(["%s"] * len(ids)) + ")"
                params.extend(ids)

    # ---------------- FILTERS ----------------
    if diff:
        diff_list = [d for d in diff.split(",") if d.lstrip("-").isdigit()]
        if diff_list:
            query += " AND starDifficulty IN (" + ",".join(["%s"] * len(diff_list)) + ")"
            params.extend(diff_list)

    if length and length.isdigit():
        query += " AND levelLength=%s"
        params.append(length)

    if featured == "1":
        query += " AND starFeatured=1"

    if epic == "1":
        query += " AND starEpic=1"

    if two_player == "1":
        query += " AND twoPlayer=1"

    if coins == "1":
        query += " AND coins>0"

    if star == "1":
        query += " AND starStars>0"

    if no_star == "1":
        query += " AND starStars=0"

    # fallback ORDER if not set
    if "ORDER BY" not in query:
        query += " ORDER BY likes DESC"

    query += " LIMIT 10 OFFSET %s"
    params.append(offset)

    cursor.execute(query, tuple(params))
    levels = cursor.fetchall()

    if not levels:
        cursor.close()
        db.close()
        return "-1"

    # total count
    count_query = "SELECT COUNT(*) as total FROM levels WHERE isDeleted=0"
    cursor.execute(count_query)
    total = cursor.fetchone()["total"]

    # ---------------- BUILD LEVELS ----------------
    lvl_out = []

    for l in levels:
        desc = l["levelDesc"] or ""
        try:
            desc = base64.b64encode(desc.encode()).decode()
        except:
            desc = ""

        lvl_out.append(
            f"1:{l['levelID']}:"
            f"2:{l['levelName']}:"
            f"5:{l['starDifficulty']}:"
            f"6:{l['levelID']}:"
            f"8:{l['starStars']}:"
            f"9:{l['coins']}:"
            f"10:{l['downloads']}:"
            f"12:0:"
            f"13:{l['userID']}:"
            f"14:{l['downloads']}:"
            f"17:1:"
            f"43:{l['starDifficulty']}:"
            f"45:{l['likes']}:"
            f"3:{desc}:"
            f"15:{l['levelVersion']}:"
            f"30:{l['songID']}"
        )

    # ---------------- CREATORS ----------------
    creators = []
    for l in levels:
        creators.append(f"{l['userID']}:{l['userName']}:{l['userID']}")

    # ---------------- SONGS (basic stub) ----------------
    songs = "1~|~0~|~2~|~Unknown~|~3~|~0~|~4~|~Unknown~|~5~|~0~|~6~|~~|~10~|~~|~7~|~~|~8~|~1~"

    cursor.close()
    db.close()

    return (
        "|".join(lvl_out)
        + "#"
        + "|".join(creators)
        + "#"
        + songs
        + f"#{total}:{offset}:10"
        + "#0"
    )

@app.route('/getAccountURL.php', methods=['GET', 'POST'])
def get_account_url():
    scheme = request.scheme  # http or https
    host = request.host      # domain + port

    # build full URL
    full_url = f"{scheme}://{host}"

    # mimic dirname() behavior
    return full_url.rsplit('/accounts/getAccountURL.php', 1)[0]

@app.route('/getGJUsers20.php', methods=['POST'])
def get_gj_users_20():
    secret = request.form.get("secret")
    search = request.form.get("str", "")

    if secret != "Wmfd2893gb7":
        return "-1"

    if not search:
        return "#0:0:10"

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT a.accountID, a.userName,
               u.stars, u.demons, u.coins, u.userCoins,
               u.diamonds, u.moons, u.creatorPoints
        FROM accounts a
        LEFT JOIN users u ON u.userID = a.accountID
        WHERE a.userName LIKE %s
        LIMIT 1
    """, (search + "%",))

    user = cursor.fetchone()

    cursor.close()
    db.close()

    if not user:
        return "#0:0:10"

    # safe ints
    def i(x):
        try:
            return int(x)
        except:
            return 0

    account_id = user["accountID"]

    stars = i(user.get("stars"))
    demons = i(user.get("demons"))
    coins = i(user.get("coins"))
    user_coins = i(user.get("userCoins"))
    diamonds = i(user.get("diamonds"))
    moons = i(user.get("moons"))
    creator_points = i(user.get("creatorPoints"))

    username = user["userName"]

    # -------------------------
    # FIXED GD FORMAT (IMPORTANT)
    # -------------------------
    response = (
        f"1:{username}:"
        f"2:{account_id}:"
        f"13:{coins}:"
        f"17:{user_coins}:"
        f"10:{stars}:"
        f"11:{demons}:"
        f"14:{diamonds}:"
        f"15:{moons}:"
        f"16:{account_id}:"
        f"8:{creator_points}"
    )

    # pagination footer (GD expects this)
    response += "#0:0:10"

    return response

@app.route('/updateGJUserScore22.php', methods=['POST'])
def update_user_score_22():
    import hashlib

    # -------------------------
    # REQUIRED CORE PARAMS
    # -------------------------
    account_id = request.form.get("accountID")
    gjp2 = request.form.get("gjp2")
    secret = request.form.get("secret")

    stars = request.form.get("stars")
    moons = request.form.get("moons")
    demons = request.form.get("demons")
    diamonds = request.form.get("diamonds")

    icon = request.form.get("icon")
    icon_type = request.form.get("iconType")

    coins = request.form.get("coins")
    user_coins = request.form.get("userCoins")

    acc_icon = request.form.get("accIcon")
    acc_ship = request.form.get("accShip")
    acc_ball = request.form.get("accBall")
    acc_bird = request.form.get("accBird")
    acc_dart = request.form.get("accDart")
    acc_robot = request.form.get("accRobot")
    acc_glow = request.form.get("accGlow")
    acc_spider = request.form.get("accSpider")
    acc_explosion = request.form.get("accExplosion")
    acc_swing = request.form.get("accSwing")
    acc_jetpack = request.form.get("accJetpack")

    seed2 = request.form.get("seed2")

    # -------------------------
    # REQUIRED STATS INFO BLOCK
    # -------------------------
    sinfo = request.form.get("sinfo")
    sinfod = request.form.get("sinfod")
    sinfog = request.form.get("sinfog")
    sinfoe = request.form.get("sinfoe")

    # optional extras
    dinfo = request.form.get("dinfo")
    dinfow = request.form.get("dinfow")
    dinfog = request.form.get("dinfog")
    dinfoe = request.form.get("dinfoe")

    seed = request.form.get("seed")

    # -------------------------
    # SECURITY CHECK
    # -------------------------
    if secret != "Wmfd2893gb7":
        return "-1"

    if not account_id or not gjp2:
        return "-1"

    # -------------------------
    # DB
    # -------------------------
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT accountID, password
        FROM accounts
        WHERE accountID=%s
    """, (account_id,))

    acc = cursor.fetchone()

    if not acc:
        cursor.close()
        db.close()
        return "-1"

    # -------------------------
    # GJP2 CHECK
    # -------------------------
    def gen_gjp2(p):
        return hashlib.sha1((p + "mI29fmAnxgTs").encode()).hexdigest()

    if gjp2 != gen_gjp2(acc["password"]):
        cursor.close()
        db.close()
        return "-11"

    # -------------------------
    # SAFE CONVERSIONS
    # -------------------------
    def i(x):
        try:
            return int(x)
        except:
            return 0

    stars = i(stars)
    moons = i(moons)
    demons = i(demons)
    diamonds = i(diamonds)
    icon = i(icon)
    icon_type = i(icon_type)
    coins = i(coins)
    user_coins = i(user_coins)

    # -------------------------
    # UPDATE USER
    # -------------------------
    cursor.execute("""
        UPDATE users SET
            stars=%s,
            moons=%s,
            demons=%s,
            diamonds=%s,

            icon=%s,
            iconType=%s,

            coins=%s,
            userCoins=%s,

            accIcon=%s,
            accShip=%s,
            accBall=%s,
            accBird=%s,
            accDart=%s,
            accRobot=%s,
            accGlow=%s,
            accSpider=%s,
            accExplosion=%s,
            accSwing=%s,
            accJetpack=%s

        WHERE userID=%s
    """, (
        stars, moons, demons, diamonds,
        icon, icon_type,
        coins, user_coins,

        acc_icon, acc_ship, acc_ball, acc_bird,
        acc_dart, acc_robot, acc_glow, acc_spider,
        acc_explosion, acc_swing, acc_jetpack,

        account_id
    ))

    db.commit()
    cursor.close()
    db.close()

    # -------------------------
    # GD SUCCESS RESPONSE
    # -------------------------
    return str(account_id)

@app.route('/accounts/registerGJAccount.php', methods=['POST'])
def register():
    username = request.form.get('userName')
    password = request.form.get('password')
    email = request.form.get('email')

    # basic checks
    if not username or len(username) > 20:
        return "-4"

    if not password or len(password) < 3:
        return "-5"

    if not email or "@" not in email:
        return "-6"

    db = get_db()
    cursor = db.cursor()

    # username taken
    cursor.execute("SELECT accountID FROM accounts WHERE userName=%s", (username,))
    if cursor.fetchone():
        return "-2"

    # email taken
    cursor.execute("SELECT accountID FROM accounts WHERE email=%s", (email,))
   
