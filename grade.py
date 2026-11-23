import unittest
import requests
import random
import string
import psycopg2

BASE_URL = "http://127.0.0.1:5000"

DB_CONFIG = {
    "host": "localhost",
    "database": "postgres",
    "user": "user",
    "password": "password"
}


def reset_database():

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        TRUNCATE TABLE
            ininventory,
            history,
            item,
            character
        RESTART IDENTITY CASCADE;
    """)

    conn.commit()

    cur.close()
    conn.close()


def random_name(length=10):
    return ''.join(
        random.choices(string.ascii_letters, k=length)
    )


class GradeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        reset_database()

    def test_root(self):

        response = requests.get(f"{BASE_URL}/")

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.text.strip(), "")

    def test1_character_crud(self):

        random_char = random_name()

        response = requests.get(
            f"{BASE_URL}/characters"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = requests.get(
            f"{BASE_URL}/character",
            params={"characterid": 12345}
        )

        self.assertEqual(response.status_code, 404)

        response = requests.delete(
            f"{BASE_URL}/character",
            params={"characterid": 12345}
        )

        self.assertEqual(response.status_code, 404)

        response = requests.post(
            f"{BASE_URL}/character",
            data={
                "firstname": random_char,
                "lastname": "test",
                "home_server": "testserver",
                "max_inventory": 10
            }
        )

        self.assertEqual(response.status_code, 201)

        characterid = response.json()["characterid"]

        response = requests.get(
            f"{BASE_URL}/character",
            params={"characterid": characterid}
        )

        self.assertEqual(response.status_code, 200)

        character = response.json()

        self.assertEqual(character["firstname"], random_char)
        self.assertEqual(character["lastname"], "test")
        self.assertEqual(character["home_server"], "testserver")
        self.assertEqual(character["max_inventory"], 10)

        response = requests.get(
            f"{BASE_URL}/characters"
        )

        characters = response.json()

        matches = [
            c for c in characters
            if c["characterid"] == characterid
        ]

        self.assertEqual(len(matches), 1)

        response = requests.delete(
            f"{BASE_URL}/character",
            params={"characterid": characterid}
        )

        self.assertEqual(response.status_code, 200)

        response = requests.get(
            f"{BASE_URL}/character",
            params={"characterid": characterid}
        )

        self.assertEqual(response.status_code, 404)

    def test2_item_crud(self):

        random_item = random_name()

        response = requests.get(
            f"{BASE_URL}/items"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = requests.get(
            f"{BASE_URL}/item",
            params={"itemid": 12345}
        )

        self.assertEqual(response.status_code, 404)

        response = requests.delete(
            f"{BASE_URL}/item",
            params={"itemid": 12345}
        )

        self.assertEqual(response.status_code, 404)

        response = requests.post(
            f"{BASE_URL}/item",
            data={
                "name": random_item,
                "type": "Sword",
                "rarity": "Common"
            }
        )

        self.assertEqual(response.status_code, 201)

        itemid = response.json()["itemid"]

        response = requests.get(
            f"{BASE_URL}/item",
            params={"itemid": itemid}
        )

        self.assertEqual(response.status_code, 200)

        item = response.json()

        self.assertEqual(item["name"], random_item)
        self.assertEqual(item["type"], "Sword")
        self.assertEqual(item["rarity"], "Common")

        response = requests.get(
            f"{BASE_URL}/items"
        )

        items = response.json()

        matches = [
            i for i in items
            if i["itemid"] == itemid
        ]

        self.assertEqual(len(matches), 1)

        response = requests.delete(
            f"{BASE_URL}/item",
            params={"itemid": itemid}
        )

        self.assertEqual(response.status_code, 200)

        response = requests.get(
            f"{BASE_URL}/item",
            params={"itemid": itemid}
        )

        self.assertEqual(response.status_code, 404)

    def test3_inventory_workflow(self):

        response = requests.post(
            f"{BASE_URL}/character",
            data={
                "firstname": random_name(),
                "lastname": "test",
                "home_server": "testserver",
                "max_inventory": 10
            }
        )

        characterid = response.json()["characterid"]

        response = requests.post(
            f"{BASE_URL}/item",
            data={
                "name": random_name(),
                "type": "Sword",
                "rarity": "Common"
            }
        )

        itemid = response.json()["itemid"]

        response = requests.get(
            f"{BASE_URL}/inventory",
            params={"characterid": characterid}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = requests.post(
            f"{BASE_URL}/item_acquired",
            data={
                "characterid": characterid,
                "itemid": itemid
            }
        )

        self.assertEqual(response.status_code, 200)

        response = requests.get(
            f"{BASE_URL}/inventory",
            params={"characterid": characterid}
        )

        inventory = response.json()

        self.assertEqual(len(inventory), 1)

        acquired = inventory[0]["time_acquired"]

        response = requests.get(
            f"{BASE_URL}/history",
            params={"characterid": characterid}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = requests.post(
            f"{BASE_URL}/item_dropped",
            data={
                "characterid": characterid,
                "itemid": itemid
            }
        )

        self.assertEqual(response.status_code, 200)

        response = requests.get(
            f"{BASE_URL}/inventory",
            params={"characterid": characterid}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

        response = requests.get(
            f"{BASE_URL}/history",
            params={"characterid": characterid}
        )

        history = response.json()

        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["itemid"], itemid)
        self.assertEqual(history[0]["time_acquired"], acquired)

        response = requests.get(
            f"{BASE_URL}/inventory",
            params={"characterid": 12345}
        )

        self.assertEqual(response.status_code, 404)

        response = requests.get(
            f"{BASE_URL}/history",
            params={"characterid": 12345}
        )

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()