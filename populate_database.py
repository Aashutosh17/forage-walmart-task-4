
import csv
import sqlite3
from collections import Counter
from pathlib import Path

# Files are stored in the same folder as this script
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE = BASE_DIR / "shipment_database.db"


def read_csv(filename):
    """Read a CSV file and return its rows."""
    with open(DATA_DIR / filename, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def get_product_id(cursor, product_name):
    """Find a product ID, or create the product if needed."""
    cursor.execute(
        "INSERT OR IGNORE INTO product (name) VALUES (?)",
        (product_name,)
    )

    cursor.execute(
        "SELECT id FROM product WHERE name = ?",
        (product_name,)
    )

    return cursor.fetchone()[0]


def insert_shipment(cursor, product, quantity, origin, destination):
    """Insert one shipment record into the database."""
    product_id = get_product_id(cursor, product)

    cursor.execute(
        """
        INSERT INTO shipment
            (product_id, quantity, origin, destination)
        VALUES (?, ?, ?, ?)
        """,
        (product_id, quantity, origin, destination)
    )


def main():
    # Step 1: Read all three CSV files
    shipping_0 = read_csv("shipping_data_0.csv")
    shipping_1 = read_csv("shipping_data_1.csv")
    shipping_2 = read_csv("shipping_data_2.csv")

    # Step 2: Create a lookup for shipment locations
    shipment_locations = {}

    for row in shipping_2:
        shipment_locations[row["shipment_identifier"]] = (
            row["origin_warehouse"],
            row["destination_store"]
        )

    # Step 3: Count products in each shipment
    product_counts = Counter()

    for row in shipping_1:
        key = (row["shipment_identifier"], row["product"])
        product_counts[key] += 1

    # Step 4: Connect to the SQLite database
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()

        # Insert records from CSV 0
        for row in shipping_0:
            insert_shipment(
                cursor,
                row["product"],
                int(row["product_quantity"]),
                row["origin_warehouse"],
                row["destination_store"]
            )

        # Insert combined records from CSV 1 and CSV 2
        for (shipment_id, product), quantity in product_counts.items():
            origin, destination = shipment_locations[shipment_id]

            insert_shipment(
                cursor,
                product,
                quantity,
                origin,
                destination
            )

        # Step 5: Check the database
        cursor.execute("SELECT COUNT(*) FROM product")
        product_total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM shipment")
        shipment_total = cursor.fetchone()[0]

        print("Database populated successfully!")
        print("Total products:", product_total)
        print("Total shipment records:", shipment_total)


if __name__ == "__main__":
    main()
