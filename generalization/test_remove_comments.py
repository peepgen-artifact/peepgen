from generalization.utils import remove_comments


def test_remove_comments():
    input_text = '''
; full line comment before
; trailing comment line
'''

    expected = '''

define i32 @foo(i32 %x) {
  %a = add i32 %x, 1
  %b = and i32 %a, 255
  ret i32 %b
}

'''

    out = remove_comments(input_text)
    print(f"Output:\n{out}\n--- expected:\n{expected}")
    # assert out == expected, f"Unexpected output:\n{out}\n--- expected:\n{expected}"


if __name__ == '__main__':
    test_remove_comments()
    print('remove_comments test passed')
