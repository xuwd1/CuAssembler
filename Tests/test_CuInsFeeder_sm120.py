# -*- coding: utf-8 -*-
''' Portable unittest for the custom-sm120 CuInsFeeder entry layout.

    Covers the entry script (import side effects, main dispatch, full-iteration
    and trans wrappers with finally-close) plus optional integration over the
    two isolated SM120 fixtures cut from existing text dumps. Structural text
    tests only: no extraction/cuobjdump is run, no giant bulk dumps are read,
    and no GPU timing/scheduling claims are made.
'''
import importlib.util
import io
import pathlib
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

import CuAsm
from CuAsm.CuSMVersion import CuSMVersion
from CuAsm.CuInsFeeder import CuInsFeeder
from CuAsm.CuControlCode import CuControlCode

_ENTRY_PATH = _REPO_ROOT / 'custom-sm120' / 'CuInsFeeder' / 'CuInsFeeder_test.py'
_SASS_DIR = _REPO_ROOT / 'custom-sm120' / 'sass'
_SAMPLES = [_SASS_DIR / 'isolated_hmma_kernel_1.sass',
            _SASS_DIR / 'isolated_imma_kernel_1.sass']
_TENSOR_OPS = {'isolated_hmma_kernel_1': 'HMMA.16816.F32.BF16',
               'isolated_imma_kernel_1': 'IMMA.16832.S8.S8'}

CTRL_POS = 105                    # SM7x/8x control-field position shared by SM120
CTRL_MASK = 0x1ffff << CTRL_POS

# Independent extractors (not reusing feeder internals) for cross-checking.
R_INS = re.compile(r'^\s*/\*([0-9a-f]+)\*/\s*(.*?;)\s*/\* (0x[0-9a-f]{16}) \*/')
R_CODE = re.compile(r'^\s*/\* (0x[0-9a-f]{16}) \*/')
R_PREFIX = re.compile(r'^\[([^\]]+)\][^\S\n]+/\*([0-9a-f]+)\*/')


