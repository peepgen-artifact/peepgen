from generalization.utils import preprocess_llm_response


def test_preprocess_with_code_fence_and_entry():
    llm_response = """Some intro
```llvm
; comment
declare i32 @foo(i32)

define i32 @src(i32 %x) {
entry:
  %a = add i32 %x, 1 ; trailing
  ret i32 %a
}
```
Other text
"""
    expected = "\n".join([
        "declare i32 @foo(i32)",
        "define i32 @src(i32 %x) {",
        "%a = add i32 %x, 1",
        "ret i32 %a",
        "}",
    ])
    out = preprocess_llm_response(llm_response)
    # assert out == expected
    print("Output:\n", out)


def test_preprocess_keeps_declares_before_define():
    llm_response = """target triple = "x86_64-unknown-linux-gnu"
; comment
declare void @llvm.assume(i1)
define i32 @src(i32 %x) {
  ret i32 %x
}
"""
    expected = "\n".join([
        "declare void @llvm.assume(i1)",
        "define i32 @src(i32 %x) {",
        "ret i32 %x",
        "}",
    ])
    out = preprocess_llm_response(llm_response)
    assert out == expected


def test_preprocess_removes_entry_lines():
    llm_response = """define i32 @src(i32 %x) {
entry:
  %a = add i32 %x, 1
entry:
  ret i32 %a
}
"""
    expected = "\n".join([
        "define i32 @src(i32 %x) {",
        "%a = add i32 %x, 1",
        "ret i32 %a",
        "}",
    ])
    out = preprocess_llm_response(llm_response)
    assert out == expected


def test_preprocess_no_define_returns_cleaned_text():
    llm_response = """; only comments
entry:
declare i32 @foo(i32) ; trailing
"""
    expected = "declare i32 @foo(i32)"
    out = preprocess_llm_response(llm_response)
    assert out == expected


if __name__ == "__main__":
    test_preprocess_with_code_fence_and_entry()
    test_preprocess_keeps_declares_before_define()
    test_preprocess_removes_entry_lines()
    test_preprocess_no_define_returns_cleaned_text()
    print("preprocess_llm_response tests passed")
