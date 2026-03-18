import unittest
from utils import extract_assumptions_and_dependencies

class TestExtractAssumptions(unittest.TestCase):
    def test_simple_assume(self):
        ir_body = [
            "%c = icmp eq i32 %x, 0",
            "call void @llvm.assume(i1 %c)",
            "%res = add i32 %x, 1",
            "%t1 = mul i32 %res, 2",
            "%t2 = sub i32 %t1, %x",
            "%t3 = xor i32 %t2, %res",
            "ret i32 %t1"
        ]
        expected = [
            "%c = icmp eq i32 %x, 0",
            "call void @llvm.assume(i1 %c)"
        ]
        result = extract_assumptions_and_dependencies(ir_body)
        self.assertEqual(result, expected)

    def test_nested_dependency(self):
        ir_body = [
            "%a = add i32 %x, 1",
            "%b = mul i32 %a, 2",
            "%c = icmp sgt i32 %b, 10",
            "call void @llvm.assume(i1 %c)",
            "%d = add i32 %b, 42",
            "%e = xor i32 %d, %a",
            "%f = shl i32 %e, 1",
            "%g = and i32 %f, 255",
            "ret i32 %g"
        ]
        expected = [
            "%a = add i32 %x, 1",
            "%b = mul i32 %a, 2",
            "%c = icmp sgt i32 %b, 10",
            "call void @llvm.assume(i1 %c)"
        ]
        result = extract_assumptions_and_dependencies(ir_body)
        self.assertEqual(result, expected)

    def test_multiple_assumes(self):
        ir_body = [
            "%cond1 = icmp ne i32 %x, 0",
            "call void @llvm.assume(i1 %cond1)",
            "%t1 = mul i32 %x, 2",
            "%y = add i32 %x, 5",
            "%t2 = add i32 %t1, %y",
            "%cond2 = icmp ult i32 %y, 100",
            "call void @llvm.assume(i1 %cond2)",
            "%r = sub i32 %y, 3",
            "%s = or i32 %r, %x",
            "%u = lshr i32 %s, 1",
            "ret i32 %u"
        ]
        expected = [
            "%cond1 = icmp ne i32 %x, 0",
            "call void @llvm.assume(i1 %cond1)",
            "%y = add i32 %x, 5",
            "%cond2 = icmp ult i32 %y, 100",
            "call void @llvm.assume(i1 %cond2)"
        ]
        result = extract_assumptions_and_dependencies(ir_body)
        self.assertEqual(result, expected)

    def test_no_assume(self):
        ir_body = [
            "%res = add i32 %x, %y",
            "ret i32 %res"
        ]
        expected = []
        result = extract_assumptions_and_dependencies(ir_body)
        self.assertEqual(result, expected)

    def test_assume_with_comments_and_whitespace(self):
        ir_body = [
            "  %c = icmp eq i32 %x, 0  ; check zero",
            "  call void @llvm.assume(i1 %c) ; assume it",
            "  %tmp = add i32 %x, 1  ; compute after assume",
            "  %t1 = mul i32 %tmp, 3",
            "  %t2 = xor i32 %t1, %x",
            "  %t3 = and i32 %t2, 7",
            "  ret i32 %t3"
        ]
        # The function returns the original lines (stripped of comments/whitespace in logic but returns original strings? 
        # Wait, the implementation returns `lines[idx]`. `lines` is `list(function_body)`.
        # So it should return the original strings.
        expected = [
            "  %c = icmp eq i32 %x, 0  ; check zero",
            "  call void @llvm.assume(i1 %c) ; assume it"
        ]
        result = extract_assumptions_and_dependencies(ir_body)
        self.assertEqual(result, expected)

    def test_shared_dependency(self):
        ir_body = [
            "%base = add i32 %x, 1",
            "%c1 = icmp sgt i32 %base, 0",
            "call void @llvm.assume(i1 %c1)",
            "%c2 = icmp slt i32 %base, 10",
            "call void @llvm.assume(i1 %c2)",
            "%res = mul i32 %base, 2",
            "%tmp1 = add i32 %res, 1",
            "%tmp2 = shl i32 %tmp1, 2",
            "%tmp3 = xor i32 %tmp2, %base",
            "ret i32 %tmp3"
        ]
        expected = [
            "%base = add i32 %x, 1",
            "%c1 = icmp sgt i32 %base, 0",
            "call void @llvm.assume(i1 %c1)",
            "%c2 = icmp slt i32 %base, 10",
            "call void @llvm.assume(i1 %c2)"
        ]
        result = extract_assumptions_and_dependencies(ir_body)
        self.assertEqual(result, expected)

if __name__ == '__main__':
    unittest.main()
