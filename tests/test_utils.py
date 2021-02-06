import unittest

from lib import utils


class TestUtils(unittest.TestCase):

    def test_parse_k8s_time(self):
        time = utils.parse_k8s_time("2021-02-03T11:33:05Z")
        self.assertEqual(time.timestamp(), 1612351985.0)
        time2 = utils.parse_k8s_time("2021-02-03T11:34:05Z")
        self.assertGreater(time2, time)
