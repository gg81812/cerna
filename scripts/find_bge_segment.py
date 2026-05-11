"""Identify which segment folder belongs to cerner_docs_bge."""
import sqlite3

con = sqlite3.connect("chroma_store/chroma.sqlite3")
cur = con.cursor()

# Get all collections
cur.execute("SELECT id, name FROM collections")
collections = {cid: cname for cid, cname in cur.fetchall()}
print("Collections:")
for cid, cname in collections.items():
    print(f"  {cname}: {cid}")

# Inspect segments table schema
cur.execute("PRAGMA table_info(segments)")
print("\nsegments table schema:")
for row in cur.fetchall():
    print(f"  {row}")

# Get all segments
cur.execute("SELECT * FROM segments")
print("\nAll segments:")
for row in cur.fetchall():
    print(f"  {row}")

con.close()
