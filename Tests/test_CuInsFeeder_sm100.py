# -*- coding: utf-8 -*-
''' Portable unittest for narrow SM100 ('BlackwellUltra') support in CuInsFeeder.

    These are STRUCTURAL tests: they verify that SM100 two-word 128-bit SASS
    dumps are fed/split/merged through the same 17-bit control-field layout
    used for SM7x/8x (and shared by SM90/SM120), and that trans output is
    consistent with it. They do NOT prove hardware scheduling semantics of
    the control bits, nor full SM100 instruction parse/assemble support.
    The SM101/SM110 cases are routing-compatibility checks on synthetic
    headers (they reuse the SM100 feeder path), not validation of actual
    SM101/SM110 binaries.
'''
import pathlib
import re
import sys
import unittest
from io import StringIO

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from CuAsm.CuSMVersion import CuSMVersion
from CuAsm.CuInsFeeder import CuInsFeeder
from CuAsm.CuControlCode import CuControlCode

CTRL_POS = 105                    # bit position of the control field
CTRL_MASK = 0x1ffff << CTRL_POS   # bits [121:105] of the 128-bit word

# Golden (low64, high64, ctrl, decoded ctrl string) observed in the
# isolated SM100 sample dumps; the decode strings are structural literals.
GOLDEN_PAIRS = [
    # isolated_utcimma_kernel_1.sass: LDC R1, c[0x0][0x37c] ;
    (0x0000df00ff017b82, 0x000e240000000800, 0x0712, 'B------:R-:W0:-:S02'),
    # isolated_hmma_kernel_1.sass:    LDC R1, c[0x0][0x37c] ;
    (0x0000df00ff017b82, 0x000fe20000000800, 0x07f1, 'B------:R-:W-:-:S01'),
    # isolated_utcimma_kernel_1.sass: UTCIMMA gdesc[UR26], ... UP2 ;
    (0x00ff0e181a0075ea, 0x0001e40009000113, 0x00f2, 'B------:R0:W-:-:S02'),
    # isolated_hmma_kernel_1.sass:    HMMA.16816.F32.BF16 R4, R68.reuse, R72, R4 ;
    (0x000000484404723c, 0x052fe20000041804, 0x97f1, 'B-1--4-:R-:W-:-:S01'),
]
GOLDEN_ASMS = [
    'LDC R1, c[0x0][0x37c] ;',
    'LDC R1, c[0x0][0x37c] ;',
    'UTCIMMA gdesc[UR26], gdesc[UR24], tmem[UR19], tmem[UR14], idesc[UR15], UP2 ;',
    'HMMA.16816.F32.BF16 R4, R68.reuse, R72, R4 ;',
]
GOLDEN_ADDRS = [0x0000, 0x0010, 0x2ac0, 0x2f20]
BOUNDARY_CTRLS = [0, 0x7e0, 0x7f1, 0x712, 0x97f1, 0x1ffff]

FUNC = '_Z5ktestPmPi'


def _header(v, accel=True):
    pre = 'EF_CUDA_ACCELERATORS ' if accel else ''
    return '\t.headerflags\t@"%sEF_CUDA_SM%d EF_CUDA_VIRTUAL_SM(EF_CUDA_SM%d)"\n' % (pre, v, v)


H_100_ACCEL = _header(100)
H_100_PLAIN = _header(100, accel=False)
H_80  = _header(80, accel=False)
H_120 = _header(120, accel=False)


def _ins_line(addr, asm, low, high):
    return ('        /*%04x*/                   %s   /* 0x%016x */\n'
            '                                                                                          /* 0x%016x */\n'
            % (addr, asm, low, high))


def _func_block(func, header, body):
    return '\t\tFunction : %s\n%s%s' % (func, header, body)


def _sm_sass(v):
    return _func_block(FUNC, _header(v),
        ''.join(_ins_line(a, s, lo, hi) for a, s, (lo, hi, _, _)
                in zip(GOLDEN_ADDRS, GOLDEN_ASMS, GOLDEN_PAIRS))) + '\t\t..........\n'


