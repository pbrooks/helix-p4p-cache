from cache.sync import __main__ as main

import os
from pathlib import Path
import pytest
import socket
import subprocess
import sys
import tempfile
import threading
import time

from P4 import P4


class NetworkDaemon(threading.Thread):

    def generate_port(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('', 0))
        return sock.getsockname()[1]

    def __del__(self):
        self._process.terminate()


class P4DServer(NetworkDaemon):

    def __init__(self):
        self.P4ROOT = tempfile.TemporaryDirectory()
        self.P4PORT = "localhost:{}".format(self.generate_port())
        super().__init__()

    def run(self):
        env = {"P4ROOT": self.P4ROOT.name,
               "P4PORT": self.P4PORT}
        self._process = subprocess.Popen("p4d", env=env)
        time.sleep(1.0)


class P4PServer(NetworkDaemon):

    def __init__(self, P4TARGET):
        self.P4TARGET = P4TARGET
        self.P4PDIR = tempfile.TemporaryDirectory()
        p4p_path = Path(self.P4PDIR.name)
        self.P4PROOT = p4p_path.joinpath("root")
        self.P4PCACHE = p4p_path.joinpath("cache")
        self.P4LOG = p4p_path.joinpath("log.txt")
        self.P4PORT = "localhost:{}".format(self.generate_port())
        self.P4PROOT.mkdir()
        self.P4PCACHE.mkdir()
        super().__init__()


    def run(self):
        env = {"P4PROOT": str(self.P4PROOT),
               "P4PCACHE": str(self.P4PCACHE),
               "P4LOG": str(self.P4LOG),
               "P4TARGET": self.P4TARGET,
               "P4PORT": self.P4PORT,
               }
        self.env = env

        self._process = subprocess.Popen("/usr/bin/p4p", env=env)
        time.sleep(1.0)


class P4Client(object):

    def get_p4(self, P4PORT, P4CLIENT, P4ROOT):
        p4 = P4()
        p4.port = P4PORT
        p4.connect()
        p4.client = P4CLIENT
        p4_client = p4.fetch_client()
        p4_client._root = P4ROOT
        p4.save_client(p4_client)
        return p4, p4_client

    def __init__(self, P4PORT, P4CLIENT):
        self.root_dir = tempfile.TemporaryDirectory()
        self.p4, self.p4_client = self.get_p4(P4PORT, P4CLIENT,
                                              self.root_dir.name)

    def add_data(self, data):
        root = Path(self.root_dir.name)
        for x in data:
            files = []
            for filename, content in x[1].items():
                path = root.joinpath(filename)
                with open(path, 'w') as fh:
                    fh.write(content)
                files.append("//depot/" + filename)
                self.p4.run_add(str(path))

            change = self.p4.fetch_change()
            change._description = x[0]
            change._files = files
            self.p4.run_submit(change)


def sync(P4PORT, P4ROOT):
    sys.argv = ['']
    os.environ['P4PORT'] = P4PORT
    os.environ['P4ROOT'] = P4ROOT
    main()


@pytest.fixture
def p4d():
    p4d = P4DServer()
    p4d.start()
    p4d.join()
    return p4d


@pytest.fixture
def p4p(p4d):
    p4p = P4PServer(p4d.P4PORT)
    p4p.start()
    p4p.join()
    return p4p


def test_sync(p4d, p4p, capfd):
    data = (
        ("Initial commit", {
            "sample.txt": "Sample"}
         ),
    )
    p4_main = P4Client(p4d.P4PORT, "init")
    p4_main.add_data(data)

    sync_root = tempfile.TemporaryDirectory()
    sync(p4p.P4PORT, sync_root.name)
    out, err = capfd.readouterr()
    assert "//depot/sample.txt#1 - added as {}/sample.txt\n"\
        .format(sync_root.name) == out
    assert "" == err


def test_sync_nop4d_err(caplog):
    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    assert "Connect to server failed" in caplog.messages[0]


# bar = "\n".join(["export {}={}".format(k, v) for k, v in p4p.env.items()])
# XXX: Sync against the p4d, instead of p4p?
# XXX: Case with no files at all
# XXX: Resync gets no files
# XXX: Test p4p, but no p4d?
