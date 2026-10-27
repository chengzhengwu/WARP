import matplotlib.pyplot as plt
import numpy as np

# 设置学术论文风格
plt.style.use('seaborn-v0_8-paper')
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 12,
    'axes.labelsize': 14,
    'legend.fontsize': 10,
    'xtick.labelsize': 11,
    'ytick.labelsize': 11
})

# 误差区间
x_labels = ['0-10%', '10-20%', '20-30%', '30-40%', '40-50%',
            '50-60%', '60-70%', '70-80%', '80-90%', '90-100%']

# 真实数据录入
warp = [0.127, 0.103, 0.100, 0.098, 0.097, 0.096, 0.095, 0.094, 0.093, 0.092]
mix_piece = [0.205, 0.100, 0.095, 0.095, 0.095, 0.064, 0.066, 0.072, 0.079, 0.120]
sim_piece = [0.237, 0.113, 0.107, 0.106, 0.106, 0.054, 0.056, 0.059, 0.062, 0.092]
SZ3 = [0.1028, 0.1017, 0.1016, 0.1005, 0.1000, 0.0998, 0.0990, 0.0986, 0.0983, 0.0977]
ZFP = [0.6992, 0.2720, 0.0286, 0.0002, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000]
swing = [0.339, 0.055, 0.056, 0.058, 0.060, 0.069, 0.074, 0.081, 0.093, 0.110]

# 检查长度是否一致
data_list = [warp, mix_piece, sim_piece, SZ3, ZFP, swing]
for data in data_list:
    assert len(data) == len(x_labels), "数据长度必须与误差区间数量一致"

x = np.arange(len(x_labels))
width = 0.13   # 6组柱子时柱宽要缩小

fig, ax = plt.subplots(figsize=(13, 6))

# 绘制柱状图（6组，分别错开）
ax.bar(x - 2.5 * width, warp, width,
       label='WARP (Ours)', color='#E31A1C',
       edgecolor='black', alpha=0.9, zorder=3)

ax.bar(x - 1.5 * width, mix_piece, width,
       label='Mix-Piece', color='#33A02C',
       edgecolor='black', alpha=0.8, zorder=3)

ax.bar(x - 0.5 * width, sim_piece, width,
       label='Sim-Piece', color='#FF7F00',
       edgecolor='black', alpha=0.8, zorder=3)

ax.bar(x + 0.5 * width, SZ3, width,
       label='SZ3', color='#1F78B4',
       edgecolor='black', alpha=0.8, zorder=3)

ax.bar(x + 1.5 * width, ZFP, width,
       label='ZFP', color='#A6CEE3',
       edgecolor='black', alpha=0.8, zorder=3)

ax.bar(x + 2.5 * width, swing, width,
       label='Swing', color='#6A3D9A',
       edgecolor='black', alpha=0.8, zorder=3)

# 装饰
ax.set_ylabel('Frequency (Ratio of points)', fontweight='bold')
ax.set_xlabel('Relative Error Intervals (as % of ε)', fontweight='bold')

# 这里建议标题改成 WindDirection，而不是 WindSpeed
ax.set_title('Error Distribution Comparison: WindDirection (ε = 1%)',
             fontsize=22, fontweight='bold', pad=20)

ax.set_xticks(x)
ax.set_xticklabels(x_labels, rotation=30)
ax.tick_params(axis='both', labelsize=16)

# 自动设置y轴，避免ZFP最高柱被截断
max_y = max(
    max(warp),
    max(mix_piece),
    max(sim_piece),
    max(SZ3),
    max(ZFP),
    max(swing)
)
ax.set_ylim(0, max_y * 1.15)

ax.legend(loc='upper right', frameon=True, shadow=True)
ax.grid(axis='y', ls='--', alpha=0.5, zorder=0)


plt.tight_layout()
# plt.savefig("Error_Distribution_WindDirection.pdf", dpi=300, bbox_inches='tight')
plt.show()
