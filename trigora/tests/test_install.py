from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
CLIENT = PACKAGE.parent / "trigora-client"


def pip_bin(work: Path) -> Path:
    venv = work / "tooling"
    pip = venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
    if not pip.is_file():
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
        subprocess.run([str(pip), "install", "-U", "pip", "setuptools", "wheel"], check=True)
    return pip


def wheel(pip: Path, project: Path, output: Path) -> None:
    result = subprocess.run(
        [str(pip), "wheel", "--no-deps", "-w", str(output), str(project)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_trigora(venv: Path) -> Path:
    return venv / ("Scripts/trigora.exe" if os.name == "nt" else "bin/trigora")


class LocalInstallTests(unittest.TestCase):
    def test_authoring_install_pulls_the_published_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheels = root / "wheels"
            wheels.mkdir()
            pip = pip_bin(root)
            wheel(pip, PACKAGE, wheels)
            authoring_wheel = next(wheels.glob("trigora-1.0.1-*.whl"))
            self.assertIn("py3-none-any", authoring_wheel.name)

            install = root / "install"
            subprocess.run([sys.executable, "-m", "venv", str(install)], check=True)
            pip_install = venv_python(install).parent / ("pip.exe" if os.name == "nt" else "pip")
            subprocess.run([str(pip_install), "install", "-U", "pip"], check=True)
            isolated = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
            result = subprocess.run(
                [
                    str(pip_install),
                    "install",
                    "--no-cache-dir",
                    "--find-links",
                    str(wheels),
                    "trigora==1.0.1",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("trigora-cli", result.stdout + result.stderr)
            check = subprocess.run(
                [
                    str(venv_python(install)),
                    "-c",
                    textwrap.dedent(
                        """\
                        import trigora
                        import trigora_cli
                        from pathlib import Path
                        authoring = Path(trigora.__file__).resolve().as_posix()
                        cli = Path(trigora_cli.__file__).resolve().as_posix()
                        assert authoring.endswith("site-packages/trigora/__init__.py"), authoring
                        assert cli.endswith("site-packages/trigora_cli/__init__.py"), cli
                        assert trigora.program is not None
                        print("imports-ok")
                        """
                    ),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(check.returncode, 0, check.stderr + result.stdout + result.stderr)
            self.assertIn("imports-ok", check.stdout)
            script = venv_trigora(install)
            self.assertTrue(script.is_file(), script)
            version = subprocess.run(
                [str(script), "--version"],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(version.returncode, 0, version.stderr)
            self.assertIn("1.0.2", version.stdout + version.stderr)

    def test_client_install_has_no_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheels = root / "wheels"
            wheels.mkdir()
            pip = pip_bin(root)
            wheel(pip, CLIENT, wheels)
            install = root / "install"
            subprocess.run([sys.executable, "-m", "venv", str(install)], check=True)
            pip_install = venv_python(install).parent / ("pip.exe" if os.name == "nt" else "pip")
            subprocess.run([str(pip_install), "install", "-U", "pip"], check=True)
            result = subprocess.run(
                [
                    str(pip_install),
                    "install",
                    "--no-index",
                    "--find-links",
                    str(wheels),
                    "trigora-client==1.0.1",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(venv_trigora(install).exists())
            check = subprocess.run(
                [
                    str(venv_python(install)),
                    "-c",
                    (
                        "import trigora_client\n"
                        "import importlib.util\n"
                        "assert importlib.util.find_spec('trigora') is None\n"
                        "assert importlib.util.find_spec('trigora_cli') is None\n"
                        "assert importlib.util.find_spec('tcc_engine') is None\n"
                    ),
                ],
                check=False,
                capture_output=True,
                text=True,
                env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
            )
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_release_directory_of_real_wheels(self) -> None:
        wheels = os.environ.get("TRIGORA_RELEASE_WHEELS")
        if not wheels:
            self.skipTest("TRIGORA_RELEASE_WHEELS is unset")
        directory = Path(wheels)
        self.assertTrue(next(directory.glob("tcc_engine-*.whl"), None), directory)
        self.assertTrue(next(directory.glob("trigora_cli-*.whl"), None), directory)
        self.assertTrue(next(directory.glob("trigora-1.0.1-*.whl"), None), directory)
        self.assertTrue(next(directory.glob("trigora_client-*.whl"), None), directory)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install = root / "install"
            subprocess.run([sys.executable, "-m", "venv", str(install)], check=True)
            pip_install = venv_python(install).parent / ("pip.exe" if os.name == "nt" else "pip")
            isolated = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
            result = subprocess.run(
                [
                    str(pip_install),
                    "install",
                    "--no-index",
                    "--find-links",
                    str(directory),
                    "trigora==1.0.1",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            check = subprocess.run(
                [
                    str(venv_python(install)),
                    "-c",
                    "import trigora, trigora_cli\n",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(check.returncode, 0, check.stderr)
            version = subprocess.run(
                [str(venv_trigora(install)), "--version"],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(version.returncode, 0, version.stderr)
            self.assertIn("1.0.2", version.stdout + version.stderr)
            client = root / "client"
            subprocess.run([sys.executable, "-m", "venv", str(client)], check=True)
            client_pip = venv_python(client).parent / ("pip.exe" if os.name == "nt" else "pip")
            client_install = subprocess.run(
                [
                    str(client_pip),
                    "install",
                    "--no-index",
                    "--find-links",
                    str(directory),
                    "trigora-client==1.0.1",
                ],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
            )
            self.assertEqual(client_install.returncode, 0, client_install.stderr)
            isolated_check = subprocess.run(
                [
                    str(venv_python(client)),
                    "-c",
                    (
                        "import trigora_client\n"
                        "import importlib.util as u\n"
                        "assert u.find_spec('trigora') is None\n"
                        "assert u.find_spec('trigora_cli') is None\n"
                        "assert u.find_spec('tcc_engine') is None\n"
                    ),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=isolated,
                cwd=client,
            )
            self.assertEqual(isolated_check.returncode, 0, isolated_check.stderr)


if __name__ == "__main__":
    unittest.main()
