import numpy as np
from gnuradio import gr
import os
import subprocess

class blk(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(self, name='Auto Terminal', in_sig=[np.uint8], out_sig=None)
        # 只在初始化时执行一次：打开 gnome-terminal 运行 nc 监听命令
        # 如果你用的是 Ubuntu，使用 gnome-terminal
        # od -t x1 是将数据以 16 进制显示，这是看原始数据最方便的方式
        cmd = 'gnome-terminal -- bash -c "echo 正在等待信号数据...; nc -u -l 12345 | od -t x1 -An; exec bash"'
        subprocess.Popen(cmd, shell=True)

    def work(self, input_items, output_items):
        # 这个模块不需要对数据做处理，直接透传或丢弃即可
        return len(input_items[0])
