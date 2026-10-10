import csv
import requests
from pathlib import Path

URL = "https://data.transportation.gov/resource/8ect-6jqj.json"

output = Path("data/peachtree_full.csv")
output.parent.mkdir(parents=True, exist_ok=True)

limit = 50000
offset = 0
total = 0
writer = None

with output.open("w", newline="", encoding="utf-8") as f:
    while True:
        params = {
            "$where": "location='peachtree'",
            "$limit": limit,
            "$offset": offset,
            "$order": "global_time, vehicle_id"
        }

        print(f"Descargando offset {offset:,}...")
        response = requests.get(URL, params=params, timeout=120)
        response.raise_for_status()

        rows = response.json()

        if not rows:
            break

        if writer is None:
            fieldnames = list(rows[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

        writer.writerows(rows)

        total += len(rows)
        offset += len(rows)

        print(f"Acumulado: {total:,}")

print(f"FINAL: {total:,} filas")
print(f"Archivo: {output}")
