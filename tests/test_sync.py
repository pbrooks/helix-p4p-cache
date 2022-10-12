from cache.sync import __main__ as main
import socket
import pytest
import subprocess
import tempfile
import threading


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

    def __del__(self):
        self._process.terminate()


@pytest.fixture
def p4d():
    p4d = P4DServer()
    p4d.start()
    p4d.join()
    return p4d


def test_sync(p4d, capsys, caplog):
    main()
    out, err = capsys.readouterr()
    assert "" == out
    assert "" == err


def test_sync_err(p4d, capsys, caplog):
    with pytest.raises(SystemExit) as excinfo:
        main()
    out, err = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "" == out
    assert "foobar" == err
