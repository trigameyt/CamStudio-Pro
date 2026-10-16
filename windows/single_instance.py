"""One CamStudio Pro process per Windows user, including tray-hidden windows.

The second launch sends SHOW to the already running instance over a local Qt
socket rather than creating a competing webcam pipeline.
"""
from __future__ import annotations
import getpass
import hashlib
import os

from PySide6.QtCore import QObject,Signal
from PySide6.QtNetwork import QLocalServer,QLocalSocket


def server_name():
    ident=f'{getpass.getuser()}|{os.path.expanduser("~")}'
    testing=os.getenv('CAMSTUDIO_INSTANCE_NAMESPACE','')
    digest=hashlib.sha256((ident+testing).encode('utf-8')).hexdigest()[:20]
    return 'CamStudioPro-V1-'+digest


class InstanceGuard(QObject):
    show_requested=Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.name=server_name()
        self.server=QLocalServer(self)
        self.server.newConnection.connect(self._incoming)
        self._connections=[]

    def _send_show(self):
        other=QLocalSocket(self)
        other.connectToServer(self.name)
        if not other.waitForConnected(450):
            other.abort()
            return False
        other.write(b'SHOW\n')
        other.flush()
        other.waitForBytesWritten(500)
        other.disconnectFromServer()
        return True

    def acquire(self):
        if self._send_show():
            return False
        if self.server.listen(self.name):
            return True
        # Handle another instance starting at the same time. Never open a
        # second unprotected stream on failure to acquire the local server.
        if self._send_show():
            return False
        # On Unix stale sockets can remain after a crash; do not remove
        # another process's live endpoint without a failed connection check.
        if os.name != 'nt':
            QLocalServer.removeServer(self.name)
            if self.server.listen(self.name):
                return True
        raise RuntimeError("Une autre instance de CamStudio Pro est déjà active ou le verrou local est indisponible.")

    def _incoming(self):
        while self.server.hasPendingConnections():
            sock=self.server.nextPendingConnection()
            self._connections.append(sock)
            sock.readyRead.connect(lambda s=sock:self._ready(s))
            sock.disconnected.connect(lambda s=sock:self._release(s))
            if sock.bytesAvailable():
                self._ready(sock)

    def _ready(self,sock):
        command=bytes(sock.readAll()).strip()
        if command==b'SHOW':
            self.show_requested.emit()
        sock.disconnectFromServer()

    def _release(self,sock):
        if sock in self._connections:
            self._connections.remove(sock)
        sock.deleteLater()
