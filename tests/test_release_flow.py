from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseVersionTests(unittest.TestCase):
    def load_version_module(self):
        path = ROOT / "release" / "version.py"
        spec = importlib.util.spec_from_file_location("addon_release_version", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_version_update_changes_config_and_prepends_changelog(self) -> None:
        module = self.load_version_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config.yaml"
            changelog = root / "CHANGELOG.md"
            config.write_text('name: HA Bridge\nversion: "0.4.2-1"\n', encoding="utf-8")
            changelog.write_text("# 更新日志\n\n## 0.4.2-1\n\n- 旧版本。\n", encoding="utf-8")
            module.CONFIG_PATH = config
            module.CHANGELOG_PATH = changelog

            self.assertEqual(module.set_version("0.4.3", 1), "0.4.3-1")
            self.assertEqual(module.read_current_version(), "0.4.3-1")
            updated_changelog = changelog.read_text(encoding="utf-8")
            self.assertIn("## 0.4.3-1", updated_changelog)
            self.assertIn("- 修复了一些已知内容。", updated_changelog)
            self.assertNotIn("HA Bridge 主程序升级至", updated_changelog)
            module.check_version("0.4.3", 1)

    def test_version_policy_rejects_invalid_base_or_revision(self) -> None:
        module = self.load_version_module()
        with self.assertRaises(SystemExit):
            module.addon_version("0.4.10", 1)
        with self.assertRaises(SystemExit):
            module.addon_version("0.4.3", 0)

    def test_compatibility_dockerfile_never_copies_product_source(self) -> None:
        source = (ROOT / "release" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("FROM ${BASE_IMAGE}", source)
        self.assertIn("USER root", source)
        self.assertNotIn("COPY ", source)
        self.assertNotIn("ADD ", source)

    def test_publish_order_verifies_image_before_store_version(self) -> None:
        source = (ROOT / "release" / "publish_addon_release.sh").read_text(encoding="utf-8")
        self.assertLess(source.index("docker buildx build"), source.index("verify_addon_upgrade.sh"))
        self.assertLess(source.index("verify_addon_upgrade.sh"), source.index("release/version.py set"))
        self.assertLess(source.index("release/version.py set"), source.index("git push --atomic"))


if __name__ == "__main__":
    unittest.main()
