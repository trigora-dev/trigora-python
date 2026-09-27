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


def cli_source() -> Path:
    override = os.environ.get("TRIGORA_CLI_SRC")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3] / "trigora" / "python" / "trigora-cli"


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


def write_engine_stub(root: Path) -> None:
    project = root / "tcc-engine"
    package = project / "src" / "tcc_engine"
    package.mkdir(parents=True)
    (project / "pyproject.toml").write_text(
        textwrap.dedent(
            """\
            [build-system]
            requires = ["setuptools>=68"]
            build-backend = "setuptools.build_meta"

            [project]
            name = "tcc-engine"
            version = "0.1.0"

            [tool.setuptools.packages.find]
            where = ["src"]
            """
        )
    )
    (package / "__init__.py").write_text('PACKAGE_VERSION = "0.1.0"\n')


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_trigora(venv: Path) -> Path:
    return venv / ("Scripts/trigora.exe" if os.name == "nt" else "bin/trigora")


class LocalInstallTests(unittest.TestCase):
    def test_authoring_install_pulls_the_cli_distribution(self) -> None:
        source = cli_source()
        self.assertTrue((source / "pyproject.toml").is_file(), source)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wheels = root / "wheels"
            wheels.mkdir()
            vendor = source / "src" / "trigora_cli" / "_vendor"
            created: list[Path] = []
            vendor.mkdir(parents=True, exist_ok=True)
            names = (
                ("trigora.exe", "trigora-local.exe")
                if os.name == "nt"
                else ("trigora", "trigora-local")
            )
            try:
                for name in names:
                    path = vendor / name
                    if path.exists():
                        continue
                    if name.startswith("trigora-local"):
                        path.write_text("#!/bin/sh\nexit 0\n")
                    else:
                        path.write_text(
                            "#!/bin/sh\n"
                            "printf '%s\\n' \"$1\"\n"
                            "printf 'helper=%s\\n' \"${TRIGORA_NODE_HELPER-unset}\"\n"
                        )
                    path.chmod(0o755)
                    created.append(path)
                pip = pip_bin(root)
                write_engine_stub(root)
                wheel(pip, root / "tcc-engine", wheels)
                wheel(pip, source, wheels)
                wheel(pip, PACKAGE, wheels)
                cli_wheel = next(wheels.glob("trigora_cli-*.whl"))
                authoring_wheel = next(wheels.glob("trigora-0.9.0-*.whl"))
                self.assertNotIn("none-any", cli_wheel.name)
                self.assertIn("py3-none-any", authoring_wheel.name)

                install = root / "install"
                subprocess.run([sys.executable, "-m", "venv", str(install)], check=True)
                pip_install = venv_python(install).parent / (
                    "pip.exe" if os.name == "nt" else "pip"
                )
                subprocess.run([str(pip_install), "install", "-U", "pip"], check=True)
                isolated = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
                result = subprocess.run(
                    [
                        str(pip_install),
                        "install",
                        "--no-cache-dir",
                        "--no-index",
                        "--find-links",
                        str(wheels),
                        "trigora==0.9.0",
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
                self.assertIn("trigora_cli", script.read_text())
                env = os.environ.copy()
                env.pop("TRIGORA_BIN", None)
                env.pop("TRIGORA_NODE_HELPER", None)
                env.pop("TRIGORA_LOCAL_BIN", None)
                env.pop("PYTHONPATH", None)
                launched = subprocess.run(
                    [str(script), "dev"],
                    check=False,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                self.assertEqual(launched.returncode, 0, launched.stderr)
                self.assertIn("dev", launched.stdout)
                self.assertIn("helper=unset", launched.stdout)
            finally:
                for path in created:
                    path.unlink(missing_ok=True)
                if vendor.is_dir() and not any(vendor.iterdir()):
                    vendor.rmdir()

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
                    "trigora-client==0.9.0",
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
        self.assertTrue(next(directory.glob("trigora-0*.whl"), None), directory)
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
                    "trigora==0.9.0",
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
            self.assertIn("0.9.0", version.stdout + version.stderr)
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
                    "trigora-client==0.9.0",
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
