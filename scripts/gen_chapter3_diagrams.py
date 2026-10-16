"""生成第三章配图（图3.1 系统总体架构图、图3.2 操作流程图）。

用法：python scripts/gen_chapter3_diagrams.py
输出：docs/第三章配图/fig3.1_系统总体架构图.png
      docs/第三章配图/fig3.2_操作流程图.png
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# 中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "第三章配图"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 配色
C_TITLE = "#1F3864"
C_APP = "#DEEBF7"
C_APP_E = "#2E75B6"
C_MODEL = "#FCE4D6"
C_MODEL_E = "#C55A11"
C_DATA = "#E2EFDA"
C_DATA_E = "#548235"
C_SIDE = "#FFF2CC"
C_SIDE_E = "#BF8F00"
C_FLOW = "#DEEBF7"
C_FLOW_E = "#2E75B6"
C_VETO = "#F8CBAD"
C_VETO_E = "#C00000"
C_OK = "#C6E0B4"
C_OK_E = "#548235"
C_BLEND = "#FFE699"
C_BLEND_E = "#BF8F00"


def box(ax, x, y, w, h, text, fc, ec, fontsize=10, bold=False, radius=0.02, align="center"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle=f"round,pad=0.008,rounding_size={radius}",
            linewidth=1.4,
            facecolor=fc,
            edgecolor=ec,
            zorder=2,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        color="#1a1a1a",
        zorder=3,
        linespacing=1.6,
    )


def arrow(ax, p1, p2, color="#404040", style="-|>", lw=1.5, ls="-", rad=0.0):
    ax.add_patch(
        FancyArrowPatch(
            p1,
            p2,
            arrowstyle=style,
            mutation_scale=14,
            linewidth=lw,
            color=color,
            linestyle=ls,
            zorder=1,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


# ---------------------------------------------------------------- 图 3.1
def fig_architecture():
    fig, ax = plt.subplots(figsize=(13, 9.2), dpi=200)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 9.2)
    ax.axis("off")

    ax.text(6.5, 8.85, "图3.1  系统总体架构图", ha="center", va="center", fontsize=16, fontweight="bold", color=C_TITLE)

    L, W = 0.45, 9.0  # 主体左边界与宽度
    SX, SW = 9.85, 2.75  # 右侧支撑模块

    # ===== 应用层 =====
    box(ax, L, 7.05, W, 1.35, "", C_APP, C_APP_E, radius=0.03)
    ax.text(L + 0.22, 8.16, "应用层", fontsize=11.5, fontweight="bold", color=C_APP_E, zorder=4)
    app_items = [
        ("信贷员操作端\n（Vue 3 + Element Plus）", 1.00),
        ("管理后台\n（指标/模型/权限配置）", 3.75),
        ("结果输出\n评分·等级·额度·利率", 6.50),
    ]
    for txt, x in app_items:
        box(ax, x, 7.22, 2.40, 0.72, txt, "#FFFFFF", C_APP_E, fontsize=9.3)

    # ===== 模型层 =====
    box(ax, L, 3.55, W, 3.15, "", C_MODEL, C_MODEL_E, radius=0.03)
    ax.text(
        L + 0.22,
        6.50,
        "模型层（“双引擎基线 + 智能增强”复合架构）",
        fontsize=11.5,
        fontweight="bold",
        color=C_MODEL_E,
        zorder=4,
    )

    # 专家规则引擎
    box(ax, L + 0.25, 4.40, 4.10, 1.85, "", "#FFFFFF", C_MODEL_E, radius=0.02)
    ax.text(
        L + 0.42, 6.02, "专家规则引擎（生产基线 · 主引擎）", fontsize=9.6, fontweight="bold", color=C_MODEL_E, zorder=4
    )
    exp_items = [
        ("① 一票否决红线校验", L + 0.42, 5.48),
        ("② 分维度逐项打分", L + 0.42, 5.04),
        ("③ 层级权重加权合成", L + 2.37, 5.48),
        ("④ 0–1000 分映射与分级", L + 2.37, 5.04),
    ]
    for txt, x, y in exp_items:
        box(ax, x, y, 1.85, 0.36, txt, C_APP, C_APP_E, fontsize=8.2)
    ax.text(
        L + 0.42,
        4.80,
        "层级权重 0.35 / 0.28 / 0.22 / 0.15 / 0.10（基本项 → 具体营业类型）",
        fontsize=7.4,
        color="#7F5F00",
        zorder=4,
    )
    ax.text(
        L + 0.42, 4.58, "星级归一：以中性基准分（500）为锚点生成上下调因子", fontsize=7.4, color="#7F5F00", zorder=4
    )

    # 数据层评分卡
    box(ax, L + 4.65, 4.40, 4.10, 1.85, "", "#FFFFFF", C_MODEL_E, radius=0.02)
    ax.text(
        L + 4.82,
        6.02,
        "数据层评分卡（生产基线 · 辅助校准）",
        fontsize=9.6,
        fontweight="bold",
        color=C_MODEL_E,
        zorder=4,
    )
    for txt, x in [("IV 特征筛选", L + 4.82), ("WOE 编码", L + 6.77)]:
        box(ax, x, 5.48, 1.85, 0.36, txt, C_MODEL, C_MODEL_E, fontsize=8.5)
    box(ax, L + 4.82, 5.04, 1.85, 0.36, "Logistic 回归", C_MODEL, C_MODEL_E, fontsize=8.5)
    box(ax, L + 6.77, 5.04, 1.85, 0.36, "评分映射", C_MODEL, C_MODEL_E, fontsize=8.5)
    ax.text(L + 4.82, 4.80, "极端分位介入：≤15% → 0.5专家 + 0.5数据（下修）", fontsize=7.4, color="#7F5F00", zorder=4)
    ax.text(L + 4.82, 4.58, "≥85% → 0.9专家 + 0.1数据（上修）｜中间区段不干预", fontsize=7.4, color="#7F5F00", zorder=4)

    # 双引擎交互（专家分 → 数据层分位校准）
    arrow(ax, (L + 4.33, 5.26), (L + 4.67, 5.26), color=C_MODEL_E, lw=1.6)

    # 智能增强层（脱敏样本积累后分阶段接入）
    box(ax, L + 0.25, 3.68, 8.50, 0.62, "", "#FFF2CC", C_SIDE_E, radius=0.02)
    ax.text(
        L + 0.42,
        4.16,
        "智能增强层（脱敏样本积累后分阶段接入 · 向后兼容）",
        fontsize=8.4,
        fontweight="bold",
        color="#7F5F00",
        zorder=4,
    )
    ax.text(
        L + 0.42,
        3.88,
        "XGBoost / LightGBM 择优调用 ｜ 集成学习基模型权重自适应 ｜ 农企—农户—农资关系图谱（GNN） ｜ 模型选择控制器",
        fontsize=7.3,
        color="#7F5F00",
        zorder=4,
    )

    # ===== 数据层 =====
    box(ax, L, 1.05, W, 2.25, "", C_DATA, C_DATA_E, radius=0.03)
    ax.text(
        L + 0.22, 3.08, "数据层（替代数据采集与预处理）", fontsize=11.5, fontweight="bold", color=C_DATA_E, zorder=4
    )
    for i, txt in enumerate(["信贷员录入", "批量表格导入", "政务系统对接", "农户自主填报"]):
        box(ax, L + 0.25 + i * 2.167, 2.50, 2.0, 0.42, txt, "#FFFFFF", C_DATA_E, fontsize=9)
    box(
        ax,
        L + 0.25,
        1.85,
        8.5,
        0.55,
        "预处理模块：字段校验 · 量纲归一 · 缺失值标记 · 主体归集与档案化",
        "#FFFFFF",
        C_DATA_E,
        fontsize=9.3,
    )
    box(
        ax,
        L + 0.25,
        1.18,
        8.5,
        0.55,
        "存储层：MySQL 8（业务数据 + 指标配置 + 评估记录）｜Docker Compose 容器化部署",
        "#FFFFFF",
        C_DATA_E,
        fontsize=9.3,
    )

    # 层间箭头
    arrow(ax, (L + W / 2, 3.30), (L + W / 2, 3.55), color="#404040", lw=2.0)
    arrow(ax, (L + W / 2, 6.70), (L + W / 2, 7.05), color="#404040", lw=2.0)
    ax.text(L + W / 2 + 0.12, 3.42, "指标数据 / 特征输入", fontsize=8.0, color="#404040", va="center")
    ax.text(L + W / 2 + 0.12, 6.87, "评分结果 / 授信建议", fontsize=8.3, color="#404040", va="center")

    # ===== 右侧支撑模块 =====
    box(
        ax,
        SX,
        5.52,
        SW,
        1.72,
        "指标配置库\n\n3,020 条替代指标\n10 大类 · 689 细分类别\n五级路径结构\n（可在线配置）",
        C_SIDE,
        C_SIDE_E,
        fontsize=8.8,
    )
    box(
        ax,
        SX,
        3.52,
        SW,
        1.72,
        "模型监控\n\nAUC / KS / 召回率\nPSI 群体稳定性\n（PSI>0.1 触发再校准）\n季度监控",
        C_SIDE,
        C_SIDE_E,
        fontsize=8.8,
    )
    box(
        ax,
        SX,
        1.52,
        SW,
        1.72,
        "模型训练与评测\n\nIV / WOE / Logistic\nSMOTE 不平衡处理\n5 折分层交叉验证\nROC-KS 曲线",
        C_SIDE,
        C_SIDE_E,
        fontsize=8.8,
    )
    arrow(ax, (SX, 6.38), (L + W, 6.38), color=C_SIDE_E, lw=1.6)
    arrow(ax, (SX, 4.38), (L + W, 5.20), color=C_SIDE_E, lw=1.6)
    arrow(ax, (SX, 2.38), (L + W, 4.00), color=C_SIDE_E, lw=1.6)

    fig.savefig(OUT_DIR / "图3.1-系统总体架构图.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[ok] 图3.1-系统总体架构图.png")


# ---------------------------------------------------------------- 图 3.2
def fig_flow():
    fig, ax = plt.subplots(figsize=(9.5, 12.6), dpi=200)
    ax.set_xlim(0, 9.5)
    ax.set_ylim(0, 12.6)
    ax.axis("off")

    ax.text(
        4.75, 12.25, "图3.2  信贷员操作流程图", ha="center", va="center", fontsize=16, fontweight="bold", color=C_TITLE
    )

    CW = 4.3  # 主流程框宽
    CX = 0.75  # 主流程左边界
    RX = CX + CW + 0.2  # 右侧「说明 / 分支」起始 x

    def fbox(y, h, text, fc=C_FLOW, ec=C_FLOW_E, fs=10, bold=False, w=CW, x=CX):
        box(ax, x, y, w, h, text, fc, ec, fontsize=fs, bold=bold)

    def down(y_from, y_to, text="", fs=8.3, color="#404040"):
        arrow(ax, (CX + CW / 2, y_from), (CX + CW / 2, y_to), color=color, lw=1.6)
        if text:
            ax.text(CX + CW / 2 + 0.12, (y_from + y_to) / 2, text, fontsize=fs, color=color, va="center")

    # 1
    fbox(11.45, 0.6, "① 登录系统 · 选择业务类型与经营区域", fc="#E2EFDA", ec=C_DATA_E)
    down(11.45, 11.05)
    # 2
    fbox(10.45, 0.6, "② 录入/导入主体基本信息\n（涉农主体身份、经营规模、区域）")
    ax.text(RX, 10.75, "支持手动录入\n与批量导入", fontsize=8, color="#7F5F00", va="center")
    down(10.45, 10.05)
    # 3
    fbox(9.45, 0.6, "③ 系统按所选营业类型\n动态加载对应指标树")
    ax.text(RX, 9.75, "指标树按五级结构\n自动展开，隐藏无关项", fontsize=8, color="#7F5F00", va="center")
    down(9.45, 9.05)
    # 4
    fbox(8.45, 0.6, "④ 逐项填写指标值\n（数值/枚举/布尔/文本）")
    ax.text(RX, 8.75, "必填校验：\n仅提交后提示、填写即清除", fontsize=8, color="#7F5F00", va="center")
    down(8.45, 8.05)
    # 5
    fbox(7.45, 0.6, "⑤ 提交评估", fc="#FFF2CC", ec=C_SIDE_E, bold=True)
    down(7.45, 6.95)
    # 6 判定
    box(ax, CX, 6.15, CW, 0.8, "⑥ 一票否决红线校验", "#FCE4D6", C_MODEL_E, fontsize=10, bold=True)
    down(
        6.15,
        5.65,
        "",
    )
    # 否决分支（置于右侧，避免越界）
    arrow(ax, (CX + CW, 6.55), (RX, 6.55), color=C_VETO_E, lw=1.6)
    box(
        ax,
        RX,
        5.72,
        2.95,
        1.65,
        "命中红线 → 终止评估\n\n判定「高风险」· 不予授信\n输出命中项清单",
        C_VETO,
        C_VETO_E,
        fontsize=8.8,
    )

    # 7 打分
    fbox(5.05, 0.6, "⑦ 分维度逐项打分\n（分段计分 / 按档映射 / 达标满分）")
    down(5.05, 4.65, "未命中")
    # 8 加权
    fbox(4.05, 0.6, "⑧ 层级权重 × 星级归一 加权合成")
    ax.text(
        RX, 4.35, "权重 0.35/0.28/0.22/0.15/0.10\n星级归一以 500 分为锚点", fontsize=8, color="#7F5F00", va="center"
    )
    down(4.05, 3.65)
    # 9 混合
    box(ax, CX, 2.85, CW, 0.8, "⑨ 数据层分位校准（若模型可用）", C_BLEND, C_BLEND_E, fontsize=9.5, bold=True)
    down(2.85, 2.45)
    # 10 结果
    box(
        ax,
        CX,
        1.5,
        CW,
        1.0,
        "⑩ 输出结果：信用评分（0–1000）· 风险等级\n建议授信额度 · 利率 · 关键扣分因子",
        fc="#C6E0B4",
        ec=C_OK_E,
        fontsize=9.3,
        bold=True,
    )
    down(1.5, 1.15)
    fbox(0.55, 0.6, "11. 信贷员结合实地核查形成审批意见", fc="#E2EFDA", ec=C_DATA_E)
    ax.text(CX + CW / 2, 0.25, "全流程耗时：录入后 3 分钟内输出结果", ha="center", fontsize=8.5, color="#7F5F00")

    # 混合引擎说明（右侧）
    box(
        ax,
        RX,
        2.5,
        2.95,
        1.45,
        "分位校准规则\n\n≤15% → 0.5专家 + 0.5数据\n≥85% → 0.9专家 + 0.1数据\n中间区段 → 沿用专家分",
        C_BLEND,
        C_BLEND_E,
        fontsize=8,
    )

    fig.savefig(OUT_DIR / "图3.2-操作流程图.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("[ok] 图3.2-操作流程图.png")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"输出目录: {OUT_DIR}")
    fig_architecture()
    fig_flow()
