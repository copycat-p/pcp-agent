import unittest
from unittest.mock import patch, MagicMock
from optimizer.windows_optimizer import WindowsOptimizer

class TestWindowsOptimizer(unittest.TestCase):

    @patch('subprocess.run')
    def test_disable_startup_program_general(self, mock_subprocess):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_subprocess.return_value = mock_res

        res = WindowsOptimizer.execute("disable_startup_program", "general")
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Invalid target", res["message"])

    @patch('subprocess.run')
    def test_disable_startup_program_empty_target(self, mock_subprocess):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_subprocess.return_value = mock_res

        res = WindowsOptimizer.execute("disable_startup_program", "")
        self.assertEqual(res["status"], "FAILED")
        self.assertIn("Invalid target", res["message"])

    @patch('subprocess.run')
    def test_disable_startup_program_specific(self, mock_subprocess):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_subprocess.return_value = mock_res

        res = WindowsOptimizer.execute("disable_startup_program", "CustomApp")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("CustomApp", res["message"])

    @patch('subprocess.run')
    def test_clean_recycle_bin(self, mock_subprocess):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_subprocess.return_value = mock_res

        res = WindowsOptimizer.execute("clean_recycle_bin", "")
        self.assertEqual(res["status"], "SUCCESS")
        self.assertIn("recycle bin", res["message"].lower())

if __name__ == "__main__":
    unittest.main()

