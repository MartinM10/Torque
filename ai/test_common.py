import unittest
from common import generate_pc_columns_names


class TestCommon(unittest.TestCase):
    def test_generate_pc_columns_names(self):
        self.assertAlmostEqual(generate_pc_columns_names(2), ['pc1', 'pc2'])


if __name__ == '__main__':
    unittest.main()
