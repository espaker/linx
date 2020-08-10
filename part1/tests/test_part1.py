import unittest

from part1.src import app


class Test_app(unittest.TestCase):
    
    def setUp(self):
        self.response = app.get('/')


if __name__ == '__main__':
    unittest.main()