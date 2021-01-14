import ctypes

from . import com, stocks

# http://cybosplus.github.io/


assert com.cybos.IsConnect, 'Disconnected'
assert ctypes.windll.shell32.IsUserAnAdmin(), 'Not administrator'
