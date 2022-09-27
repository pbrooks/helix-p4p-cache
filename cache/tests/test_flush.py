from collections import namedtuple
import logging
from pathlib import Path
import pytest
import pathlib
import tempfile
from time import time
import unittest

from .. import flush

MB = 1024*1024


class MockPath(Path):

    _children = []
    _flavour = pathlib._PosixFlavour()

    def __init__(self, name):
        self._name = name

    def iterdir(self):
        return self._children


class MockDir(MockPath):

    def __init__(self, name, children=()):
        super().__init__(name)
        self._children = children


class MockFile(MockPath):

    deleted = False
    _ctime = None

    def __init__(self, name, size=0, ctime=0):
        super().__init__(name)
        self._size = size
        self._ctime = time() - (ctime * 60 * 60)

    def stat(self, *, follow_symlinks=True):
        MockStat = namedtuple(
                "mock_stat",
                ("st_size", 'st_ctime'))
        return MockStat(self._size, self._ctime)

    def unlink(self):
        self.deleted = True


class TestFindFiles(unittest.TestCase):

    def test_invaliddirectory_raises(self):
        path = Path(tempfile.TemporaryDirectory().name)
        with self.assertRaises(ValueError) as ex:
            flush.find_files(path)
        self.assertEqual("Path {} doesn't exist".format(path),
                         str(ex.exception))

    def test_file_raises(self):
        path = Path(tempfile.mkstemp()[1])
        with self.assertRaises(ValueError) as ex:
            flush.find_files(path)
        self.assertEqual("Path {} is not a directory".format(path),
                         str(ex.exception))


class TestFilterExpired(unittest.TestCase):

    default_args = ((), 0, 1)

    def test_discover_directory(self):
        self.assertEqual(0, len(
            list(flush.filter_expired(*self.default_args))))

    def test_default_singlerev_noexpired(self):
        files = (MockDir("sample,d", children=(
            MockFile("sample,d/1.1", size=1*MB),)),)
        self.assertEqual(0, len(
            list(flush.filter_expired(files, *self.default_args[1:]))))

    def test_default_multiplerev_singleexpired(self):
        files = (MockDir("sample,d", children=[
            MockFile("sample,d/1.1", size=1*MB),
            MockFile("sample,d/1.2", size=2*MB)]),)
        expired = list(flush.filter_expired(files, *self.default_args[1:]))
        expected = [(files[0], [(files[0]._children[0], "1", 1*MB)])]
        self.assertEqual(expected, expired)

    def test_default_multiplerev_multipleexpired(self):
        files = (MockDir("sample,d", children=[
            MockFile("sample,d/1.1", size=1*MB),
            MockFile("sample,d/1.2", size=2*MB),
            MockFile("sample,d/1.3", size=3*MB),
            ]),)
        expired = list(flush.filter_expired(files, *self.default_args[1:]))
        expected = [(files[0], [
            (files[0]._children[1], "2", 2*MB),
            (files[0]._children[0], "1", 1*MB)]
        )]
        self.assertEqual(expected, expired)

    def test_vers_expire_rev1(self):
        files = (MockDir("sample,d", children=[
            MockFile("sample,d/1.1", size=1*MB, ctime=4),
            MockFile("sample,d/1.2", size=1*MB, ctime=2),
            MockFile("sample,d/1.3", size=2*MB, ctime=1),
            ]),)
        expired = list(flush.filter_expired(files, *self.default_args[1:2], 2))
        expected = [(files[0], [
            (files[0]._children[0], "1", 1*MB)]
        )]
        self.assertEqual(expected, expired)

    def test_ttl_expire_rev1(self):
        files = (MockDir("sample,d", children=[
            MockFile("sample,d/1.1", size=1*MB, ctime=4),
            MockFile("sample,d/1.2", size=1*MB, ctime=2),
            MockFile("sample,d/1.3", size=2*MB, ctime=1),
            ]),)
        expired = list(flush.filter_expired(files, 3, *self.default_args[2:]))
        expected = [(files[0], [
            (files[0]._children[0], "1", 1*MB)]
        )]
        self.assertEqual(expected, expired)

    def test_ttl_onevalid_equalttl(self):
        files = (MockDir("sample,d", children=[
            MockFile("sample,d/1.1", size=1*MB, ctime=3),
            MockFile("sample,d/1.2", size=2*MB, ctime=2),
            ]),)
        expired = list(flush.filter_expired(files, 2, *self.default_args[2:]))
        expected = [(files[0], [
            (files[0]._children[0], "1", 1*MB)]
        )]
        self.assertEqual(expected, expired)


class TestProcess(unittest.TestCase):

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog
        self._caplog.set_level(logging.INFO)

    def test_empty_nofilesfound(self):
        flush.process(Path(), [], False)
        self.assertEqual(["No cache files found."], self._caplog.messages)

    def test_single_expired(self):
        expired = (
            (
                MockDir("sample,d"),
                [(MockFile("sample,d/1.1", size=1*MB), "1", 1*MB)]
            ),)

        flush.process(Path(), expired, False)
        self.assertEqual(
                ["sample,d 1.00MB [r1: 1.00MB]",
                 "Total: 1.00MB"],
                self._caplog.messages)

    def test_multiple_expired(self):
        expired = (
            (
                MockDir("sample,d"), [
                    (MockFile("sample,d/1.2", size=2*MB), "2", 2*MB),
                    (MockFile("sample,d/1.1", size=1*MB), "1", 1*MB)
                ]
            ),)

        flush.process(Path(), expired, False)
        self.assertEqual(
                ["sample,d 3.00MB [r2: 2.00MB, r1: 1.00MB]",
                 "Total: 3.00MB"],
                self._caplog.messages)

    def test_single_purge(self):
        expired = (
            (
                MockDir("sample,d"),
                [(MockFile("sample,d/1.1", size=1*MB), "1", 1*MB)]
            ),)

        flush.process(Path(), expired, True)
        self.assertEqual(
                ["Purged sample,d 1.00MB [r1: 1.00MB]",
                 "Purge Total: 1.00MB"],
                self._caplog.messages)

        for item in expired:
            for x in item[1]:
                self.assertTrue(x[0].deleted)
