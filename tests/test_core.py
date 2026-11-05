import json
import unittest
from pathlib import Path

from backend.agents.director import direct_scenes
from backend.agents.scriptwriter import interpret_prompt
from backend.agents.validator import ValidationFailure, parse_project_with_retries
from backend.pipeline.generate import build_project, resolution_for
from backend.pipeline.render import doctor_rendering
from backend.schemas import Project
from backend.tools.timing_tools import frames_to_seconds, reconcile_duration, seconds_to_frames
from backend.audio.sfx_library import SfxLibrary


class VectorForgeTests(unittest.TestCase):
    def test_prompt_interpretation(self):
        plan = interpret_prompt("Explain indexing in 30 seconds for beginners, portrait and energetic")
        self.assertEqual(plan["duration_second"], 30)
        self.assertEqual(plan["format"], "9:16")
        self.assertEqual(plan["audience"], "beginners")

    def test_frame_conversion(self):
        self.assertEqual(seconds_to_frames(1.0, 30), 30)
        self.assertEqual(frames_to_seconds(45, 30), 1.5)

    def test_duration_reconciliation(self):
        result = reconcile_duration(40, 30)
        self.assertGreaterEqual(result.speed, 1.0)
        self.assertTrue(result.regenerated)

    def test_deterministic_fixture_without_llm(self):
        project = build_project("Explain how database indexing works in 30 seconds", generate_audio=False, aspect="16:9")
        self.assertEqual(project.resolution.width, 1920)
        self.assertEqual(project.resolution.height, 1080)
        self.assertGreaterEqual(len(project.scenes), 4)
        Project.model_validate(project.model_dump())

    def test_sfx_empty_catalogue_is_valid(self):
        library = SfxLibrary(Path("assets/sfx/manifest.json"))
        self.assertEqual(library.assets, [])
        self.assertIsNone(library.match("whoosh"))

    def test_portrait_layout_is_not_a_crop(self):
        portrait = resolution_for("9:16")
        landscape = resolution_for("16:9")
        self.assertEqual((portrait.width, portrait.height), (1080, 1920))
        self.assertEqual((landscape.width, landscape.height), (1920, 1080))

    def test_invalid_llm_payload_has_actionable_failure(self):
        with self.assertRaises(ValidationFailure) as error:
            parse_project_with_retries({"script": "not a project"}, attempts=2)
        self.assertIn("after 2 attempts", str(error.exception))

    def test_render_configuration_is_discoverable(self):
        status = doctor_rendering()
        self.assertIn("remotion_config", status)
        self.assertTrue(status["remotion_config"])


if __name__ == "__main__":
    unittest.main()

