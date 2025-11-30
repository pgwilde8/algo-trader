import logging
import sys
from datetime import datetime
import pytz

def setup_logging():
    """Configure logging with Eastern Time timestamps"""
    eastern = pytz.timezone('US/Eastern')
    
    class EasternTimeFormatter(logging.Formatter):
        def formatTime(self, record, datefmt=None):
            dt = datetime.fromtimestamp(record.created, tz=eastern)
            return dt.strftime('%Y-%m-%d %H:%M:%S %Z')
    
    formatter = EasternTimeFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)

