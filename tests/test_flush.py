from cache.flush import __main__ as main
from pathlib import Path
import pathlib
import logging
import pytest
import tempfile
from time import time


MB = 1024 * 1024
GB = 1024 * MB


class MockPath(Path):

    _mock_ctime = {}

    _flavour = pathlib._PosixFlavour()

    _ctime = None

    def stat(self):
        stat = super().stat()
        if self.absolute() not in self._mock_ctime:
            return stat

        ctime = self._mock_ctime[self.absolute()]

        import os
        return os.stat_result(stat[:-1] + (ctime,))

    def set_ctime(self, value):
        MockPath._mock_ctime[self.absolute()] = value


def test_help(mocker, capsys):
    mocker.patch("sys.argv", [
        "p4p-flush", "-h"
    ])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 0
    out, err = capsys.readouterr()

    assert err == ""
    assert "usage: p4p-flush" in out


def test_notfound_path(mocker, capsys):
    # The TempDir will go out of scope, and be removed
    path = Path(tempfile.TemporaryDirectory().name)

    mocker.patch("sys.argv", [
        "p4p-flush", str(path)
    ])
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    out, err = capsys.readouterr()
    assert "" == out
    assert "Path {} doesn't exist".format(path)


def test_file_path(mocker, capsys):
    path = Path(tempfile.mkstemp()[1])

    mocker.patch("sys.argv", [
        "p4p-flush", str(path)
    ])
    with pytest.raises(SystemExit) as excinfo:
        main()
    out, err = capsys.readouterr()
    assert excinfo.value.code == 2
    assert "" == out
    assert "Path {} is not a directory".format(path) == err


def test_empty_path(mocker, capsys, caplog):
    path = tempfile.TemporaryDirectory()
    caplog.set_level(logging.INFO)
    mocker.patch("sys.argv", [
        "p4p-flush", path.name
    ])

    main()
    out, err = capsys.readouterr()
    assert "" == err
    assert "" == out

    assert "WARNING" == caplog.records[0].levelname
    assert 1 == len(caplog.records)
    assert "No cache files found." == caplog.records[0].message


def prepare_env(mocker, temp_dir, files):
    mocker.patch("pathlib.Path.__new__", side_effect=side_effect_mockpath)

    now = time()
    path = MockPath(temp_dir.name)
    for x in files:
        file_path = path.joinpath(x[0])
        if not file_path.parent.exists():
            file_path.parent.mkdir(parents=True)
        with open(path.joinpath(x[0]), "wb") as fh:
            fh.write(bytes(x[1]))
        if len(x) > 2:
            file_path.set_ctime(now - (x[2] * 60 * 60))
    return path


def side_effect_mockpath(cls, *args, **kwargs):
    return MockPath._from_parts(args)


@pytest.mark.parametrize("args,files,expected", (
    (
        [],
        (
            ("sample,d/1.1", 1*MB),
            ("sample,d/1.2", 2*MB),
        ),
        (
            "sample,d 1.00MB [r1: 1.00MB]",
            "Total: 1.00MB"
        )
    ),
    (
        [],
        (
           ("sample,d/1.1", 1*MB),
           ("sample,d/1.2", 2*MB),
           ("sample,d/1.3", 3*MB)
        ),
        (
            "sample,d 3.00MB [r2: 2.00MB, r1: 1.00MB]",
            "Total: 3.00MB"
        )
    ),
    (
        ["--ttl", "4"],
        (
           ("sample,d/1.1", 1*MB, 5),
           ("sample,d/1.2", 2*MB, 3),
           ("sample,d/1.3", 3*MB, 2)
        ),
        (
            "sample,d 1.00MB [r1: 1.00MB]",
            "Total: 1.00MB"
        )
    ),
    (
        [],
        (
            ("sample,d/1.1", 1*MB),
            ("sample,d/1.2", 2*MB),
        ),
        (
            "sample,d 1.00MB [r1: 1.00MB]",
            "Total: 1.00MB"
        )
    ),
    (
        ["--ttl", "3"],
        (
            ("sample,d/1.1", 1*MB, 2),
            ("sample,d/1.2", 2*MB, 1),
        ),
        (
            # XXX: Best message for here?
            "No cache files found.",
        )
    ),
    (
        ["--min-vers", "2"],
        (
            ("sample,d/1.1", 1*MB, 2),
            ("sample,d/1.2", 2*MB, 1),
        ),
        (
            # XXX: Best message for here?
            "No cache files found.",
        )
    ),
))
def test_output(mocker, caplog, args, files, expected):
    caplog.set_level(logging.INFO)
    temp_dir = tempfile.TemporaryDirectory()

    mocker.patch("sys.argv", [*[
        "p4p-flush", str(prepare_env(mocker, temp_dir, files))
    ], *args])
    main()
    assert caplog.messages == list(expected)


@pytest.mark.parametrize("files,expected_log, expected_files", (
    (
        (
            ("sample,d/1.1", 1*MB),
            ("sample,d/1.2", 2*MB),
        ),
        (
            "Purged sample,d 1.00MB [r1: 1.00MB]",
            "Purge Total: 1.00MB"
        ),
        (
            ("sample,d/1.2",)
        )
    ),
    (
        (
           ("sample,d/1.1", 1*MB),
           ("sample,d/1.2", 2*MB),
           ("sample,d/1.3", 3*MB)
        ),
        (
            "Purged sample,d 3.00MB [r2: 2.00MB, r1: 1.00MB]",
            "Purge Total: 3.00MB"
        ),
        (
            ("sample,d/1.3",)
        )
    ),
))
def test_purge(mocker, caplog, files, expected_log, expected_files):
    caplog.set_level(logging.INFO)
    temp_dir = tempfile.TemporaryDirectory()
    path = prepare_env(mocker, temp_dir, files)

    mocker.patch("sys.argv", [
        "p4p-flush", "--purge", str(path)
    ])
    main()
    assert caplog.messages == list(expected_log)

    for x in files:
        item = path.joinpath(x[0])
        if x[0] not in expected_files:
            assert not item.exists()
        else:
            assert item.exists()


# XXX: Expand test cases
# dir/dir/dir/file
