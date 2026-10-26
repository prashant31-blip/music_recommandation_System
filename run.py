import os
import sys

from backend.database import DB_PATH, init_db
from backend.seed_data import seed_database

def ensure_setup():
    init_db()
    # Check if tracks table is populated
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM tracks")
    count = c.fetchone()[0]
    conn.close()

    if count == 0:
        print("[!] No tracks found in SQLite. Running automated seed...")
        seed_database(limit_tracks=40000)
    else:
        print(f"[OK] SQLite database ready with {count} indexed tracks.")

if __name__ == '__main__':
    # Ensure stdout handles utf-8 if possible
    reconfigure = getattr(sys.stdout, 'reconfigure', None)
    if callable(reconfigure):
        reconfigure(encoding='utf-8', errors='replace')
    print("=" * 60)
    print("   VIBENEST AI - MUSIC RECOMMENDATION SYSTEM")
    print("=" * 60)
    
    ensure_setup()

    from backend.app import app
    port = int(os.environ.get('PORT', 5000))
    url = f"http://127.0.0.1:{port}"
    print(f"\n[+] Server running at: {url}")
    print("[*] Press Ctrl+C to stop the server\n")

    app.run(host='127.0.0.1', port=port, debug=False)
