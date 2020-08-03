from zipline.utils.run_algo import load_extensions
import os

# Load extensions.py; this allows you access to custom bundles
load_extensions(
    default=True,
    extensions=[],
    strict=True,
    environ=os.environ,
)


from trading_calendars import get_calendar

tt = get_calendar('AShare')
print(tt)