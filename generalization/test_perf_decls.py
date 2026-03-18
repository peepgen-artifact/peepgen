from performance_verification import _ensure_decls

examples = [
    {
        'name': 'ctpop on i32',
        'ir': '''define i32 @f(i32 %x) {
  %y = call i32 @llvm.ctpop.i32(i32 %x)
  ret i32 %y
}
'''
    },
    {
        'name': 'ctpop on i128',
        'ir': '''define i128 @f(i128 %x) {
  %y = call i128 @llvm.ctpop.i128(i128 %x)
  ret i128 %y
}
'''
    },
    {
        'name': 'umin on v4i32 (vector of i32)',
        'ir': '''
define <4 x i32> @f(<4 x i32> %x, <4 x i32> %y) {
  %z = call <4 x i32> @llvm.umin.v4i32(<4 x i32> %x, <4 x i32> %y)
  ret <4 x i32> %z
}
'''
    },
    {
        'name': 'ctpop on v2float (vector of float) - synthetic',
        'ir': '''define <2 x float> @f(<2 x float> %x) {
  %y = call <2 x float> @llvm.ctpop.v2float(<2 x float> %x)
  ret <2 x float> %y
}
'''
    },
    {
        'name': 'bswap on i8 (small integer)',
        'ir': '''define i8 @f(i8 %x) {
  %y = call i8 @llvm.bswap.i8(i8 %x)
  ret i8 %y
}
'''
    },
    {
        'name': 'mixed: umanip and ct pop',
        'ir': '''define i64 @src(i64 %a, i64 %b) {
  %u = call i64 @llvm.umax.i64(i64 %a, i64 %b)
  %c = call i64 @llvm.ctpop.i64(i64 %u)
  ret i64 %c
}
'''
    },
]

if __name__ == '__main__':
    for ex in examples:
        print('---')
        print('Example:', ex['name'])
        print('\nOriginal IR:\n')
        print(ex['ir'])
        got = _ensure_decls(ex['ir'])
        print('\nAfter _ensure_decls:\n')
        print(got)
        print('\n')
    print('Done. Run `python test_perf_decls.py` from the `generalization/` directory.')
