import matplotlib.pyplot as plt
import numpy as np

# 1. 准备数据 (130 个样本)
# WAP-SRC (CR)
group_a = np.array([
    # BTCUSD
    31.48, 49.80, 67.20, 84.67, 96.57,
    116.10, 134.28, 165.21, 191.06, 211.79,

    # Cricket
    28.27, 42.50, 56.43, 65.87, 78.54,
    92.04, 108.44, 126.73, 148.45, 172.39,

    # FaceFour
    21.13, 27.09, 32.62, 38.18, 45.30,
    50.30, 54.59, 59.65, 64.75, 70.73,

    # Lightning
    36.11, 58.08, 70.26, 91.01, 119.75,
    145.42, 190.00, 224.92, 254.22, 293.00,

    # MoteStrain
    26.03, 36.38, 44.93, 52.03, 59.34,
    66.61, 76.46, 82.57, 87.71, 92.96,

    # SPX
    67.24, 116.54, 170.24, 219.94, 271.87,
    322.26, 384.26, 433.31, 485.62, 539.53,

    # Wafer
    85.13, 116.29, 141.91, 146.63, 175.80,
    209.26, 212.14, 214.25, 213.20, 217.22,

    # WindDirection
    14.13, 18.37, 22.04, 25.38, 28.73,
    32.01, 35.67, 39.41, 41.43, 44.26,

    # SSD_HDD_benchmarks
    14.65, 16.87, 17.84, 19.73, 19.21,
    21.87, 21.87, 22.77, 22.35, 22.78
])

# Mix-Branch (CR)
group_b = np.array([
    # BTCUSD
    12.13, 23.79, 37.73, 54.54, 73.73,
    91.05, 113.60, 135.44, 158.34, 188.15,

    # Cricket
    15.70, 27.16, 38.94, 50.93, 63.04,
    75.67, 87.87, 100.36, 113.56, 128.07,

    # FaceFour
    8.38, 11.23, 14.39, 17.58, 21.07,
    24.56, 28.37, 31.69, 35.16, 38.16,

    # Lightning
    21.01, 35.29, 50.70, 66.86, 83.99,
    104.80, 124.53, 145.37, 162.86, 185.37,

    # MoteStrain
    14.75, 22.52, 29.09, 35.12, 40.55,
    46.48, 51.69, 57.02, 61.67, 67.82,

    # SPX
    37.60, 98.20, 183.09, 289.89, 414.81,
    556.90, 725.24, 907.27, 1103.43, 1304.43,

    # Wafer
    51.42, 69.39, 81.91, 90.04, 95.83,
    101.77, 113.95, 119.18, 123.49, 131.40,

    # WindDirection
    7.46, 9.62, 11.73, 13.97, 16.33,
    18.81, 21.47, 24.26, 27.14, 30.20,

    # SSD_HDD_benchmarks
    9.42, 10.91, 11.80, 12.62, 13.05,
    13.73, 14.60, 14.92, 15.13, 15.77
])
# 2. 计算 CDF
def get_cdf(data):
    sorted_data = np.sort(data)
    y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)
    return sorted_data, y



x_a, y_a = get_cdf(group_a)
x_b, y_b = get_cdf(group_b)

# 3. 绘图：设置合理的比例
plt.figure(figsize=(7, 5))

# 使用 log 刻度
plt.xscale('log')

# 按照 file.png 渲染线条
plt.plot(x_a, y_a, label='WAP-SRC', color='#0052cc', linewidth=2.0, linestyle='-')
plt.plot(x_b, y_b, label='Mix-Branch', color='#e68a00', linewidth=2.0, linestyle='--')

# 4. 图表细节美化
plt.title('CDF of Performance', fontsize=12)
plt.xlabel('CR (pts/byte)', fontsize=10)
plt.ylabel('Probability (CDF)', fontsize=10)

# 移除上方和右方的边框
plt.gca().spines['top'].set_visible(False)
plt.gca().spines['right'].set_visible(False)

# 设置图例
plt.legend(loc='upper left', frameon=True, fontsize=9)

# 自动调整边距，防止裁剪
plt.tight_layout()

# 保存高清图
plt.savefig('final_cdf_reproduced.png', dpi=300)
plt.show()
