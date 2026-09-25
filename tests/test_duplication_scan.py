"""S-42 advisory scan fixtures; no repository state is changed."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import duplication_scan as scan


class DuplicationScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = patch.object(scan, 'REPO', self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def function(self, name, lines):
        return f'def {name}():\n' + ''.join(f'    x = {i}\n' for i in range(lines))

    def test_duplicates_threshold_and_shapes(self):
        self.write('aion_core/a.py', self.function('validate_a', 16))
        self.write('bridges/b.py', self.function('validate_b', 16))
        self.write('scripts/c.py', self.function('retry_a', 15))
        self.write('scripts/d.py', self.function('retry_b', 15))
        report = scan.run_scan()
        self.assertEqual(len(report['duplicate_functions']), 1)
        self.assertEqual(len(report['duplicate_functions'][0]), 2)
        self.assertEqual(set(report['name_pattern_shapes']), {'validation', 'retry_backoff'})

    def test_four_independent_exclusions(self):
        for name in ('orphan', 'wired', 'imported', 'tested', 'manifested', 'documented', 'planned'):
            self.write(f'aion_core/{name}.py', 'VALUE = 1\n')
        self.write('aion_core/cli.py', 'MODULE = "wired"\n')
        self.write('integrations/consumer.py', 'from aion_core import imported\n')
        self.write('tests/helper.py', 'from aion_core import tested\n')
        self.write('manifest.json', '{"module": "manifested"}')
        self.write('docs/guide.md', '`documented`')
        self.write('.lucy/plan.md', '`planned`')
        rows = {r['file']: r for r in scan.dead_weight_modules()}
        self.assertTrue(rows['aion_core/orphan.py']['candidate'])
        for name in ('wired', 'imported', 'tested', 'manifested', 'documented', 'planned'):
            self.assertFalse(rows[f'aion_core/{name}.py']['candidate'], name)
        text = scan.render_dead_weight_markdown(scan.run_scan())
        line = next(line for line in text.splitlines() if line.startswith('- `aion_core/orphan.py`'))
        for check in ('no importers', 'no CLI wiring', 'no test import', 'no manifest/.lucy/docs reference'):
            self.assertIn(check, line)

    def test_docs_and_existing_ground_truth(self):
        self.write('docs/a.md', '[broken](missing.py)\n[ok](exists.py)\n[web](https://example.org)')
        self.write('docs/exists.py', '')
        self.write('.lucy/planning/old.md', '# SUPERSEDED by new plan\n')
        for name in scan.KNOWN_STALE_PLANNING_DOCS:
            self.write(name, '# Historical plan\n')
        report = scan.run_scan()
        self.assertEqual(report['dead_links']['findings'], [{'doc': 'docs/a.md', 'link': 'missing.py'}])
        self.assertEqual(len(report['superseded_docs']), 5)
        self.assertIn('missing.py', scan.render_dead_weight_markdown(report))

    def test_reports_do_not_become_inputs_and_cli_is_deterministic(self):
        self.write('aion_core/orphan.py', 'VALUE = 1\n')
        output = self.root / '.lucy/evidence'
        args = ['--root', str(self.root), '--write-evidence', str(output), '--json']
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(args), 0)
        before = {p.name: p.read_bytes() for p in output.iterdir()}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(scan.main(args), 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_private_and_symlinked_files_are_excluded(self):
        self.write('private_state/hidden.py', 'import orphan\n')
        self.write('secrets/hidden.md', '[bad](missing)')
        self.write('aion_core/orphan.py', 'VALUE = 1\n')
        (self.root / 'docs').symlink_to(self.root / 'secrets', target_is_directory=True)
        report = scan.run_scan()
        self.assertTrue(report['dead_weight_modules'][0]['candidate'])
        self.assertEqual(report['dead_links']['findings'], [])


if __name__ == '__main__':
    unittest.main()
