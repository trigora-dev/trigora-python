import unittest

from trigora import effect, gather, invoke, program, race, sleep, wait_for_event


class AuthoringTests(unittest.TestCase):
    def test_primitives_require_the_runtime(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "trigora dev"):
            effect("generate", lambda: 42)
        with self.assertRaisesRegex(RuntimeError, "trigora dev"):
            wait_for_event("approved")
        with self.assertRaisesRegex(RuntimeError, "trigora dev"):
            sleep("1s")
        with self.assertRaisesRegex(RuntimeError, "trigora dev"):
            invoke("child", {"n": 1})
        with self.assertRaisesRegex(RuntimeError, "trigora dev"):
            gather(1)
        with self.assertRaisesRegex(RuntimeError, "trigora dev"):
            race(1)

    def test_gather_and_race_reject_an_empty_call(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            gather()
        with self.assertRaisesRegex(ValueError, "at least one"):
            race()

    def test_program_returns_the_same_function(self) -> None:
        async def approval():
            return 1

        self.assertIs(program(approval), approval)
        self.assertEqual(program(approval).__name__, "approval")

    def test_effect_rejects_an_empty_key(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty"):
            effect("  ", lambda: 1)


if __name__ == "__main__":
    unittest.main()
