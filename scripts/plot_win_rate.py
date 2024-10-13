import math
import numpy as np
import matplotlib.pyplot as plt

def amplify_win_rate(win_rate, base=10):
    centered_rate = win_rate - 0.9
    amplified = (math.exp(base * centered_rate) - 1) # / (math.exp(base / 2) - 1)
    return amplified

# 创建数据点
win_rates = np.linspace(0, 1, 1000)
amplified_rates = [amplify_win_rate(wr) for wr in win_rates]

# 绘制图形
plt.figure(figsize=(10, 6))
plt.plot(win_rates, amplified_rates, label='Amplified Win Rate')
plt.plot([0, 1], [0, 1], '--', color='gray', label='y=x (No amplification)')

# 添加参考线
plt.axvline(x=0.5, color='r', linestyle=':', label='Center (50% win rate)')
plt.axhline(y=0.5, color='g', linestyle=':', label='50% amplified rate')

plt.xlabel('Original Win Rate')
plt.ylabel('Amplified Win Rate')
plt.title('Win Rate Amplification Function')
plt.legend()
plt.grid(True)

# 显示图形
plt.show()