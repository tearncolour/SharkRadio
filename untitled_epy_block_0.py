import numpy as np
from gnuradio import gr

class blk(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(
            self,
            name='4-FSK Slicer',
            in_sig=[np.float32], # 输入是同步后的浮点数
            out_sig=[np.uint8]   # 输出是 0, 1, 2, 3 的符号
        )

    def work(self, input_items, output_items):
        in0 = input_items[0]
        out = output_items[0]
        
        # 判决门限：2, 0, -2
        for i in range(len(in0)):
            if in0[i] > 2:
                out[i] = 3   # 对应 11
            elif in0[i] > 0:
                out[i] = 2   # 对应 10
            elif in0[i] > -2:
                out[i] = 1   # 对应 01
            else:
                out[i] = 0   # 对应 00
        return len(out)
