import json

with open("schema_dump.json") as f:
    data = json.load(f)

print("Categories exists:", "categories" in data["columns"])
if "categories" in data["columns"]:
    print("Categories columns:")
    for col in data["columns"]["categories"]:
        print(f"  {col['name']} (default: {col['default']}, nullable: {col['nullable']})")

print("\nSuppliers exists:", "suppliers" in data["columns"])
if "suppliers" in data["columns"]:
    print("Suppliers columns:")
    for col in data["columns"]["suppliers"]:
        print(f"  {col['name']} (default: {col['default']}, nullable: {col['nullable']})")
