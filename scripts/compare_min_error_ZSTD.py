import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# =========================
# 1. 读取数据
# =========================
df = pd.read_csv(r"E:\data_compress\第二篇论文资料\第二篇论文实验数据\compare_min_error_ZSTD.csv")

# 清理列名
df.columns = [c.strip() for c in df.columns]

# 清理数据集名称
df["Dataset"] = (
    df["Dataset"]
    .astype(str)
    .str.replace(".csv.gz", "", regex=False)
    .str.replace(".csv", "", regex=False)
)

# =========================
# 2. 取每个 Dataset 的“最小误差”对应行
# =========================
# 你的数据看起来每个数据集是按 epsilon 从小到大排列的
# 所以直接取每组第一行
df_min = df.groupby("Dataset", sort=False).first().reset_index()

# 如果你想固定数据集顺序，可以手动指定
dataset_order = [
    "Cricket", "Lightning", "MoteStrain", "Wafer",
    "WindSpeed", "WindDirection", "FaceFour",
    "Pressure", "BTCUSD", "ETHUSD", "SPX",
    "STOXX50E", "city_temperature"
]

# 只保留存在的数据集，并排序
df_min = df_min.set_index("Dataset")
df_min = df_min.loc[[d for d in dataset_order if d in df_min.index]].reset_index()

# =========================
# 3. 需要绘制的列
# =========================
cols = [
    "PMC-MR_CR(pts/byte)",
    "PMC-MR_CRzstd(pts/byte)",
    "Swing_CR(pts/byte)",
    "Swing_CRzstd(pts/byte)",
    "ZFP_CR(pts/byte)",
    "ZFP_CRzstd(pts/byte)",
    "WARP_CR(pts/byte)",
    "WARP_CRzstd(pts/byte)",
]

labels = [
    "PMC-MR",
    "PMC-MR+Zstd",
    "Swing",
    "Swing+Zstd",
    "ZFP",
    "ZFP+Zstd",
    "WARP",
    "WARP+Zstd",
]

# 检查列是否都存在
missing = [c for c in cols if c not in df_min.columns]
if missing:
    raise ValueError(f"缺少列: {missing}")

# 转为数值
for c in cols:
    df_min[c] = pd.to_numeric(df_min[c], errors="coerce")

# =========================
# 4. 画分组柱状图
# =========================
x = np.arange(len(df_min))
n_series = len(cols)
width = 0.1

plt.figure(figsize=(18, 7))

for i, col in enumerate(cols):
    plt.bar(
        x + (i - (n_series - 1) / 2) * width,
        df_min[col],
        width=width,
        label=labels[i]
    )

plt.xticks(x, df_min["Dataset"], rotation=35, ha="right")
plt.ylabel("Compression Ratio (pts/byte)", fontsize=12)
plt.xlabel("Dataset", fontsize=12)
plt.title("Compression Ratio at the Smallest Error Bound", fontsize=14)
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.legend(ncol=4, fontsize=10)
plt.tight_layout()

plt.savefig("min_error_cr_barplot.png", dpi=300, bbox_inches="tight")
plt.savefig("min_error_cr_barplot.pdf", bbox_inches="tight")
plt.show()

# =========================
# 5. 可选：打印提取后的数据
# =========================
print(df_min[["Dataset"] + cols].round(4))
