import math
import matplotlib.pyplot as plt
import numpy as np

def duration_factor(minutes):
    return 2 / (1 + math.exp(minutes / 1440))

# 创建数据点
minutes = np.linspace(0, 10080, 1000)  # 0 到 7 天（10080 分钟）
factors = [duration_factor(m) for m in minutes]

# 绘制图形
plt.figure(figsize=(10, 6))
plt.plot(minutes / 60, factors)  # 转换 x 轴为小时
plt.title('Duration Factor vs. Trade Duration')
plt.xlabel('Trade Duration (hours)')
plt.ylabel('Duration Factor')
plt.grid(True)
plt.show()