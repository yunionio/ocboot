import unittest

from lib import utils


class TestUtils(unittest.TestCase):

    def test_parse_k8s_time(self):
        time = utils.parse_k8s_time("2021-02-03T11:33:05Z")
        self.assertEqual(time.timestamp(), 1612351985.0)
        time2 = utils.parse_k8s_time("2021-02-03T11:34:05Z")
        self.assertGreater(time2, time)

    def test_is_below_v3_9(self):
        self.assertTrue(utils.is_below_v3_9('v3.8.11'))
        self.assertTrue(utils.is_below_v3_9('v3.7.11'))
        self.assertTrue(utils.is_below_v3_9('v3.6.11'))
        self.assertTrue(utils.is_below_v3_9('v2.6.11'))
        self.assertFalse(utils.is_below_v3_9('v3.9.0'))
        self.assertFalse(utils.is_below_v3_9('master-test'))