SM100_SASS = _sm_sass(100)

MIXED_SASS = (
    _func_block('func_sm80', H_80, _ins_line(0x0000, 'UMOV UR4, URZ ;', 0x000000ff00047c82, 0x000fe20000000000)) +
    _func_block('func_sm100', H_100_PLAIN, _ins_line(0x0000, GOLDEN_ASMS[0], *GOLDEN_PAIRS[0][:2])) +
    _func_block('func_sm101', _header(101, accel=False), _ins_line(0x0000, GOLDEN_ASMS[0], *GOLDEN_PAIRS[0][:2])) +
    _func_block('func_sm110', _header(110, accel=False), _ins_line(0x0000, GOLDEN_ASMS[0], *GOLDEN_PAIRS[0][:2])) +
    _func_block('func_sm120', H_120, _ins_line(0x0000, 'UMOV UR4, URZ ;', 0x000000ff00047c82, 0x000fe20000000000)))

SAMPLE_DIR = _REPO_ROOT / 'custom-sm100' / 'sass'
SAMPLES = [SAMPLE_DIR / 'isolated_hmma_kernel_1.sass',
           SAMPLE_DIR / 'isolated_utcimma_kernel_1.sass']

# Independent extractors (not reusing feeder internals) for cross-checking.
R_INS = re.compile(r'^\s*/\*([0-9a-f]+)\*/\s*(.*?;)\s*/\* (0x[0-9a-f]{16}) \*/')
R_CODE = re.compile(r'^\s*/\* (0x[0-9a-f]{16}) \*/')
R_CTRL_PREFIX = re.compile(r'^\[([^\]]+)\][^\S\n]+/\*([0-9a-f]+)\*/', re.M)


def _parse_raw_pairs(path):
    ''' Independently extract (addr, asm, raw128) for every instruction.'''
    lines = path.read_text().splitlines()
    pairs, i = [], 0
    while i < len(lines):
        m = R_INS.match(lines[i])
        if m:
            hi = R_CODE.match(lines[i + 1])
            assert hi is not None, f'missing second code word after line {i+1} of {path}'
            raw = int(m.group(3), 16) | (int(hi.group(1), 16) << 64)
            pairs.append((int(m.group(1), 16), m.group(2), raw))
            i += 2
        else:
            i += 1
    return pairs


def _trans_str(sass, **kwargs):
    feeder = CuInsFeeder(StringIO(sass))
    out = StringIO()
    feeder.trans(out, **kwargs)
    return out.getvalue()


