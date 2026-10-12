import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location("installer",Path(__file__).resolve().parents[1]/"scripts/install.py")
installer=importlib.util.module_from_spec(spec); spec.loader.exec_module(installer)

class InstallerTests(unittest.TestCase):
    def test_snapshot_integrity(self): installer.verify()
    def test_boot_preserves_and_is_idempotent(self):
        original="[all]\ndtoverlay=s5krc1s-cam0\n# display settings\n"
        result=installer.configure_boot(original)
        self.assertTrue(result.startswith(original))
        self.assertEqual(result.count("dtoverlay=s5krc1s-cam0"),1)
        self.assertIn("dtparam=i2c_csi_dsi0=on",result)
        self.assertEqual(installer.configure_boot(result),result)
    def test_restore_existing_and_new_files_and_venv(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); old=root/"old"; new=root/"new"; venv=root/"venv"
            old.write_text("old configuration");old.chmod(0o640)
            venv.mkdir(); (venv/"python").symlink_to("/usr/bin/python3")
            installer.backup([old,new,venv],root/"backup")
            old.write_text("changed");new.write_text("installed");(venv/"new-lib").touch()
            installer.restore(root/"backup")
            self.assertEqual(old.read_text(),"old configuration")
            self.assertEqual(old.stat().st_mode&0o777,0o640)
            self.assertFalse(new.exists());self.assertFalse((venv/"new-lib").exists())
            self.assertTrue((venv/"python").is_symlink())
