from supabase_client import get_flights, init_supabase

print("Initializing Supabase...")
if init_supabase():
    print("Supabase initialized.")
    
    print("Fetching flights with pagination...")
    flights = get_flights()
    count = len(flights)
    
    print(f"Total flights fetched: {count}")
    
    if count > 1000:
        print("✅ SUCCESS: Pagination is working! Fetched > 1000 rows.")
    else:
        print("❌ FAILURE: Still capped at 1000 rows or DB is empty.")
else:
    print("❌ Failed to initialize Supabase.")
