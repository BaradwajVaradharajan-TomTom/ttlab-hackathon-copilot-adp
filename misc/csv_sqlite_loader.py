import sqlite3
import csv
import os
import sys

DB_FILE = "database.db"


def main(csv_file, table_name):
    # Check if the CSV file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found.")
        exit(1)

    # Connect to SQLite database (or create a new one)
    connection = sqlite3.connect(DB_FILE)
    cursor = connection.cursor()

    # Read CSV file and determine headers
    with open(csv_file, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        headers = next(reader)  # First row is assumed to be the headers

        # Create table
        columns = ", ".join(
            [f'"{h}" TEXT' for h in headers]
        )  # Assuming all columns as TEXT for simplicity
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(f"CREATE TABLE {table_name} ({columns})")

        # Insert data into the table
        for row in reader:
            placeholders = ", ".join(["?" for _ in row])
            cursor.execute(f"INSERT INTO {table_name} VALUES ({placeholders})", row)

    # Commit and close connection
    connection.commit()
    connection.close()

    print(
        f"Data from '{csv_file}' has been loaded into SQLite database '{DB_FILE}' in table '{table_name}'."
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
