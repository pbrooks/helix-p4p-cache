from cache.sync import __main__ as main
import socket
import pytest
import subprocess
import tempfile
import threading

import time
import os
import logging


class P4DServer(threading.Thread):

    def __init__(self):
        self.P4ROOT = tempfile.TemporaryDirectory()
        self.P4PORT = "localhost:{}".format(self.generate_port())
        super().__init__()

    def generate_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        return sock.getsockname()[1]

    def run(self):
        env = {"P4ROOT": self.P4ROOT.name,
               "P4PORT": self.P4PORT}
        self._process = subprocess.Popen("p4d", env=env)
        time.sleep(1.0)

    def __del__(self):
        self._process.terminate()


@pytest.fixture
def p4d():
    p4d = P4DServer()
    p4d.start()
    p4d.join()
    return p4d


def test_sync(p4d, capfd):
    import sys
    sys.argv = ['']
    os.environ['P4PORT'] = p4d.P4PORT
    main()
    out, err = capfd.readouterr()
    assert "" == out
    assert "" == err


def test_sync_nop4d_err(capfd):
    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    out, err = capfd.readouterr()
    assert "" == out
    assert "Perforce client error" in err