def _load_entry():
    ''' Load the entry script as a module without running main().'''
    spec = importlib.util.spec_from_file_location('sm120_feeder_entry', _ENTRY_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_raw_pairs(path):
    ''' Independently extract (addr, asm, raw128) for every instruction.'''
    lines = path.read_text().splitlines()
    pairs, i = [], 0
    while i < len(lines):
        m = R_INS.match(lines[i])
        if m:
            hi = R_CODE.match(lines[i + 1])
            assert hi is not None, f'missing second code word after line {i+1} of {path}'
            pairs.append((int(m.group(1), 16), m.group(2),
                          int(m.group(3), 16) | (int(hi.group(1), 16) << 64)))
            i += 2
        else:
            i += 1
    return pairs


class TestEntryImport(unittest.TestCase):
    def test_import_no_output_no_mkdir(self):
        buf = io.StringIO()
        with mock.patch.object(pathlib.Path, 'mkdir') as m_mkdir, redirect_stdout(buf):
            mod = _load_entry()
        self.assertEqual(buf.getvalue(), '')
        m_mkdir.assert_not_called()
        for p in (mod.SM120_ISOLATED_HMMA_KERNEL_1_SASS_PATH,
                  mod.SM120_ISOLATED_IMMA_KERNEL_1_SASS_PATH):
            self.assertTrue(p.exists())


class TestEntryCalls(unittest.TestCase):
    def setUp(self):
        self.mod = _load_entry()

    def test_main_processes_both_samples(self):
        with mock.patch.object(self.mod, 'try_CuInsFeeder') as m_feed, \
             mock.patch.object(self.mod, 'try_CuInsFeeder_trans') as m_trans:
            self.mod.main()
        expected = [mock.call(p) for p in (self.mod.SM120_ISOLATED_HMMA_KERNEL_1_SASS_PATH,
                                           self.mod.SM120_ISOLATED_IMMA_KERNEL_1_SASS_PATH)]
        self.assertEqual(m_feed.call_args_list, expected)
        self.assertEqual(m_trans.call_args_list, expected)

    def test_try_feeder_full_iteration_and_close(self):
        feeder = mock.MagicMock()
        feeder.__iter__.return_value = iter([(0x0, 123, 'LDC R1 ;', 0x712),
                                             (0x10, 456, 'IMMA x ;', 0x7f1)])
        with mock.patch.object(self.mod.CuAsm, 'CuInsFeeder', return_value=feeder):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.mod.try_CuInsFeeder(_SAMPLES[0])
        out = buf.getvalue()
        self.assertIn('total instructions: 2', out)
        for s in ('addr: 0', 'code: 123', 'asm: LDC R1 ;', 'ctrlcode: 1810'):
            self.assertIn(s, out)
        feeder.close.assert_called_once()

    def test_try_feeder_exception_still_closes(self):
        def gen():
            yield (0x0, 1, 'A ;', 2)
            raise RuntimeError('boom')
        feeder = mock.MagicMock()
        feeder.__iter__.return_value = gen()
        with mock.patch.object(self.mod.CuAsm, 'CuInsFeeder', return_value=feeder):
            with redirect_stdout(io.StringIO()):
                self.assertRaises(RuntimeError, self.mod.try_CuInsFeeder, _SAMPLES[0])
        feeder.close.assert_called_once()

    def test_try_trans_creates_dir_and_calls(self):
        with tempfile.TemporaryDirectory() as td:
            outdir = pathlib.Path(td) / 'trans_output'
            feeder = mock.MagicMock()
            with mock.patch.object(self.mod, '_TRANS_OUTPUT_DIR', outdir), \
                 mock.patch.object(self.mod.CuAsm, 'CuInsFeeder', return_value=feeder):
                with redirect_stdout(io.StringIO()):
                    self.mod.try_CuInsFeeder_trans(_SAMPLES[0])
            self.assertTrue(outdir.is_dir())
            feeder.trans.assert_called_once_with(
                str(outdir / (_SAMPLES[0].stem + '.sass.control')),
                custom=True, res_usage_dict={})
            feeder.close.assert_called_once()

    def test_try_trans_exception_still_closes(self):
        with tempfile.TemporaryDirectory() as td:
            feeder = mock.MagicMock()
            feeder.trans.side_effect = RuntimeError('boom')
            with mock.patch.object(self.mod, '_TRANS_OUTPUT_DIR', pathlib.Path(td) / 'trans_output'), \
                 mock.patch.object(self.mod.CuAsm, 'CuInsFeeder', return_value=feeder):
                with redirect_stdout(io.StringIO()):
                    self.assertRaises(RuntimeError, self.mod.try_CuInsFeeder_trans, _SAMPLES[0])
            feeder.close.assert_called_once()


@unittest.skipUnless(all(p.exists() for p in _SAMPLES),
                     'isolated SM120 sample dumps not present')
class TestRealSamples(unittest.TestCase):
    def test_iteration_and_reconstruction(self):
        for path in _SAMPLES:
            pairs = _parse_raw_pairs(path)
            self.assertTrue(pairs)
            feeder = CuInsFeeder(str(path))
            tuples = list(feeder)
            self.assertEqual(feeder.CurrArch.getVersionNumber(), 120)
            self.assertEqual(len(tuples), len(pairs))
            for (addr, code, asm, ctrl), (eaddr, easm, raw) in zip(tuples, pairs):
                self.assertEqual((addr, asm, code, ctrl),
                                 (eaddr, easm, raw & ~CTRL_MASK, (raw >> CTRL_POS) & 0x1ffff))
                self.assertEqual(CuControlCode.encode(CuControlCode.decode(ctrl)), ctrl)
            bs = b''.join(r.to_bytes(16, 'little') for _, _, r in pairs)
            ctrls, inss = CuSMVersion(120).splitCtrlCodeFromBytes(bs)
            self.assertEqual((inss, ctrls), ([t[1] for t in tuples], [t[3] for t in tuples]))
            self.assertEqual(CuSMVersion(120).mergeCtrlCodes(inss, ctrls), bs)

    def test_trans_ordered_prefixes_and_headers(self):
        for path in _SAMPLES:
            expected = [(a, CuControlCode.decode((r >> CTRL_POS) & 0x1ffff))
                        for a, _, r in _parse_raw_pairs(path)]
            header = next(line for line in path.read_text().splitlines()
                          if line.lstrip().startswith('.headerflags'))
            for kwargs in ({}, {'custom': True, 'res_usage_dict': {}}):
                feeder = CuInsFeeder(str(path))
                out = io.StringIO()
                feeder.trans(out, **kwargs)
                text = out.getvalue()
                got = [(int(m.group(2), 16), m.group(1))
                       for m in (R_PREFIX.match(l) for l in text.splitlines()) if m]
                self.assertEqual(got, expected)
                # frozen fixture header (incl. the unrecognized:0 form) survives translation
                self.assertIn(header, text)
                self.assertIn(_TENSOR_OPS[path.stem], text)


if __name__ == '__main__':
    unittest.main()
