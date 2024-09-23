import matplotlib.pyplot as plt
import re
from collections import defaultdict
import csv

# 读取数据文件
with open('fitness_log.txt', 'r') as file:
    data = file.read()

# 解析数据
generation_data = defaultdict(lambda: {'fitnesses': [], 'profits': []})

for line in data.split('\n'):
    match = re.search(r'Generation: (\d+).+fitness: ([-\d.]+)', line)
    if match:
        gen = int(match.group(1))
        fit = float(match.group(2))
        generation_data[gen]['fitnesses'].append(fit)
        
        profit_match = re.search(r'total_profit_percent: ([-\d.]+)', line)
        if profit_match:
            profit = float(profit_match.group(1))
            generation_data[gen]['profits'].append(profit)

# 提取每代的最大值
generations = sorted(generation_data.keys())
max_fitnesses = [max(generation_data[gen]['fitnesses']) for gen in generations]
max_profits = [max(generation_data[gen]['profits']) for gen in generations]

# 保存数据到CSV文件
with open('genetic_algorithm_results.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['Generation', 'Max Fitness', 'Max Profit (%)'])
    for gen, fit, profit in zip(generations, max_fitnesses, max_profits):
        csvwriter.writerow([gen, fit, profit])

# 创建两个子图
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12))

# 绘制 Fitness vs Generation 散点图和连线
for gen in generations:
    ax1.scatter([gen] * len(generation_data[gen]['fitnesses']), generation_data[gen]['fitnesses'], alpha=0.5)
ax1.plot(generations, max_fitnesses, color='red', linewidth=2, label='Max Fitness')
ax1.set_xlabel('Generation')
ax1.set_ylabel('Fitness')
ax1.set_title('Fitness vs Generation')
ax1.legend()

# 绘制 Total Profit vs Generation 散点图和连线
for gen in generations:
    ax2.scatter([gen] * len(generation_data[gen]['profits']), generation_data[gen]['profits'], alpha=0.5)
ax2.plot(generations, max_profits, color='red', linewidth=2, label='Max Profit (%)')
ax2.set_xlabel('Generation')
ax2.set_ylabel('Total Profit (%)')
ax2.set_title('Total Profit (%) vs Generation')
ax2.legend()

plt.tight_layout()

# 保存图像到本地
plt.savefig('genetic_algorithm_results.png', dpi=300, bbox_inches='tight')

print("数据已保存到 genetic_algorithm_results.csv")
print("图像已保存到 genetic_algorithm_results.png")