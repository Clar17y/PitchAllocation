from functools import wraps
from sqlalchemy.exc import OperationalError
import time

def retry_on_db_error(max_retries=3, delay=1):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return f(*args, **kwargs)
                except OperationalError as e:
                    retries += 1
                    if retries == max_retries:
                        raise
                    time.sleep(delay * (2 ** (retries - 1)))  # Exponential backoff
            return f(*args, **kwargs)
        return wrapper
    return decorator