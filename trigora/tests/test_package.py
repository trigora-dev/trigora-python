from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
CLIENT = PACKAGE.parent / "trigora-client"


def wheel_command(output: Path, project: Path) -> list[str]:
    probe = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    version = probe.stdout.split()[1] if len(probe.stdout.split()) > 1 else "0"
    major = int(version.split(".", maxsplit=1)[0])
    if major >= 23:
        return [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(output), str(project)]
    venv = output / "build-venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    pip = venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    subprocess.run([str(pip), "install", "-U", "pip", "setuptools", "wheel"], check=True)
    return [str(pip), "wheel", "--no-deps", "-w", str(output), str(project)]


def build_wheel(project: Path) -> tuple[Path, list[str]]:
    tmp = Path(tempfile.mkdtemp())
    result = subprocess.run(
        wheel_command(tmp, project),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    wheels = list(tmp.glob("*.whl"))
    if len(wheels) != 1:
        raise AssertionError(result.stdout + result.stderr)
    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
    return wheels[0], names


class PackageBoundaryTests(unittest.TestCase):
    def test_authoring_wheel_is_pure_and_depends_on_the_cli(self) -> None:
        wheel, names = build_wheel(PACKAGE)
        self.assertIn("py3-none-any", wheel.name)
        self.assertFalse(any(name.endswith(("/trigora", "/trigora.exe")) for name in names), names)
        self.assertFalse(any("_vendor/" in name for name in names), names)
        metadata = metadata_text(wheel)
        self.assertIn("Requires-Dist: tcc-engine==26.10.0", metadata)
        self.assertIn("Requires-Dist: trigora-cli==1.0.0", metadata)

    def test_client_wheel_has_no_cli_or_compiler(self) -> None:
        wheel, names = build_wheel(CLIENT)
        self.assertIn("py3-none-any", wheel.name)
        self.assertFalse(any(name.endswith(("/trigora", "/trigora.exe")) for name in names), names)
        requires = [
            line for line in metadata_text(wheel).splitlines() if line.startswith("Requires-Dist:")
        ]
        self.assertEqual(requires, [])


def metadata_text(wheel: Path) -> str:
    with zipfile.ZipFile(wheel) as archive:
        name = next(item for item in archive.namelist() if item.endswith("METADATA"))
        return archive.read(name).decode()


if __name__ == "__main__":
    unittest.main()
