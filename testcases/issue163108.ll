define i8 @src(i1 %arg0) {
  %v0 = zext i1 %arg0 to i8
  %v1 = select i1 %arg0, i8 0, i8 8
  %v2 = or disjoint i8 %v1, %v0
  %v3 = or disjoint i8 %v2, 16
  ret i8 %v3
}

define i8 @tgt(i1 %arg0) {
  %v1 = select i1 %arg0, i8 17, i8 24
  ret i8 %v1
}