class TestSM100Version(unittest.TestCase):
    def test_aliases(self):
        for v in (100, 101, 110):
            base = CuSMVersion(v)
            for alias in (v, str(v), 'sm_%d' % v, 'SM%d' % v):
                self.assertIs(CuSMVersion(alias), base)
            self.assertEqual(base.getVersionNumber(), v)
            self.assertEqual(base.getMajor(), v // 10)

    def test_code_names(self):
        self.assertEqual(CuSMVersion.SMCodeNameDict[100], 'BlackwellUltra')
        self.assertEqual(CuSMVersion.SMCodeNameDict[101], 'BlackwellThorOld')
        self.assertEqual(CuSMVersion.SMCodeNameDict[110], 'BlackwellThor')
        self.assertEqual(CuSMVersion.SMCodeNameDict[120], 'BlackwellGeforce')

    def test_header_variants_parse_as_version(self):
        for v in (100, 101, 110):
            for accel in (True, False):
                sass = _func_block(FUNC, _header(v, accel),
                                   _ins_line(0x0, GOLDEN_ASMS[0], *GOLDEN_PAIRS[0][:2]))
                feeder = CuInsFeeder(StringIO(sass))
                self.assertEqual(len(list(feeder)), 1)
                self.assertEqual(feeder.CurrArch.getVersionNumber(), v)


class TestSM100SplitMerge(unittest.TestCase):
    def test_split_merge_roundtrip_all_arches(self):
        raws = [lo | (hi << 64) for lo, hi, _, _ in GOLDEN_PAIRS]
        base = raws[0] & ~CTRL_MASK
        raws += [base | (c << CTRL_POS) for c in BOUNDARY_CTRLS]
        for v in (80, 90, 100, 101, 110, 120):
            sv = CuSMVersion(v)
            bs = b''.join(r.to_bytes(16, 'little') for r in raws)
            ctrls, inss = sv.splitCtrlCodeFromBytes(bs)
            self.assertEqual(ctrls, [(r >> CTRL_POS) & 0x1ffff for r in raws])
            self.assertEqual(inss, [r & ~CTRL_MASK for r in raws])
            ctrls2, inss2 = sv.splitCtrlCodeFromIntList(raws)
            self.assertEqual((ctrls2, inss2), (ctrls, inss))
            self.assertEqual(sv.mergeCtrlCodes(inss, ctrls), bs)

    def test_posdep_opcodes_match_100(self):
        for v in (101, 110):
            self.assertEqual(CuSMVersion(v).m_PosDepOpcodes, CuSMVersion(100).m_PosDepOpcodes)
            self.assertTrue({'HMMA', 'IMMA'} <= CuSMVersion(v).m_PosDepOpcodes)


class TestSM100Feeder(unittest.TestCase):
    def test_iteration_golden_tuples(self):
        tuples = list(CuInsFeeder(StringIO(SM100_SASS)))
        self.assertEqual(len(tuples), len(GOLDEN_PAIRS))
        for (addr, code, asm, ctrl), (lo, hi, ectrl, estr), easm, eaddr in \
                zip(tuples, GOLDEN_PAIRS, GOLDEN_ASMS, GOLDEN_ADDRS):
            raw = lo | (hi << 64)
            self.assertEqual(addr, eaddr)
            self.assertEqual(asm, easm)
            self.assertEqual(code, raw & ~CTRL_MASK)
            self.assertEqual(ctrl, (raw >> CTRL_POS) & 0x1ffff)
            self.assertEqual(ctrl, ectrl)
            self.assertEqual(CuControlCode.decode(ctrl), estr)
        # reuse field stays outside the control mask and survives in stripped code
        self.assertIn('.reuse', tuples[-1][2])
        self.assertEqual(tuples[-1][1], (GOLDEN_PAIRS[-1][0] | (GOLDEN_PAIRS[-1][1] << 64)) & ~CTRL_MASK)

    def test_iteration_other_versions_same_tuples(self):
        baseline = list(CuInsFeeder(StringIO(SM100_SASS)))
        for v in (101, 110):
            feeder = CuInsFeeder(StringIO(_sm_sass(v)))
            self.assertEqual(list(feeder), baseline)
            self.assertEqual(feeder.CurrArch.getVersionNumber(), v)

    def test_archfilter_and_reiteration(self):
        for v in (100, 101, 110):
            feeder = CuInsFeeder(StringIO(MIXED_SASS), archfilter=v)
            arches, first = set(), []
            for t in feeder:
                arches.add(feeder.CurrArch.getVersionNumber())
                first.append(t)
            self.assertEqual(first, list(feeder))
            self.assertEqual(len(first), 1)
            self.assertEqual(arches, {v})
            self.assertEqual(first[0][0], 0x0000)
            self.assertIn('LDC', first[0][2])


class TestSM100Trans(unittest.TestCase):
    def test_trans_default_and_keep(self):
        for mode in ('none', 'keep'):
            out = _trans_str(SM100_SASS, codeonly_line_mode=mode)
            self.assertIn('EF_CUDA_SM100', out)                     # header preserved
            self.assertIn('Function : ' + FUNC, out)
            prefixes = R_CTRL_PREFIX.findall(out)
            self.assertEqual(len(prefixes), len(GOLDEN_PAIRS))      # every instruction emitted
            for (dec, addr), (_, _, _, estr), eaddr in zip(prefixes, GOLDEN_PAIRS, GOLDEN_ADDRS):
                self.assertEqual(dec, estr)
                self.assertEqual(int(addr, 16), eaddr)
            self.assertEqual('/* 0x000e240000000800 */' in out, mode == 'keep')

    def test_trans_custom(self):
        out = _trans_str(SM100_SASS, custom=True, res_usage_dict={})
        self.assertIn('EF_CUDA_SM100', out)
        self.assertIn('Demangled Function :', out)
        self.assertNotIn('Resource Usage :', out)                    # empty map -> none emitted
        prefixes = R_CTRL_PREFIX.findall(out)
        self.assertEqual(len(prefixes), len(GOLDEN_PAIRS))
        for (dec, _), (_, _, _, estr) in zip(prefixes, GOLDEN_PAIRS):
            self.assertEqual(dec, estr)
        for s in ('UTCIMMA', 'HMMA.16816', '.reuse'):
            self.assertIn(s, out)
        # custom collapses lines and drops the machine-code comments
        self.assertNotIn('/* 0x', out)

    def test_trans_custom_res_usage(self):
        out = _trans_str(SM100_SASS, custom=True, res_usage_dict={FUNC: 'REG:32'})
        self.assertIn('Resource Usage : REG:32', out)

    def test_trans_other_versions_identical(self):
        base_default = _trans_str(SM100_SASS)
        base_custom = _trans_str(SM100_SASS, custom=True, res_usage_dict={})
        for v in (101, 110):
            self.assertEqual(_trans_str(_sm_sass(v)),
                             base_default.replace('SM100', 'SM%d' % v))
            self.assertEqual(_trans_str(_sm_sass(v), custom=True, res_usage_dict={}),
                             base_custom.replace('SM100', 'SM%d' % v))


@unittest.skipUnless(all(p.exists() for p in SAMPLES),
                     'isolated SM100 sample dumps not present')
class TestSM100RealSamples(unittest.TestCase):
    def _check_sample(self, path):
        pairs = _parse_raw_pairs(path)
        self.assertTrue(pairs)
        tuples = list(CuInsFeeder(str(path)))
        self.assertEqual(len(tuples), len(pairs))   # last instruction consumed, no leftovers
        for (addr, code, asm, ctrl), (eaddr, easm, raw) in zip(tuples, pairs):
            self.assertEqual(addr, eaddr)
            self.assertEqual(asm, easm)
            self.assertEqual(code, raw & ~CTRL_MASK)
            self.assertEqual(ctrl, (raw >> CTRL_POS) & 0x1ffff)
            # structural decode/encode roundtrip of every observed ctrl value
            self.assertEqual(CuControlCode.encode(CuControlCode.decode(ctrl)), ctrl)
        # exact 128-bit reconstruction through the generic split/merge path
        bs = b''.join(r.to_bytes(16, 'little') for _, _, r in pairs)
        ctrls, inss = CuSMVersion(100).splitCtrlCodeFromBytes(bs)
        self.assertEqual(inss, [t[1] for t in tuples])
        self.assertEqual(ctrls, [t[3] for t in tuples])
        self.assertEqual(CuSMVersion(100).mergeCtrlCodes(inss, ctrls), bs)

    def test_real_samples_iteration(self):
        for p in SAMPLES:
            self._check_sample(p)

    def test_real_samples_trans_prefix(self):
        for p in SAMPLES:
            pairs = dict((a, (r >> CTRL_POS) & 0x1ffff) for a, _, r in _parse_raw_pairs(p))
            for kwargs in ({}, {'custom': True, 'res_usage_dict': {}}):
                feeder = CuInsFeeder(str(p))
                out = StringIO()
                feeder.trans(out, **kwargs)
                seen = 0
                for line in out.getvalue().splitlines():
                    m = R_CTRL_PREFIX.match(line)
                    if m:
                        addr = int(m.group(2), 16)
                        self.assertEqual(m.group(1), CuControlCode.decode(pairs[addr]))
                        seen += 1
                self.assertEqual(seen, len(pairs))  # no instruction lost in translation


if __name__ == '__main__':
    unittest.main()
