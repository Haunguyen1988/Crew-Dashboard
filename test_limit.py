import os
import sys

# Try to load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from supabase import create_client
except ImportError:
    print("Error: 'supabase' package not found. Run: pip install supabase")
    sys.exit(1)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not set in .env")
    sys.exit(1)

print(f"Testing Supabase Limit on: {url}...")
client = create_client(url, key)

try:
    # 1. Total Count
    print("1. Checking total count (HEAD)...")
    res = client.table('flights').select("*", count='exact', head=True).execute()
    total = res.count
    print(f"   Total rows in DB: {total}")

    # 2. Fetch with limit=2000
    print("\n2. Attempting to fetch 2000 rows...")
    res = client.table('flights').select('*').limit(2000).execute()
    fetched = len(res.data)
    print(f"   Fetched: {fetched} rows")
    
    if fetched == 1000 and total > 1000:
        print("\n⚠️  DETECTED HARD LIMIT: 1000 per request.")
        print("   This is a server-side setting in Supabase.")
        print("   FIX: Go to Supabase Dashboard -> Settings -> API -> Global Limits -> Max rows -> Change to 10000.")
    elif fetched > 1000:
        print("\n✅ Success! The API allows fetching > 1000 rows.")
    else:
        print("\nℹ️  Fetched < 1000, probably not enough data to test limit.")

except Exception as e:
    print(f"❌ Error: {str(e)}")
