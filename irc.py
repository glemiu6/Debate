"""
Minimal IRC client (pure stdlib, socket-based — no extra dependencies)
for posting debate turns into an IRC channel.

Handles: connection registration, PING/PONG keepalive, channel join,
message chunking (IRC lines are capped around 512 bytes), and basic
flood protection via a per-message delay.
"""

import select
import socket
import ssl
import time

# mIRC color codes: name -> two-digit code
IRC_COLORS = {
    "green": "03",
    "yellow": "08",
    "cyan": "11",
    "magenta": "13",
    "white": "00",
    "dim": "14",
    "red": "04",
}


def irc_color(text: str, color_name: str) -> str:
    code = IRC_COLORS.get(color_name)
    if not code:
        return text
    return f"\x03{code}{text}\x03"


class IRCBridge:
    def __init__(self, server: str, port: int = 6667, nick: str = "DebateBot",
                 channel: str = "#debate", use_ssl: bool = False, password: str = None):
        self.server = server
        self.port = port
        self.nick = nick
        self.channel = channel if channel.startswith("#") else f"#{channel}"
        self.use_ssl = use_ssl
        self.password = password
        self.sock = None
        self._buffer = ""

    def connect(self, timeout: float = 15):
        raw_sock = socket.create_connection((self.server, self.port), timeout=timeout)
        if self.use_ssl:
            ctx = ssl.create_default_context()
            self.sock = ctx.wrap_socket(raw_sock, server_hostname=self.server)
        else:
            self.sock = raw_sock

        if self.password:
            self._send_raw(f"PASS {self.password}")
        self._send_raw(f"NICK {self.nick}")
        self._send_raw(f"USER {self.nick} 0 * :{self.nick}")
        self._wait_for_welcome(timeout=timeout)
        self._send_raw(f"JOIN {self.channel}")
        time.sleep(1)  # give the server a moment to process the join

    def _send_raw(self, line: str):
        self.sock.sendall((line + "\r\n").encode("utf-8", errors="ignore"))

    def _readlines_nonblocking(self, timeout: float = 0.0):
        """Drain any currently-available data and yield complete lines."""
        readable, _, _ = select.select([self.sock], [], [], timeout)
        if readable:
            try:
                chunk = self.sock.recv(4096).decode("utf-8", errors="ignore")
            except (ConnectionResetError, OSError):
                return
            self._buffer += chunk
        while "\r\n" in self._buffer:
            line, self._buffer = self._buffer.split("\r\n", 1)
            yield line

    def _wait_for_welcome(self, timeout: float = 15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for line in self._readlines_nonblocking(timeout=1):
                if line.startswith("PING"):
                    self._send_raw(line.replace("PING", "PONG", 1))
                if " 001 " in line:  # RPL_WELCOME = registration succeeded
                    return
                if " 433 " in line:  # nick already in use
                    raise RuntimeError(f"IRC nick '{self.nick}' is already in use on this server.")
        raise RuntimeError("Timed out waiting for IRC server welcome (001). Check server/port.")

    def pump(self):
        """Call periodically (e.g. before sending) to answer any pending PING."""
        for line in self._readlines_nonblocking(timeout=0):
            if line.startswith("PING"):
                self._send_raw(line.replace("PING", "PONG", 1))

    def send_message(self, text: str, chunk_size: int = 400, delay: float = 0.6):
        """Split long text into IRC-safe chunks and send as PRIVMSGs."""
        self.pump()
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i + chunk_size]
            self._send_raw(f"PRIVMSG {self.channel} :{chunk}")
            time.sleep(delay)  # basic flood protection

    def close(self):
        try:
            self._send_raw("QUIT :debate finished")
            self.sock.close()
        except Exception:
            pass