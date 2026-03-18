define i40 @src(i40 %arg0) {
  %1 = trunc i40 %arg0 to i8
  %2 = icmp eq i8 %1, 2
  %3 = and i40 %arg0, -256
  %4 = select i1 %2, i8 0, i8 %1
  %5 = select i1 %2, i40 0, i40 %3
  %6 = zext i8 %4 to i40
  %7 = or disjoint i40 %5, %6
  ret i40 %7
}

define i40 @tgt(i40 %arg0) {
  %1 = trunc i40 %arg0 to i8
  %2 = icmp eq i8 %1, 2
  %3 = select i1 %2, i40 0, i40 %arg0
  ret i40 %3
}