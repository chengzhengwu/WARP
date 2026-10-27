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
    "WAP-SRC (adaptive)",
    "WAP-SRC (W128)",
    "WAP-SRC (W1024)",
    "WAP-SRC (W4096)",
    "WAP-SRC (W16k)",
]

# 两类误差网格：market/index/disk 用 0.05%..0.50%，measurement 用 0.5%..5.0%
SMALL_REGIME = "small-eps"     # 0.05% .. 0.50%  (BTCUSD, SPX, SSD_HDD_benchmarks)
LARGE_REGIME = "large-eps"     # 0.50% .. 5.00%  (Cricket, FaceFour, Lightning,
                                #                MoteStrain, Wafer, WindDirection)

# =========================
# 2) 找到 xlsx
# =========================

xlsx_path = r"E:\data_compress\第二篇论文资料\第二篇论文实验数据\window_ablation_wapsrc.xlsx"
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
    elif cl in ["regime", "grid", "epsilon regime"]:
        rename_map[c] = "Regime"
raw = raw.rename(columns=rename_map)

need = {"Epsilon%", "Points", "CompressedBytes", "Variant", "Regime"}
missing = need - set(raw.columns)
if missing:
    raise ValueError(f"缺少列：{missing}\n当前列名：{list(raw.columns)}")

raw["Epsilon%"] = raw["Epsilon%"].astype(float)

# =========================
# 4) micro-average CR：CR = 8 * sum(Points) / sum(CompressedBytes)
#    按 (Variant, Regime, Epsilon%) 分组：Regime 区分两套误差网格，
#    避免同一个 ε 位置上把不同网格的数据集混在一起求平均。
# =========================
def micro_cr(g: pd.DataFrame) -> float:
    pts = g["Points"].sum()
    byt = g["CompressedBytes"].sum()
    return (8.0 * pts) / byt if byt > 0 else float("nan")

curve = (
    raw.groupby(["Variant", "Regime", "Epsilon%"], as_index=False)
       .apply(lambda g: pd.Series({"CR": micro_cr(g)}))
       .reset_index(drop=True)
)
curve = curve[curve["Variant"].isin(variants)].copy()
if curve.empty:
    print("variants 没匹配到任何 sheet。实际 sheet 有：")
    print(sorted(raw["Variant"].unique()))
    raise SystemExit

print("\n=== micro-average CR (8*sum(Points)/sum(CompressedBytes)) ===")
piv = curve.pivot_table(index=["Regime", "Epsilon%"], columns="Variant", values="CR")
piv = piv[[v for v in variants if v in piv.columns]]
print(piv.round(4).to_string())

# =========================
# 5) 两子图：左 = 小 ε 网格，右 = 大 ε 网格
# =========================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.2), sharey=False)

for v in variants:
    dv = curve[(curve["Variant"] == v) & (curve["Regime"] == SMALL_REGIME)].sort_values("Epsilon%")
    if not dv.empty:
        ax1.plot(dv["Epsilon%"], dv["CR"], marker="o", linewidth=2.0, label=v)

ax1.set_title(r"Small $\varepsilon$ (0.05% – 0.50%, market/index/disk)")
ax1.set_xlabel("Epsilon (%)")
ax1.set_ylabel("CR = 8 · Points / CompressedBytes")
ax1.grid(True, alpha=0.3)

for v in variants:
    dv = curve[(curve["Variant"] == v) & (curve["Regime"] == LARGE_REGIME)].sort_values("Epsilon%")
    if not dv.empty:
        ax2.plot(dv["Epsilon%"], dv["CR"], marker="o", linewidth=2.0, label=v)

ax2.set_title(r"Large $\varepsilon$ (0.50% – 5.00%, measurement)")
ax2.set_xlabel("Epsilon (%)")
ax2.grid(True, alpha=0.3)

ax2.legend(loc="best")

fig.suptitle("Window-size ablation: CR vs ε (micro-average across datasets)")
plt.tight_layout()

out_dir = Path(r"E:\data_compress\第二篇论文资料\第二篇论文实验数据")
out_png = out_dir / "窗口消融_90cfg.png"
fig.savefig(out_png, dpi=300, bbox_inches="tight")
print("\nsaved:", out_png)
plt.show()
