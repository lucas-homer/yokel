"""Read a transient JSON line without PTY echo or canonical line limits."""
import json, sys, termios

def read_json_line():
    if sys.stdin.isatty():
        mode = termios.tcgetattr(sys.stdin.fileno())
        mode[3] &= ~(termios.ECHO | termios.ECHONL | termios.ICANON)
        mode[6][termios.VMIN] = 1
        mode[6][termios.VTIME] = 0
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, mode)
    print('{"stdin_ready":true}', flush=True)
    line = sys.stdin.readline()
    if not line:
        raise RuntimeError('Transient stdin closed before payload')
    return json.loads(line)
