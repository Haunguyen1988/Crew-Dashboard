"""
AIMS SOAP Client Module
Kết nối AIMS Web Service (SOAP 1.1) để lấy dữ liệu phi hành đoàn
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from functools import wraps
import time

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aims_errors.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AIMSSoapClient')

# Try to import zeep, provide fallback message if not installed
try:
    from zeep import Client
    from zeep.transports import Transport
    from zeep.exceptions import Fault, TransportError
    from requests import Session
    from requests.exceptions import RequestException
    ZEEP_AVAILABLE = True
except ImportError:
    ZEEP_AVAILABLE = False
    logger.warning("zeep not installed. Run: pip install zeep")

try:
    import pytz
    PYTZ_AVAILABLE = True
except ImportError:
    PYTZ_AVAILABLE = False
    logger.warning("pytz not installed. Run: pip install pytz")


def retry_on_failure(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
            logger.error(f"All {max_retries} attempts failed for {func.__name__}")
            raise last_exception
        return wrapper
    return decorator


class AIMSSoapClient:
    """
    AIMS Web Service SOAP Client
    
    Kết nối với AIMS để lấy:
    - Lịch công tác phi hành đoàn (Crew Roster)
    - Chi tiết chuyến bay (Flight Details)
    - Danh sách phi hành đoàn (Crew List)
    """
    
    def __init__(
        self,
        wsdl_url: str = None,
        username: str = None,
        password: str = None,
        timeout: int = 30
    ):
        """
        Khởi tạo AIMS SOAP Client
        
        Args:
            wsdl_url: URL của WSDL endpoint
            username: Tên đăng nhập AIMS
            password: Mật khẩu AIMS
            timeout: Timeout cho requests (seconds)
        """
        # Load from environment if not provided
        self.wsdl_url = wsdl_url or os.getenv(
            'AIMS_WSDL_URL', 
            'https://vj-awstest.aims.aero/api/soap/aimswebservice?singlewsdl'
        )
        self.username = username or os.getenv('AIMS_USERNAME', '')
        self.password = password or os.getenv('AIMS_PASSWORD', '')
        self.timeout = timeout
        
        self._client = None
        self._service = None
        
        # Timezone for Vietnam
        self.gmt7 = pytz.timezone('Asia/Ho_Chi_Minh') if PYTZ_AVAILABLE else None
        self.utc = pytz.UTC if PYTZ_AVAILABLE else None
        
    def _init_client(self):
        """Initialize SOAP client lazily"""
        if not ZEEP_AVAILABLE:
            raise ImportError("zeep library not installed. Run: pip install zeep")
            
        if self._client is None:
            try:
                session = Session()
                session.verify = True  # SSL verification
                transport = Transport(session=session, timeout=self.timeout)
                
                self._client = Client(self.wsdl_url, transport=transport)
                self._service = self._client.service
                logger.info(f"AIMS SOAP Client initialized: {self.wsdl_url}")
            except Exception as e:
                logger.error(f"Failed to initialize AIMS client: {e}")
                raise
                
    def is_configured(self) -> bool:
        """Check if credentials are configured"""
        return bool(self.username and self.password)
    
    def is_enabled(self) -> bool:
        """Check if AIMS integration is enabled"""
        return os.getenv('AIMS_ENABLED', 'false').lower() == 'true'
    
    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to AIMS Web Service
        
        Returns:
            dict: Connection status and info
        """
        result = {
            'status': 'unknown',
            'message': '',
            'wsdl_url': self.wsdl_url,
            'credentials_configured': self.is_configured(),
            'operations': []
        }
        
        if not ZEEP_AVAILABLE:
            result['status'] = 'error'
            result['message'] = 'zeep library not installed'
            return result
            
        try:
            self._init_client()
            
            # List available operations
            for service in self._client.wsdl.services.values():
                for port in service.ports.values():
                    for operation in port.binding._operations.values():
                        result['operations'].append(operation.name)
            
            result['status'] = 'ok'
            result['message'] = f'Connected. Found {len(result["operations"])} operations.'
            logger.info(f"AIMS Connection test: OK - {len(result['operations'])} operations available")
            
        except Exception as e:
            result['status'] = 'error'
            result['message'] = str(e)
            logger.error(f"AIMS Connection test failed: {e}")
            
        return result
    
    def _format_date_parts(self, date: datetime) -> Dict[str, str]:
        """Format datetime to AIMS date parts (DD, MM, YYYY)"""
        return {
            'DD': date.strftime('%d'),
            'MM': date.strftime('%m'),
            'YYYY': date.strftime('%Y'),
            'YY': date.strftime('%y')
        }
    
    def convert_utc_to_gmt7(self, utc_dt: datetime) -> datetime:
        """
        Convert UTC datetime to GMT+7 (Vietnam timezone)
        
        Args:
            utc_dt: DateTime in UTC
            
        Returns:
            DateTime in GMT+7
        """
        if not PYTZ_AVAILABLE:
            # Fallback: simple offset addition
            return utc_dt + timedelta(hours=7)
            
        if utc_dt.tzinfo is None:
            utc_dt = self.utc.localize(utc_dt)
        return utc_dt.astimezone(self.gmt7)
    
    @retry_on_failure(max_retries=3)
    def get_crew_roster(
        self, 
        crew_id: int,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        Lấy lịch công tác phi hành đoàn (GetCrewSchedule)
        
        Maps to AIMS: CrewMemberRosterDetailsForPeriod
        
        Mapping:
            cCrewID → dim_crew.crew_id
            cActivityCode → fact_roster.activity_type
            dStartDate → fact_roster.start_dt
            dEndDate → fact_roster.end_dt
        
        Args:
            crew_id: Mã phi hành đoàn
            from_date: Ngày bắt đầu
            to_date: Ngày kết thúc
            
        Returns:
            dict: Crew roster data với mapping fields
        """
        self._init_client()
        
        from_parts = self._format_date_parts(from_date)
        to_parts = self._format_date_parts(to_date)
        
        try:
            response = self._service.CrewMemberRosterDetailsForPeriod(
                UN=self.username,
                PSW=self.password,
                ID=crew_id,
                FmDD=from_parts['DD'],
                FmMM=from_parts['MM'],
                FmYY=from_parts['YY'],
                ToDD=to_parts['DD'],
                ToMM=to_parts['MM'],
                ToYY=to_parts['YY']
            )
            
            # Parse response and map to our schema
            roster_items = []
            if hasattr(response, 'TAIMSCrewRostDetailList') and response.TAIMSCrewRostDetailList:
                for item in response.TAIMSCrewRostDetailList.TAIMSCrewRostItm:
                    # Map AIMS fields to our schema
                    roster_item = {
                        'crew_id': getattr(item, 'CrewId', crew_id),
                        'activity_type': getattr(item, 'Flt', 'UNKNOWN'),  # Flight number as activity
                        'start_dt': self._parse_aims_datetime(
                            getattr(item, 'Day', ''),
                            getattr(item, 'STD', '00:00')
                        ),
                        'end_dt': self._parse_aims_datetime(
                            getattr(item, 'Day', ''),
                            getattr(item, 'STA', '00:00')
                        ),
                        'departure': getattr(item, 'Dep', ''),
                        'arrival': getattr(item, 'Arr', ''),
                        'carrier': getattr(item, 'Carrier', ''),
                        'route': getattr(item, 'CROUTE', ''),
                        'crew_base': getattr(item, 'CrewBase', ''),
                        # Raw AIMS data for reference
                        '_raw': {
                            'STD': getattr(item, 'STD', ''),
                            'STA': getattr(item, 'STA', ''),
                            'ATD': getattr(item, 'ATD', ''),
                            'ATA': getattr(item, 'ATA', ''),
                        }
                    }
                    roster_items.append(roster_item)
            
            logger.info(f"Fetched {len(roster_items)} roster items for crew {crew_id}")
            
            return {
                'success': True,
                'crew_id': crew_id,
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'count': len(roster_items),
                'items': roster_items,
                'error': None
            }
            
        except Fault as e:
            logger.error(f"SOAP Fault in get_crew_roster: {e}")
            return {'success': False, 'error': str(e), 'items': []}
        except Exception as e:
            logger.error(f"Error in get_crew_roster: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def get_flight_details(
        self,
        from_date: datetime,
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        Lấy chi tiết chuyến bay thực tế (GetCrewActuals)
        
        Maps to AIMS: FlightDetailsForPeriod
        
        Mapping:
            nBlockTime → fact_actuals.block_minutes
            dActualDeparture → fact_actuals.dep_actual_dt
            cRegistration → fact_actuals.ac_reg
        
        Args:
            from_date: Ngày bắt đầu (recommend: Today - 30 days)
            to_date: Ngày kết thúc (recommend: Today + 30 days)
            
        Returns:
            dict: Flight details với actual block times
        """
        self._init_client()
        
        from_parts = self._format_date_parts(from_date)
        to_parts = self._format_date_parts(to_date)
        
        try:
            response = self._service.FlightDetailsForPeriod(
                UN=self.username,
                PSW=self.password,
                FromDD=from_parts['DD'],
                FromMMonth=from_parts['MM'],
                FromYYYY=from_parts['YYYY'],
                FromHH='00',
                FromMMin='00',
                ToDD=to_parts['DD'],
                ToMMonth=to_parts['MM'],
                ToYYYY=to_parts['YYYY'],
                ToHH='23',
                ToMMin='59'
            )
            
            flights = []
            if hasattr(response, 'FlightList') and response.FlightList:
                for flight in response.FlightList.TAIMSFlight:
                    # Calculate block time in minutes from ATD/ATA
                    block_minutes = self._calculate_block_minutes(
                        getattr(flight, 'FlightAtd', ''),
                        getattr(flight, 'FlightAta', '')
                    )
                    
                    flight_data = {
                        # Map to fact_actuals schema
                        'block_minutes': block_minutes,
                        'dep_actual_dt': self._parse_aims_datetime(
                            f"{getattr(flight, 'FlightDD', '')}/{getattr(flight, 'FlightMM', '')}/{getattr(flight, 'FlightYY', '')}",
                            getattr(flight, 'FlightAtd', '') or getattr(flight, 'FlightStd', '')
                        ),
                        'ac_reg': getattr(flight, 'FlightReg', ''),
                        
                        # Additional useful fields
                        'flight_no': f"{getattr(flight, 'FlightCarrier', '')}{getattr(flight, 'FlightNo', '')}",
                        'departure': getattr(flight, 'FlightDep', ''),
                        'arrival': getattr(flight, 'FlightArr', ''),
                        'status': getattr(flight, 'FlightStatus', ''),
                        'ac_type': getattr(flight, 'FlightAcType', ''),
                        
                        # Schedule times
                        'std': getattr(flight, 'FlightStd', ''),
                        'sta': getattr(flight, 'FlightSta', ''),
                        'atd': getattr(flight, 'FlightAtd', ''),
                        'ata': getattr(flight, 'FlightAta', ''),
                        
                        # Flight date
                        'flight_date': f"{getattr(flight, 'FlightDD', '')}/{getattr(flight, 'FlightMM', '')}/{getattr(flight, 'FlightYY', '')}"
                    }
                    flights.append(flight_data)
            
            logger.info(f"Fetched {len(flights)} flight details for period {from_date.date()} to {to_date.date()}")
            
            return {
                'success': True,
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'count': len(flights),
                'flights': flights,
                'error': None
            }
            
        except Fault as e:
            logger.error(f"SOAP Fault in get_flight_details: {e}")
            return {'success': False, 'error': str(e), 'flights': []}
        except Exception as e:
            logger.error(f"Error in get_flight_details: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def get_crew_list(
        self,
        from_date: datetime = None,
        to_date: datetime = None,
        base: str = None,
        ac_type: str = None,
        position: str = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách phi hành đoàn (Crew Master Data)
        
        Maps to AIMS: GetCrewList
        
        Args:
            from_date: Ngày bắt đầu (optional)
            to_date: Ngày kết thúc (optional)
            base: Filter theo base (e.g., 'SGN', 'HAN')
            ac_type: Filter theo loại tàu bay (e.g., 'A320')
            position: Filter theo vị trí (e.g., 'CP', 'FO')
            
        Returns:
            dict: Danh sách crew với thông tin chi tiết
        """
        self._init_client()
        
        # Default date range: today
        now = datetime.now()
        from_date = from_date or now
        to_date = to_date or now
        
        from_parts = self._format_date_parts(from_date)
        to_parts = self._format_date_parts(to_date)
        
        try:
            response = self._service.GetCrewList(
                UN=self.username,
                PSW=self.password,
                ID=0,  # 0 = all crew
                PrimaryQualify=True,
                FmDD=from_parts['DD'],
                FmMM=from_parts['MM'],
                FmYY=from_parts['YY'],
                ToDD=to_parts['DD'],
                ToMM=to_parts['MM'],
                ToYY=to_parts['YY'],
                BaseStr=base or '',
                ACStr=ac_type or '',
                PosStr=position or ''
            )
            
            crew_list = []
            if hasattr(response, 'CrewList') and response.CrewList:
                for crew in response.CrewList.TAIMSGetCrewItm:
                    crew_data = {
                        'crew_id': getattr(crew, 'Id', ''),
                        'name': getattr(crew, 'CrewName', ''),
                        'short_name': getattr(crew, 'ShortName', ''),
                        'qualifications': getattr(crew, 'Quals', ''),
                        'email': getattr(crew, 'Email', ''),
                        'location': getattr(crew, 'Location', ''),
                        'nationality': getattr(crew, 'Nationality', ''),
                        'employment_date': getattr(crew, 'EmploymentDate', ''),
                        'contact_cell': getattr(crew, 'ContactCell', ''),
                    }
                    crew_list.append(crew_data)
            
            logger.info(f"Fetched {len(crew_list)} crew members")
            
            return {
                'success': True,
                'count': len(crew_list),
                'crew_list': crew_list,
                'error': None
            }
            
        except Fault as e:
            logger.error(f"SOAP Fault in get_crew_list: {e}")
            return {'success': False, 'error': str(e), 'crew_list': []}
        except Exception as e:
            logger.error(f"Error in get_crew_list: {e}")
            raise
    
    def _parse_aims_datetime(self, date_str: str, time_str: str) -> Optional[str]:
        """Parse AIMS date/time strings to ISO format"""
        if not date_str or not time_str:
            return None
        try:
            # Handle various date formats
            date_str = date_str.strip()
            time_str = time_str.strip()
            
            # Try DD/MM/YY or DD/MM/YYYY format
            for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", f"{fmt} %H:%M")
                    return dt.isoformat()
                except ValueError:
                    continue
            return None
        except Exception:
            return None
    
    def _calculate_block_minutes(self, atd: str, ata: str) -> int:
        """Calculate block time in minutes from ATD/ATA strings"""
        if not atd or not ata:
            return 0
        try:
            atd_parts = atd.split(':')
            ata_parts = ata.split(':')
            
            atd_minutes = int(atd_parts[0]) * 60 + int(atd_parts[1])
            ata_minutes = int(ata_parts[0]) * 60 + int(ata_parts[1])
            
            # Handle overnight flights
            if ata_minutes < atd_minutes:
                ata_minutes += 24 * 60
                
            return ata_minutes - atd_minutes
        except Exception:
            return 0
    
    def get_optimized_date_range(self, days_back: int = 30, days_forward: int = 30):
        """
        Get optimized date range for fetching data (±30 days by default)
        
        Returns:
            tuple: (from_date, to_date)
        """
        now = datetime.now()
        return (
            now - timedelta(days=days_back),
            now + timedelta(days=days_forward)
        )
    
    def calculate_rolling_28day_hours(self, crew_id: int) -> Dict[str, Any]:
        """
        Tính toán giờ bay 28 ngày cuốn chiếu (Rolling 28-day Block Hours)
        
        Công thức: SUM(block_minutes) WHERE date BETWEEN (Today - 28) AND Today
        
        Args:
            crew_id: Mã phi hành đoàn
            
        Returns:
            dict: {
                'block_hours': float,
                'alert_status': 'normal' | 'warning' | 'critical',
                'details': list
            }
        """
        now = datetime.now()
        from_date = now - timedelta(days=28)
        
        # Get crew roster for 28 days
        roster = self.get_crew_roster(crew_id, from_date, now)
        
        if not roster['success']:
            return {
                'block_hours': 0,
                'block_minutes': 0,
                'alert_status': 'error',
                'error': roster.get('error'),
                'details': []
            }
        
        # Sum block minutes from roster items
        total_minutes = sum(
            item.get('block_minutes', 0) or self._calculate_block_from_schedule(item)
            for item in roster['items']
        )
        
        total_hours = total_minutes / 60.0
        
        # Determine alert status based on Alert Matrix
        if total_hours > 95:
            alert_status = 'critical'
        elif total_hours > 85:
            alert_status = 'warning'
        else:
            alert_status = 'normal'
        
        return {
            'crew_id': crew_id,
            'block_hours': round(total_hours, 2),
            'block_minutes': total_minutes,
            'alert_status': alert_status,
            'from_date': from_date.isoformat(),
            'to_date': now.isoformat(),
            'details': roster['items']
        }
    
    def _calculate_block_from_schedule(self, roster_item: dict) -> int:
        """Calculate block minutes from schedule times if actual not available"""
        raw = roster_item.get('_raw', {})
        atd = raw.get('ATD') or raw.get('STD')
        ata = raw.get('ATA') or raw.get('STA')
        return self._calculate_block_minutes(atd, ata)
    
    @retry_on_failure(max_retries=3)
    def fetch_leg_members_per_day(self, date: datetime) -> Dict[str, Any]:
        """
        FetchLegMembersPerDay - Lấy tất cả chuyến bay và phi hành đoàn trong ngày
        
        Maps to AIMS: TAIMSDayGetLegMembers
        
        Args:
            date: Ngày cần lấy dữ liệu
            
        Returns:
            dict: {
                'success': bool,
                'legs': list of flights with crew,
                'error': str or None
            }
        """
        self._init_client()
        date_parts = self._format_date_parts(date)
        
        try:
            response = self._service.FetchLegMembersPerDay(
                UN=self.username,
                PSW=self.password,
                DD=date_parts['DD'],
                MM=date_parts['MM'],
                YYYY=date_parts['YYYY']
            )
            
            # Check for AIMS error
            error_msg = getattr(response, 'ErrorExplanation', None) or getattr(response, 'Error', None)
            if error_msg and str(error_msg).strip():
                logger.error(f"AIMS Error in FetchLegMembersPerDay: {error_msg}")
                return {'success': False, 'error': str(error_msg), 'legs': [], 'date': date.strftime('%d/%m/%Y')}
            
            # Parse response
            legs = []
            leg_list = getattr(response, 'LegList', None) or getattr(response, 'Legs', None)
            
            if leg_list:
                # Handle both list and object with items
                items = leg_list if isinstance(leg_list, list) else getattr(leg_list, 'TAIMSLegMember', [])
                
                for leg in items:
                    leg_data = {
                        'flight_no': getattr(leg, 'Flt', '') or getattr(leg, 'FlightNo', ''),
                        'reg': getattr(leg, 'Reg', '') or getattr(leg, 'AcReg', ''),
                        'dep': getattr(leg, 'Dep', '') or getattr(leg, 'Departure', ''),
                        'arr': getattr(leg, 'Arr', '') or getattr(leg, 'Arrival', ''),
                        'std': getattr(leg, 'STD', '') or getattr(leg, 'DepTime', ''),
                        'sta': getattr(leg, 'STA', '') or getattr(leg, 'ArrTime', ''),
                        'date': date.strftime('%d/%m/%Y'),
                        'crew': []
                    }
                    
                    # Parse crew members
                    crew_list = getattr(leg, 'CrewList', None) or getattr(leg, 'Crew', None)
                    if crew_list:
                        crew_items = crew_list if isinstance(crew_list, list) else getattr(crew_list, 'TAIMSCrewMember', [])
                        for crew in crew_items:
                            leg_data['crew'].append({
                                'id': str(getattr(crew, 'ID', '') or getattr(crew, 'CrewId', '')),
                                'name': getattr(crew, 'Name', '') or getattr(crew, 'CrewName', ''),
                                'role': getattr(crew, 'Role', '') or getattr(crew, 'Position', '')
                            })
                    
                    legs.append(leg_data)
            
            logger.info(f"FetchLegMembersPerDay: Got {len(legs)} legs for {date.strftime('%d/%m/%Y')}")
            
            return {
                'success': True,
                'date': date.strftime('%d/%m/%Y'),
                'count': len(legs),
                'legs': legs,
                'error': None
            }
            
        except Fault as e:
            logger.error(f"SOAP Fault in fetch_leg_members_per_day: {e}")
            return {'success': False, 'error': str(e), 'legs': [], 'date': date.strftime('%d/%m/%Y')}
        except Exception as e:
            logger.error(f"Error in fetch_leg_members_per_day: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def fetch_crew_quals(self, crew_id: int = 0) -> Dict[str, Any]:
        """
        FetchCrewQuals - Lấy ID, Name, Qualifications của tổ bay
        
        Args:
            crew_id: Mã phi hành đoàn (0 = tất cả)
            
        Returns:
            dict: Crew qualifications data
        """
        self._init_client()
        
        try:
            response = self._service.FetchCrewQuals(
                UN=self.username,
                PSW=self.password,
                ID=crew_id
            )
            
            # Check for AIMS error
            error_msg = getattr(response, 'ErrorExplanation', None)
            if error_msg and str(error_msg).strip():
                logger.error(f"AIMS Error in FetchCrewQuals: {error_msg}")
                return {'success': False, 'error': str(error_msg), 'crew': []}
            
            # Parse response
            crew_list = []
            quals_list = getattr(response, 'QualsList', None) or getattr(response, 'CrewQuals', None)
            
            if quals_list:
                items = quals_list if isinstance(quals_list, list) else getattr(quals_list, 'TAIMSCrewQual', [])
                
                for crew in items:
                    crew_data = {
                        'crew_id': str(getattr(crew, 'ID', '') or getattr(crew, 'CrewId', '')),
                        'name': getattr(crew, 'Name', '') or getattr(crew, 'CrewName', ''),
                        'qualifications': getattr(crew, 'Quals', '') or getattr(crew, 'Qualifications', ''),
                        'base': getattr(crew, 'Base', ''),
                        'rank': getattr(crew, 'Rank', '') or getattr(crew, 'Position', '')
                    }
                    crew_list.append(crew_data)
            
            logger.info(f"FetchCrewQuals: Got {len(crew_list)} crew members")
            
            return {
                'success': True,
                'count': len(crew_list),
                'crew': crew_list,
                'error': None
            }
            
        except Fault as e:
            logger.error(f"SOAP Fault in fetch_crew_quals: {e}")
            return {'success': False, 'error': str(e), 'crew': []}
        except Exception as e:
            logger.error(f"Error in fetch_crew_quals: {e}")
            raise
    
    @retry_on_failure(max_retries=3)
    def crew_schedule_changes_for_period(
        self, 
        from_date: datetime, 
        to_date: datetime
    ) -> Dict[str, Any]:
        """
        CrewScheduleChangesForPeriod - Lấy log các thay đổi lịch trình
        
        Args:
            from_date: Ngày bắt đầu
            to_date: Ngày kết thúc
            
        Returns:
            dict: Schedule change logs
        """
        self._init_client()
        
        from_parts = self._format_date_parts(from_date)
        to_parts = self._format_date_parts(to_date)
        
        try:
            response = self._service.CrewScheduleChangesForPeriod(
                UN=self.username,
                PSW=self.password,
                FmDD=from_parts['DD'],
                FmMM=from_parts['MM'],
                FmYY=from_parts['YY'],
                ToDD=to_parts['DD'],
                ToMM=to_parts['MM'],
                ToYY=to_parts['YY']
            )
            
            # Check for AIMS error
            error_msg = getattr(response, 'ErrorExplanation', None)
            if error_msg and str(error_msg).strip():
                logger.error(f"AIMS Error in CrewScheduleChangesForPeriod: {error_msg}")
                return {'success': False, 'error': str(error_msg), 'changes': []}
            
            # Parse response
            changes = []
            change_list = getattr(response, 'ChangeList', None) or getattr(response, 'Changes', None)
            
            if change_list:
                items = change_list if isinstance(change_list, list) else getattr(change_list, 'TAIMSScheduleChange', [])
                
                for change in items:
                    change_data = {
                        'crew_id': str(getattr(change, 'CrewId', '')),
                        'change_type': getattr(change, 'ChangeType', ''),
                        'change_date': getattr(change, 'ChangeDate', ''),
                        'old_value': getattr(change, 'OldValue', ''),
                        'new_value': getattr(change, 'NewValue', ''),
                        'reason': getattr(change, 'Reason', '')
                    }
                    changes.append(change_data)
            
            logger.info(f"CrewScheduleChangesForPeriod: Got {len(changes)} changes")
            
            return {
                'success': True,
                'from_date': from_date.isoformat(),
                'to_date': to_date.isoformat(),
                'count': len(changes),
                'changes': changes,
                'error': None
            }
            
        except Fault as e:
            logger.error(f"SOAP Fault in crew_schedule_changes_for_period: {e}")
            return {'success': False, 'error': str(e), 'changes': []}
        except Exception as e:
            logger.error(f"Error in crew_schedule_changes_for_period: {e}")
            raise


# Singleton instance
_aims_client = None


def get_aims_client() -> AIMSSoapClient:
    """Get or create AIMS SOAP client singleton"""
    global _aims_client
    if _aims_client is None:
        _aims_client = AIMSSoapClient()
    return _aims_client


def is_aims_available() -> bool:
    """Check if AIMS integration is available and enabled"""
    client = get_aims_client()
    return client.is_enabled() and client.is_configured()


# CLI for testing
if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("AIMS SOAP Client - Connection Test")
    print("=" * 60)
    
    client = get_aims_client()
    
    print(f"\nWSDL URL: {client.wsdl_url}")
    print(f"Credentials configured: {client.is_configured()}")
    print(f"AIMS Enabled: {client.is_enabled()}")
    
    if '--test' in sys.argv:
        print("\nTesting connection...")
        result = client.test_connection()
        
        print(f"\nStatus: {result['status']}")
        print(f"Message: {result['message']}")
        
        if result['status'] == 'ok':
            print(f"\nAvailable operations ({len(result['operations'])}):")
            for op in sorted(result['operations'])[:10]:
                print(f"  - {op}")
            if len(result['operations']) > 10:
                print(f"  ... and {len(result['operations']) - 10} more")
        
        sys.exit(0 if result['status'] == 'ok' else 1)
    
    print("\nRun with --test to test connection")
    print("Example: python aims_soap_client.py --test")
