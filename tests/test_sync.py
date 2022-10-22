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


'''
P4D - Add basic files into the repo
Then decide how to spin up a p4p.


'''


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
    # Section here, will make a client and submit files
    data = (
        ("Initial commit", {
            "sample.txt": "Sample"}
         ),
    )

    p4 = P4()
    p4.port = p4d.P4PORT
    p4.connect()
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
    # XXX: Doesn't want to be the p4d direct
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
