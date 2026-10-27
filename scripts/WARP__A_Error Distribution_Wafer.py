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


def plot_error_distribution_wafer():
    # 误差区间标签
    x_labels = [
        '0-10%', '10-20%', '20-30%', '30-40%', '40-50%',
        '50-60%', '60-70%', '70-80%', '80-90%', '90-100%'
    ]

    # --- 录入 Wafer 数据集 @ Epsilon = 1.0% 的真实数据 ---
    # 数据来源：你提供的表格中 Wafer.csv.gz Epsilon=1 的行
    warp = [
        0.0877, 0.0969, 0.0952, 0.1019, 0.1024,
        0.1050, 0.1035, 0.1036, 0.1009, 0.1025
    ]

    mix_piece = [
        0.2546, 0.1902, 0.1513, 0.1120, 0.0804,
        0.0569, 0.0502, 0.0442, 0.0335, 0.0263
    ]

    sim_piece = [
        0.2496, 0.1900, 0.1509, 0.1122, 0.0818,
        0.0559, 0.0515, 0.0466, 0.0354, 0.0256
    ]

    SZ3 = [
        0.1316, 0.1279, 0.1243, 0.1193, 0.1131,
        0.1048, 0.0924, 0.0797, 0.0628, 0.0441
    ]

    ZFP = [
        0.7351, 0.2239, 0.0353, 0.0055, 0.0003,
        0.0000, 0.0000, 0.0000, 0.0000, 0.0000
    ]

    swing = [
        0.3673, 0.1481, 0.1032, 0.0830, 0.0718,
        0.0641, 0.0570, 0.0467, 0.0317, 0.0265
    ]

    # 检查数据长度是否一致
    data_list = [warp, mix_piece, sim_piece, SZ3, ZFP, swing]
    for data in data_list:
        assert len(data) == len(x_labels), "数据长度必须与误差区间数量一致"

    x = np.arange(len(x_labels))

    # 现在有 6 组柱子，所以柱宽要适当减小
    width = 0.13

    fig, ax = plt.subplots(figsize=(13, 6))

    # 绘制对比柱状图
    ax.bar(
        x - 2.5 * width, warp, width,
        label='WARP (Ours)',
        color='#E31A1C',
        edgecolor='black',
        alpha=0.9,
        zorder=3
    )

    ax.bar(
        x - 1.5 * width, mix_piece, width,
        label='Mix-Piece',
        color='#33A02C',
        edgecolor='black',
        alpha=0.8,
        zorder=3
    )

    ax.bar(
        x - 0.5 * width, sim_piece, width,
        label='Sim-Piece',
        color='#FF7F00',
        edgecolor='black',
        alpha=0.8,
        zorder=3
    )

    ax.bar(
        x + 0.5 * width, SZ3, width,
        label='SZ3',
        color='#1F78B4',
        edgecolor='black',
        alpha=0.8,
        zorder=3
    )

    ax.bar(
        x + 1.5 * width, ZFP, width,
        label='ZFP',
        color='#A6CEE3',
        edgecolor='black',
        alpha=0.8,
        zorder=3
    )

    ax.bar(
        x + 2.5 * width, swing, width,
        label='Swing',
        color='#6A3D9A',
        edgecolor='black',
        alpha=0.8,
        zorder=3
    )

    # 装饰图表
    ax.set_ylabel('Frequency (Ratio of data points)', fontweight='bold')
    ax.set_xlabel('Relative Error Intervals (as % of ε)', fontweight='bold')
    ax.set_title(
        'Error Distribution Comparison: Wafer Dataset (ε = 1%)',
        fontsize=22,
        fontweight='bold',
        pad=20
    )

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, rotation=30)

    # 设置 X 轴和 Y 轴刻度字体大小
    ax.tick_params(axis='both', labelsize=16)

    # 自动设置 y 轴范围，避免 ZFP 的高柱子被截断
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

    # 保存图片时可以取消下面这行注释
    # plt.savefig("Error_Dist_Wafer_1pct.pdf", dpi=300, bbox_inches='tight')

    plt.show()


# 执行绘图
plot_error_distribution_wafer()
