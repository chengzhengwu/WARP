import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# =========================
# 0) 全局字体设置（关键：这里统一放大）
# =========================
plt.rcParams.update({
    "font.size": 16,          # 全局默认字号（刻度等）
    "axes.labelsize": 18,     # x/y 轴标题
    "axes.titlesize": 18,     # 子图标题
    "figure.titlesize": 20,   # 总标题
    "legend.fontsize": 14,    # 图例
    "xtick.labelsize": 16,    # x刻度
    "ytick.labelsize": 16,    # y刻度
})

# =========================
# 1) 配置
# =========================

variants = [
    "WARP(full)",
    "WARP(fixedW128)",
    "WARP(fixedW1024)",
    "WARP(fixedW4096)",
    "WARP(fixedW16384)",
]
SMALL_EPS_MAX = 0.5
LARGE_EPS_MIN = 1.0

# =========================
# 2) 自动找到 xlsx
# =========================


xlsx_path = "E:\data_compress\第二篇论文资料\第二篇论文实验数据\warp_ablation_最新消融数据.xlsx"  # 改成你的路径
print("使用文件：", xlsx_path)

# =========================
# 3) 读 Excel
# =========================
xl = pd.ExcelFile(xlsx_path)
dfs = []
for sheet in xl.sheet_names:
    df = xl.parse(sheet).copy()
    df["Variant"] = sheet
    dfs.append(df)
raw = pd.concat(dfs, ignore_index=True)

# 列名统一
rename_map = {}
for c in raw.columns:
    cl = str(c).strip().lower()
    if cl in ["epsilon", "epsilon%", "eps", "eps%", "error", "error%"]:
        rename_map[c] = "Epsilon%"
    elif cl in ["compressedbytes", "compressed_bytes", "bytes", "compressed bytes", "compressed"]:
        rename_map[c] = "CompressedBytes"
    elif cl in ["points", "n", "num_points", "count", "num points"]:
        rename_map[c] = "Points"
    elif cl in ["dataset", "name", "series", "trace"]:
        rename_map[c] = "Dataset"
raw = raw.rename(columns=rename_map)

need = {"Epsilon%", "Points", "CompressedBytes", "Variant"}
missing = need - set(raw.columns)
if missing:
    raise ValueError(f"缺少列：{missing}\n当前列名：{list(raw.columns)}")

raw["Epsilon%"] = raw["Epsilon%"].astype(float)

# =========================
# 4) micro-average CR：CR = 8 * sum(Points) / sum(CompressedBytes)
# =========================
def micro_cr(g: pd.DataFrame) -> float:
    pts = g["Points"].sum()
    byt = g["CompressedBytes"].sum()
    return (8.0 * pts) / byt if byt > 0 else float("nan")

curve = (
    raw.groupby(["Variant", "Epsilon%"], as_index=False)
       .apply(lambda g: pd.Series({"CR": micro_cr(g)}))
       .reset_index(drop=True)
)
curve = curve[curve["Variant"].isin(variants)].copy()
if curve.empty:
    print("variants 没匹配到任何 sheet。实际 sheet 有：")
    print(sorted(raw["Variant"].unique()))
    raise SystemExit

# =========================
# 5) 方案一：两子图（小ε / 大ε），字体已放大
# =========================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), sharey=False)

# 左：小ε
for v in variants:
    dv = curve[(curve["Variant"] == v) & (curve["Epsilon%"] <= SMALL_EPS_MAX)].sort_values("Epsilon%")
    if not dv.empty:
        ax1.plot(dv["Epsilon%"], dv["CR"], marker="o", linewidth=2.0, label=v)

ax1.set_title(f"Small ε (≤ {SMALL_EPS_MAX}%)")
ax1.set_xlabel("Epsilon (%)")
ax1.set_ylabel("CR = 8 · Points / CompressedBytes")
ax1.grid(True, alpha=0.3)

# 右：大ε
for v in variants:
    dv = curve[(curve["Variant"] == v) & (curve["Epsilon%"] >= LARGE_EPS_MIN)].sort_values("Epsilon%")
    if not dv.empty:
        ax2.plot(dv["Epsilon%"], dv["CR"], marker="o", linewidth=2.0, label=v)

ax2.set_title(f"Large ε (≥ {LARGE_EPS_MIN}%)")
ax2.set_xlabel("Epsilon (%)")
ax2.grid(True, alpha=0.3)

ax2.legend(loc="best")

fig.suptitle("Window-size ablation: CR vs ε (micro-average across datasets)")
plt.tight_layout()
plt.show()

# 可选保存（论文用）
# fig.savefig("window_ablation_cr_vs_eps_split_bigfont.png", dpi=300, bbox_inches="tight")
