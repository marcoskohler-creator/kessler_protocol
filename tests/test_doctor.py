import unittest
import tempfile
from pathlib import Path
from unittest import mock
from kessler_protocol.doctor import package_checks

class DoctorTests(unittest.TestCase):
    def test_deep_package_doctor(self):
        with tempfile.TemporaryDirectory() as td, mock.patch("pathlib.Path.home", return_value=Path(td)):
            rows=package_checks(deep=True)
        self.assertTrue(all(x[0] for x in rows), rows)

if __name__=="__main__": unittest.main()
