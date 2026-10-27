
import csv
import sqlite3
from collections import Counter
from pathlib import Path

# Define file paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATABASE = BASE_DIR / "shipment_database.db"


def read_csv(filename):
    """Read a CSV file and return its rows."""
    file_path = DATA_DIR / filename

    with open(file_path, newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def get_product_id(cursor, product_name):
    """Get an existing product ID or create a new product."""

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
    """Insert a shipment record into the database."""

    product_id = get_product_id(cursor, product)

    cursor.execute(
        """
        INSERT INTO shipment
            (product_id, quantity, origin, destination)
        VALUES (?, ?, ?, ?)
        """,
        (product_id, quantity, origin, destination)
    )


def prepare_shipping_data():
    """Read and combine the three shipping CSV files."""

    shipping_0 = read_csv("shipping_data_0.csv")
    shipping_1 = read_csv("shipping_data_1.csv")
    shipping_2 = read_csv("shipping_data_2.csv")

    # Store origin and destination for each shipment
    shipment_locations = {}

    for row in shipping_2:
        shipment_id = row["shipment_identifier"]

        shipment_locations[shipment_id] = (
            row["origin_warehouse"],
            row["destination_store"]
        )

    # Count how many times each product appears in a shipment
    product_counts = Counter()

    for row in shipping_1:
        shipment_id = row["shipment_identifier"]
        product_name = row["product"]

        product_counts[(shipment_id, product_name)] += 1

    return shipping_0, shipment_locations, product_counts


def populate_database():
    """Insert the processed shipping data into SQLite."""

    shipping_0, shipment_locations, product_counts = prepare_shipping_data()

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()

        # Avoid inserting the same dataset twice
        cursor.execute("SELECT COUNT(*) FROM shipment")

        if cursor.fetchone()[0] > 0:
            print("Shipment data already exists.")
            print("Skipping insertion to avoid duplicates.")
            return

        # Insert shipments from the first CSV file
        for row in shipping_0:
            insert_shipment(
                cursor,
                row["product"],
                int(row["product_quantity"]),
                row["origin_warehouse"],
                row["destination_store"]
            )

        # Combine product quantities with shipment locations
        for (shipment_id, product), quantity in product_counts.items():

            origin, destination = shipment_locations[shipment_id]

            insert_shipment(
                cursor,
                product,
                quantity,
                origin,
                destination
            )

        connection.commit()

        print("Database populated successfully!")


def verify_database():
    """Display the total number of products and shipments."""

    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM product")
        product_total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM shipment")
        shipment_total = cursor.fetchone()[0]

        print("\nDatabase Summary")
        print("-------------------------")
        print(f"Total products: {product_total}")
        print(f"Total shipment records: {shipment_total}")


def main():
    """Run the data munging process."""

    try:
        populate_database()
        verify_database()

    except FileNotFoundError as error:
        print(f"File not found: {error}")

    except KeyError as error:
        print(f"Missing CSV field or shipment ID: {error}")

    except sqlite3.Error as error:
        print(f"Database error: {error}")


if __name__ == "__main__":
    main()
