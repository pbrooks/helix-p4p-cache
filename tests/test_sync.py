from cache.sync import __main__ as main
import socket
import pytest
import subprocess
import tempfile
import threading

import time
import os
import logging

from P4 import P4
from pathlib import Path


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


# bar = "\n".join(["export {}={}".format(k, v) for k, v in p4p.env.items()])


def test_sync(p4d, p4p, capfd):
    # Section here, will make a client and submit files
    data = (
        ("Initial commit", {
            "sample.txt": "Sample"}
         ),
    )

    p4 = P4()
    p4.port = p4d.P4PORT
    p4.connect()
    p4.client = "init"
    p4_client = p4.fetch_client()
    root_dir = tempfile.TemporaryDirectory()
    p4_client._root = root_dir.name
    p4.save_client(p4_client)
    root = Path(root_dir.name)
    
    for x in data:
        files = []
        for filename, content in x[1].items():
            path = root.joinpath(filename)
            with open(path, 'w') as fh:
                fh.write(content)
            files.append("//depot/" + filename)
            p4.run_add(str(path))

        change = p4.fetch_change()
        change._description = x[0]
        change._files = files
        p4.run_submit(change)

    # XXX: Principal here, need to also be able to run a p4p

    # Run the sync
    import sys
    sys.argv = ['']
    sync_root = tempfile.TemporaryDirectory()
    os.environ['P4PORT'] = p4p.P4PORT
    os.environ['P4ROOT'] = sync_root.name
    out, err = capfd.readouterr()
    main()
    out, err = capfd.readouterr()
    assert "//depot/sample.txt#1 - added as {}/sample.txt\n"\
        .format(sync_root.name) == out
    assert "" == err

    # XXX: Case with no files at all
    # XXX: Resync gets no files


def test_sync_nop4d_err(capfd):
    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1
    out, err = capfd.readouterr()
    assert "" == out
    assert "Perforce client error" in err
