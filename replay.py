"""Reference OHLC execution semantics, not a trading engine."""
def reference_exit(rows, side, stop, target):
    if side not in (-1,1) or not (stop<target if side==1 else target<stop): raise ValueError('Invalid barriers')
    if not len(rows): raise ValueError('Empty price path')
    for i,(o,h,l,c) in enumerate(rows):
        if side==1:
            if o<=stop: return i,o,1
            if l<=stop: return i,stop,1
            if h>=target: return i,target,2
        else:
            if o>=stop: return i,o,1
            if h>=stop: return i,stop,1
            if l<=target: return i,target,2
    return len(rows)-1,rows[-1][3],0
