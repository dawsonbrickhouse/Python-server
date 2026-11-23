import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from datetime import datetime
from contextlib import contextmanager

app = Flask(__name__)

DB_CONFIG = {
    "host": "localhost",
    "dbname": "postgres",
    "user": "user",
    "password": "password",
    "cursor_factory": RealDictCursor,
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def database():
    conn = get_conn()
    try:
        db = conn.cursor()
        yield db
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with database() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS character (
                characterid SERIAL PRIMARY KEY,
                firstname TEXT NOT NULL,
                lastname TEXT NOT NULL,
                home_server TEXT NOT NULL,
                max_inventory INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item (
                itemid SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                rarity TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ininventory (
                characterid INTEGER NOT NULL
                    REFERENCES character (characterid) ON DELETE CASCADE,
                itemid INTEGER NOT NULL
                    REFERENCES item (itemid) ON DELETE CASCADE,
                time_acquired TIMESTAMP NOT NULL,
                PRIMARY KEY (characterid, itemid)
            );

            CREATE TABLE IF NOT EXISTS history (
                characterid INTEGER NOT NULL
                    REFERENCES character (characterid) ON DELETE CASCADE,
                itemid INTEGER NOT NULL
                    REFERENCES item (itemid) ON DELETE CASCADE,
                time_acquired TIMESTAMP NOT NULL,
                time_dropped TIMESTAMP NOT NULL
            );
            """
        )


def parse_int(value):
    if value is None:
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def required_text(name):
    value = request.values.get(name)
    if value is None:
        return None
    value = value.strip()
    if value == "":
        return None
    return value


def format_time(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    return value


def invalid():
    return jsonify({"error": "invalid input"}), 400


def not_found():
    return jsonify({"error": "not found"}), 404


@app.get("/")
def root():
    return "csci3700", 200


@app.get("/characters")
def list_characters():
    with database() as db:
        db.execute(
            """
            SELECT characterid, firstname, lastname, home_server, max_inventory
            FROM character
            ORDER BY characterid
            """
        )
        rows = [dict(row) for row in db.fetchall()]
    return jsonify(rows), 200


@app.get("/character")
def get_character():
    characterid = parse_int(request.values.get("characterid"))
    if characterid is None:
        return invalid()
    with database() as db:
        db.execute(
            """
            SELECT characterid, firstname, lastname, home_server, max_inventory
            FROM character
            WHERE characterid = %s
            """,
            (characterid,),
        )
        row = db.fetchone()
    if row is None:
        return not_found()
    return jsonify(dict(row)), 200


@app.post("/character")
def create_character():
    firstname = required_text("firstname")
    lastname = required_text("lastname")
    home_server = required_text("home_server")
    max_inventory = parse_int(request.values.get("max_inventory"))
    if (
        firstname is None
        or lastname is None
        or home_server is None
        or max_inventory is None
        or max_inventory < 0
        or max_inventory > 2147483647
    ):
        return invalid()
    with database() as db:
        db.execute(
            """
            INSERT INTO character (firstname, lastname, home_server, max_inventory)
            VALUES (%s, %s, %s, %s)
            RETURNING characterid
            """,
            (firstname, lastname, home_server, max_inventory),
        )
        characterid = db.fetchone()["characterid"]
    return jsonify({"characterid": characterid}), 201


@app.delete("/character")
def delete_character():
    characterid = parse_int(request.values.get("characterid"))
    if characterid is None:
        return invalid()
    with database() as db:
        db.execute(
            "DELETE FROM character WHERE characterid = %s",
            (characterid,),
        )
        deleted = db.rowcount
    if deleted == 0:
        return not_found()
    return jsonify({"success": True}), 200


@app.get("/items")
def list_items():
    with database() as db:
        db.execute(
            """
            SELECT itemid, name, type, rarity
            FROM item
            ORDER BY itemid
            """
        )
        rows = [dict(row) for row in db.fetchall()]
    return jsonify(rows), 200


@app.get("/item")
def get_item():
    itemid = parse_int(request.values.get("itemid"))
    if itemid is None:
        return invalid()
    with database() as db:
        db.execute(
            """
            SELECT itemid, name, type, rarity
            FROM item
            WHERE itemid = %s
            """,
            (itemid,),
        )
        row = db.fetchone()
    if row is None:
        return not_found()
    return jsonify(dict(row)), 200


@app.post("/item")
def create_item():
    name = required_text("name")
    item_type = required_text("type")
    rarity = required_text("rarity")
    if name is None or item_type is None or rarity is None:
        return invalid()
    with database() as db:
        db.execute(
            """
            INSERT INTO item (name, type, rarity)
            VALUES (%s, %s, %s)
            RETURNING itemid
            """,
            (name, item_type, rarity),
        )
        itemid = db.fetchone()["itemid"]
    return jsonify({"itemid": itemid}), 201


@app.delete("/item")
def delete_item():
    itemid = parse_int(request.values.get("itemid"))
    if itemid is None:
        return invalid()
    with database() as db:
        db.execute("DELETE FROM item WHERE itemid = %s", (itemid,))
        deleted = db.rowcount
    if deleted == 0:
        return not_found()
    return jsonify({"success": True}), 200


def character_exists(db, characterid):
    db.execute(
        "SELECT 1 FROM character WHERE characterid = %s",
        (characterid,),
    )
    return db.fetchone() is not None


@app.get("/inventory")
def get_inventory():
    characterid = parse_int(request.values.get("characterid"))
    if characterid is None:
        return invalid()
    with database() as db:
        if not character_exists(db, characterid):
            return not_found()
        db.execute(
            """
            SELECT characterid, itemid, time_acquired
            FROM ininventory
            WHERE characterid = %s
            ORDER BY time_acquired, itemid
            """,
            (characterid,),
        )
        rows = []
        for row in db.fetchall():
            entry = dict(row)
            entry["time_acquired"] = format_time(entry["time_acquired"])
            rows.append(entry)
    return jsonify(rows), 200


@app.get("/history")
def get_history():
    characterid = parse_int(request.values.get("characterid"))
    if characterid is None:
        return invalid()
    with database() as db:
        if not character_exists(db, characterid):
            return not_found()
        db.execute(
            """
            SELECT characterid, itemid, time_acquired, time_dropped
            FROM history
            WHERE characterid = %s
            ORDER BY time_dropped, time_acquired, itemid
            """,
            (characterid,),
        )
        rows = []
        for row in db.fetchall():
            entry = dict(row)
            entry["time_acquired"] = format_time(entry["time_acquired"])
            entry["time_dropped"] = format_time(entry["time_dropped"])
            rows.append(entry)
    return jsonify(rows), 200


@app.post("/item_acquired")
def item_acquired():
    characterid = parse_int(request.values.get("characterid"))
    itemid = parse_int(request.values.get("itemid"))
    if characterid is None or itemid is None:
        return invalid()
    acquired_at = datetime.now().replace(microsecond=0)
    with database() as db:
        db.execute(
            """
            SELECT max_inventory
            FROM character
            WHERE characterid = %s
            """,
            (characterid,),
        )
        character = db.fetchone()
        if character is None:
            return invalid()
        db.execute("SELECT 1 FROM item WHERE itemid = %s", (itemid,))
        if db.fetchone() is None:
            return invalid()
        db.execute(
            """
            SELECT 1
            FROM ininventory
            WHERE characterid = %s AND itemid = %s
            """,
            (characterid, itemid),
        )
        if db.fetchone() is not None:
            return invalid()
        db.execute(
            "SELECT COUNT(*) AS count FROM ininventory WHERE characterid = %s",
            (characterid,),
        )
        if db.fetchone()["count"] >= character["max_inventory"]:
            return invalid()
        db.execute(
            """
            INSERT INTO ininventory (characterid, itemid, time_acquired)
            VALUES (%s, %s, %s)
            """,
            (characterid, itemid, acquired_at),
        )
    return jsonify({"success": True}), 200


@app.post("/item_dropped")
def item_dropped():
    characterid = parse_int(request.values.get("characterid"))
    itemid = parse_int(request.values.get("itemid"))
    if characterid is None or itemid is None:
        return invalid()
    dropped_at = datetime.now().replace(microsecond=0)
    with database() as db:
        db.execute(
            """
            SELECT time_acquired
            FROM ininventory
            WHERE characterid = %s AND itemid = %s
            """,
            (characterid, itemid),
        )
        held = db.fetchone()
        if held is None:
            return invalid()
        db.execute(
            """
            DELETE FROM ininventory
            WHERE characterid = %s AND itemid = %s
            """,
            (characterid, itemid),
        )
        db.execute(
            """
            INSERT INTO history (
                characterid, itemid, time_acquired, time_dropped
            )
            VALUES (%s, %s, %s, %s)
            """,
            (characterid, itemid, held["time_acquired"], dropped_at),
        )
    return jsonify({"success": True}), 200


init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
