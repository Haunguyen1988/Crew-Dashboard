"""
ETL Scheduler for AIMS Data Integration
Chạy job ETL định kỳ để sync dữ liệu từ AIMS vào Supabase
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ETLScheduler')

# Try to import APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Run: pip install APScheduler")


class ETLScheduler:
    """
    ETL Scheduler for AIMS Data
    
    - Chạy job định kỳ mỗi 15 phút
    - Tối ưu: chỉ fetch dữ liệu ±30 ngày
    - Sync data vào Supabase staging tables
    """
    
    def __init__(self, interval_minutes: int = 15):
        """
        Khởi tạo ETL Scheduler
        
        Args:
            interval_minutes: Khoảng thời gian giữa mỗi lần chạy (default: 15 phút)
        """
        self.interval_minutes = interval_minutes
        self.scheduler = None
        self.is_running = False
        self.last_run = None
        self.last_status = None
        
    def _get_aims_client(self):
        """Lazy import AIMS client to avoid circular imports"""
        from aims_soap_client import get_aims_client, is_aims_available
        if not is_aims_available():
            logger.warning("AIMS not available or not enabled")
            return None
        return get_aims_client()
    
    def run_etl_job(self) -> dict:
        """
        Chạy ETL job một lần
        
        Workflow:
        1. Lấy dữ liệu từ AIMS (±30 ngày)
        2. Transform và mapping
        3. Sync vào Supabase staging tables
        
        Returns:
            dict: Job result status
        """
        start_time = datetime.now()
        result = {
            'success': False,
            'start_time': start_time.isoformat(),
            'end_time': None,
            'duration_seconds': 0,
            'flights_synced': 0,
            'crew_synced': 0,
            'errors': []
        }
        
        try:
            logger.info("=" * 50)
            logger.info("AIMS ETL Job Started")
            logger.info("=" * 50)
            
            # Get AIMS client
            aims_client = self._get_aims_client()
            if not aims_client:
                result['errors'].append("AIMS client not available")
                return result
            
            # Get optimized date range (±30 days)
            from_date, to_date = aims_client.get_optimized_date_range()
            logger.info(f"Fetching data from {from_date.date()} to {to_date.date()}")
            
            # 1. Fetch flight details
            logger.info("Fetching flight details...")
            flight_result = aims_client.get_flight_details(from_date, to_date)
            
            if flight_result['success']:
                flights = flight_result['flights']
                result['flights_synced'] = len(flights)
                logger.info(f"Fetched {len(flights)} flights")
                
                # Sync to Supabase
                self._sync_flights_to_supabase(flights)
            else:
                result['errors'].append(f"Flight fetch error: {flight_result.get('error')}")
            
            # 2. Fetch crew list
            logger.info("Fetching crew list...")
            crew_result = aims_client.get_crew_list(from_date, to_date)
            
            if crew_result['success']:
                crew_list = crew_result['crew_list']
                result['crew_synced'] = len(crew_list)
                logger.info(f"Fetched {len(crew_list)} crew members")
                
                # Sync to Supabase
                self._sync_crew_to_supabase(crew_list)
            else:
                result['errors'].append(f"Crew fetch error: {crew_result.get('error')}")
            
            # Mark success if no critical errors
            result['success'] = len(result['errors']) == 0
            
        except Exception as e:
            logger.error(f"ETL Job failed: {e}")
            result['errors'].append(str(e))
        finally:
            end_time = datetime.now()
            result['end_time'] = end_time.isoformat()
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            
            self.last_run = start_time
            self.last_status = result
            
            logger.info(f"ETL Job completed in {result['duration_seconds']:.2f}s")
            logger.info(f"Flights: {result['flights_synced']}, Crew: {result['crew_synced']}")
            
        return result
    
    def _sync_flights_to_supabase(self, flights: list):
        """Sync flight data to Supabase fact_actuals table"""
        if not flights:
            return
            
        try:
            # Import supabase client
            from supabase_client import get_client, is_connected
            
            if not is_connected():
                logger.warning("Supabase not connected, skipping sync")
                return
            
            client = get_client()
            
            # Transform for Supabase schema
            records = []
            for flight in flights:
                record = {
                    'flight_date': flight.get('flight_date', ''),
                    'flight_no': flight.get('flight_no', ''),
                    'ac_reg': flight.get('ac_reg', ''),
                    'departure': flight.get('departure', ''),
                    'arrival': flight.get('arrival', ''),
                    'std': flight.get('std', ''),
                    'sta': flight.get('sta', ''),
                    'atd': flight.get('atd', ''),
                    'ata': flight.get('ata', ''),
                    'block_minutes': flight.get('block_minutes', 0),
                    'status': flight.get('status', ''),
                    'source': 'AIMS_API',
                    'synced_at': datetime.now().isoformat()
                }
                records.append(record)
            
            # Upsert to Supabase fact_actuals table
            if records:
                try:
                    client.table('fact_actuals').upsert(
                        records, 
                        on_conflict='flight_date,flight_no'
                    ).execute()
                    logger.info(f"Synced {len(records)} flight records to Supabase")
                except Exception as upsert_error:
                    logger.warning(f"Upsert failed, trying insert: {upsert_error}")
                    # Fallback to insert if table doesn't support upsert
                    for batch_start in range(0, len(records), 100):
                        batch = records[batch_start:batch_start+100]
                        client.table('fact_actuals').insert(batch).execute()
            
        except Exception as e:
            logger.error(f"Error syncing flights to Supabase: {e}")
    
    def _sync_crew_to_supabase(self, crew_list: list):
        """Sync crew data to Supabase dim_crew table"""
        if not crew_list:
            return
            
        try:
            from supabase_client import get_client, is_connected
            
            if not is_connected():
                logger.warning("Supabase not connected, skipping sync")
                return
            
            client = get_client()
            
            # Transform for Supabase schema
            records = []
            for crew in crew_list:
                record = {
                    'crew_id': crew.get('crew_id', ''),
                    'name': crew.get('name', ''),
                    'short_name': crew.get('short_name', ''),
                    'qualifications': crew.get('qualifications', ''),
                    'email': crew.get('email', ''),
                    'location': crew.get('location', ''),
                    'source': 'AIMS_API',
                    'synced_at': datetime.now().isoformat()
                }
                records.append(record)
            
            # Upsert to Supabase dim_crew table
            if records:
                try:
                    client.table('dim_crew').upsert(
                        records, 
                        on_conflict='crew_id'
                    ).execute()
                    logger.info(f"Synced {len(records)} crew records to Supabase")
                except Exception as upsert_error:
                    logger.warning(f"Upsert failed, trying insert: {upsert_error}")
                    # Fallback to insert if table doesn't support upsert
                    for batch_start in range(0, len(records), 100):
                        batch = records[batch_start:batch_start+100]
                        client.table('dim_crew').insert(batch).execute()
            
        except Exception as e:
            logger.error(f"Error syncing crew to Supabase: {e}")
    
    def start(self):
        """Start the scheduler with background jobs"""
        if not SCHEDULER_AVAILABLE:
            logger.error("APScheduler not available. Cannot start scheduler.")
            return False
        
        if self.is_running:
            logger.warning("Scheduler already running")
            return True
        
        self.scheduler = BackgroundScheduler()
        
        # Add job to run every interval_minutes
        self.scheduler.add_job(
            self.run_etl_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id='aims_etl_job',
            name='AIMS ETL Sync Job',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info(f"ETL Scheduler started. Running every {self.interval_minutes} minutes.")
        
        return True
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("ETL Scheduler stopped")
    
    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            'is_running': self.is_running,
            'interval_minutes': self.interval_minutes,
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'last_status': self.last_status
        }


# Singleton instance
_scheduler = None


def get_scheduler() -> ETLScheduler:
    """Get or create ETL scheduler singleton"""
    global _scheduler
    if _scheduler is None:
        _scheduler = ETLScheduler()
    return _scheduler


# CLI for testing
if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("AIMS ETL Scheduler")
    print("=" * 60)
    
    scheduler = get_scheduler()
    
    if '--run-once' in sys.argv:
        print("\nRunning ETL job once...")
        result = scheduler.run_etl_job()
        
        print(f"\nJob completed:")
        print(f"  Success: {result['success']}")
        print(f"  Duration: {result['duration_seconds']:.2f}s")
        print(f"  Flights synced: {result['flights_synced']}")
        print(f"  Crew synced: {result['crew_synced']}")
        
        if result['errors']:
            print(f"  Errors:")
            for err in result['errors']:
                print(f"    - {err}")
        
        sys.exit(0 if result['success'] else 1)
    
    elif '--start' in sys.argv:
        print("\nStarting scheduler...")
        scheduler.start()
        
        print("Scheduler running. Press Ctrl+C to stop.")
        try:
            # Keep main thread alive
            import time
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            scheduler.stop()
            print("\nScheduler stopped.")
    
    else:
        print("\nUsage:")
        print("  python etl_scheduler.py --run-once  # Run ETL job once")
        print("  python etl_scheduler.py --start     # Start background scheduler")
