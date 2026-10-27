import pandas as pd
import matplotlib.pyplot as plt

# =========================
# 1. Read data
# =========================
# Save your table as: zstd_effect.csv
df = pd.read_csv("E:\data_compress\第二篇论文资料\第二篇论文实验数据\zstd_effect - 10个数据集版.csv")

# =========================
# 2. Clean column names
# =========================
df.columns = [c.strip() for c in df.columns]

# Rename for convenience
df = df.rename(columns={
    "CR(pts/byte)": "CR_zstd",
    "no-zstdCR(pts/byte)": "CR_no_zstd"
})

# Convert to numeric
df["CR_zstd"] = pd.to_numeric(df["CR_zstd"], errors="coerce")
df["CR_no_zstd"] = pd.to_numeric(df["CR_no_zstd"], errors="coerce")

# Drop invalid rows
df = df.dropna(subset=["Dataset", "CR_zstd", "CR_no_zstd"])
df = df[(df["CR_zstd"] > 0) & (df["CR_no_zstd"] > 0)]

# =========================
# 3. Compute gain
# =========================
df["Zstd_Gain"] = df["CR_zstd"] / df["CR_no_zstd"]

# Optional: clean dataset names
df["Dataset"] = (
    df["Dataset"]
    .str.replace(".csv.gz", "", regex=False)
    .str.replace(".csv", "", regex=False)
)

# =========================
# 4. Sort datasets by median gain
# =========================
dataset_order = (
    df.groupby("Dataset")["Zstd_Gain"]
    .median()
    .sort_values(ascending=False)
    .index
    .tolist()
)

data_to_plot = [
    df.loc[df["Dataset"] == d, "Zstd_Gain"].values
    for d in dataset_order
]

# =========================
# 5. Plot
# =========================
plt.figure(figsize=(12, 5.5))

bp = plt.boxplot(
    data_to_plot,
    labels=dataset_order,
    showmeans=True,
    patch_artist=True,
    widths=0.6
)

# Baseline line: gain = 1 means no extra benefit from Zstd
plt.axhline(1.0, linestyle="--", linewidth=1.5, label="Gain = 1 (no improvement)")

plt.ylabel("Zstd Gain = CR with Zstd / CR without Zstd", fontsize=12)
plt.xlabel("Dataset", fontsize=12)
plt.title("Effect of Zstd Post-compression on WARP", fontsize=14)
plt.xticks(rotation=35, ha="right")
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.legend()
plt.tight_layout()

plt.savefig("zstd_gain_boxplot.png", dpi=300, bbox_inches="tight")
plt.savefig("zstd_gain_boxplot.pdf", bbox_inches="tight")
plt.show()

# =========================
# 6. Print summary
# =========================
summary = df.groupby("Dataset")["Zstd_Gain"].agg(["mean", "median", "min", "max"])
print(summary.round(4))
print("\nOverall mean gain:", round(df["Zstd_Gain"].mean(), 4))
print("Overall median gain:", round(df["Zstd_Gain"].median(), 4))
