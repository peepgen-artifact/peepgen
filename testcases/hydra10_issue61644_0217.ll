define i32 @src(i32 %x) {
  %2 = tail call i32 @llvm.ctpop.i32(i32 %x)
  %3 = icmp eq i32 %2, 1
  %ctlz = tail call i32 @llvm.ctlz.i32(i32 %x, i1 false)
  %bw = select i1 %3, i32 31, i32 32
  %sub = sub i32 %bw, %ctlz
  %shl = shl i32 1, %sub
  ret i32 %shl
}

define i32 @tgt(i32 %x) {
  %dec = add i32 %x, -1
  %lz = tail call i32 @llvm.ctlz.i32(i32 %dec, i1 false)
  %cnt = sub i32 0, %lz
  %mask = and i32 %cnt, 31
  %res = shl i32 1, %mask
  ret i32 %res
}
