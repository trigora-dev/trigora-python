from __future__ import annotations

import unittest

try:
    from tcc_engine import CompileError, compile
except ImportError:
    compile = None
    CompileError = Exception


@unittest.skipUnless(compile, "tcc_engine is not installed")
class ProgramEntryTests(unittest.TestCase):
    def test_program_marker_compiles(self) -> None:
        artifact = compile(
            "from trigora import program\n@program\nasync def approval():\n    return 1\n",
            filename="approval.py",
        )
        self.assertEqual(artifact["program"]["functions"][0]["name"], "approval")

    def test_aliased_marker_compiles(self) -> None:
        artifact = compile(
            "from trigora import program as marker\n@marker\nasync def approval():\n    return 1\n",
            filename="alias.py",
        )
        self.assertEqual(artifact["program"]["functions"][0]["name"], "approval")

    def test_bare_run_is_rejected(self) -> None:
        with self.assertRaises(CompileError):
            compile("async def run():\n    return 1\n", filename="run.py")

    def test_gather_and_race_compile(self) -> None:
        source = (
            "from trigora import gather, program, race, sleep, wait_for_event\n"
            "@program\n"
            "async def approval():\n"
            "    both = await gather(wait_for_event('left'), sleep(1))\n"
            "    first = await race(wait_for_event('right'), sleep(2))\n"
            "    return {'both': both, 'first': first}\n"
        )
        artifact = compile(source, filename="joins.py")
        self.assertEqual(artifact["program"]["functions"][0]["name"], "approval")

    def test_two_program_functions_are_rejected(self) -> None:
        source = (
            "from trigora import program\n"
            "@program\nasync def one():\n    return 1\n"
            "@program\nasync def two():\n    return 2\n"
        )
        with self.assertRaises(CompileError):
            compile(source, filename="two.py")


if __name__ == "__main__":
    unittest.main()
