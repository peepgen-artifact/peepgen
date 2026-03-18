define i32 @src(i32 %v0) {
  %v1 = icmp eq i32 0, %v0
  %v2 = lshr i32 %v0, 1
  %v3 = call i32 @llvm.ctlz.i32(i32 %v2, i1 false)
  %v4 = sub i32 32, %v3
  %v5 = shl i32 1, %v4
  %v6 = select i1 %v1, i32 0, i32 %v5
  ret i32 %v6
}

define i32 @tgt(i32 %v0) {
  %v1 = icmp eq i32 0, %v0
  %v2 = call i32 @llvm.ctlz.i32(i32 %v0, i1 false)
  %v3 = lshr i32 -2147483648, %v2
  %v4 = select i1 %v1, i32 0, i32 %v3
  ret i32 %v4
}

; define i32 @src(i32 %x) {
;   %s = add i32 %x, -1
;   %lz = call i32 @llvm.ctlz.i32(i32 %s, i1 false)
;   %s32 = sub nuw nsw i32 32, %lz
;   %pow2 = shl nuw i32 1, %s32
;   %ugt1 = icmp ugt i32 %x, 1
;   %ceil = select i1 %ugt1, i32 %pow2, i32 1
;   ret i32 %ceil
; }
;
; define i32 @tgt(i32 %x) {
;   %m = call i32 @llvm.umax.i32(i32 %x, i32 1)
;   %s = add i32 %m, -1
;   %lz = call i32 @llvm.ctlz.i32(i32 %s, i1 false)
;   %s32 = sub nuw nsw i32 32, %lz
;   %ceil = shl nuw i32 1, %s32
;  ret i32 %ceil
; }

; wrong input and inconsistent with the original optimization in github issue
