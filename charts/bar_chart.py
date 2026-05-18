"""
charts/bar_chart.py - 月度收入 vs 支出对比柱状图

使用 pyecharts 生成近 6 个月的收入/支出对比柱状图。
"""

from pyecharts.charts import Bar
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode


def generate_monthly_bar_chart(data: list[dict]) -> str:
    """
    生成月度收入 vs 支出对比柱状图（近6个月）。

    Args:
        data: get_monthly_stats() 返回的列表（取最近6条）

    Returns:
        HTML 字符串
    """
    # 只取最近 6 个月
    recent = data[-6:] if len(data) >= 6 else data
    months = [item["month"] for item in recent]
    incomes = [item["income"] for item in recent]
    expenses = [item["expense"] for item in recent]
    balances = [item["balance"] for item in recent]

    bar = (
        Bar(init_opts=opts.InitOpts(
            width="100%",
            height="350px",
            theme="light",
        ))
        .add_xaxis(months)
        .add_yaxis(
            "收入",
            incomes,
            itemstyle_opts=opts.ItemStyleOpts(color="#22c55e"),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            "支出",
            expenses,
            itemstyle_opts=opts.ItemStyleOpts(color="#ef4444"),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="月度收支对比",
                subtitle="近6个月",
                title_textstyle_opts=opts.TextStyleOpts(font_size=15),
                subtitle_textstyle_opts=opts.TextStyleOpts(font_size=11, color="#94a3b8"),
                item_gap=4,
            ),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                formatter=(
                    "{b}<br/>"
                    "收入：{c0} 元<br/>"
                    "支出：{c1} 元"
                ),
            ),
            legend_opts=opts.LegendOpts(
                pos_bottom="2%",
                item_width=18,
                item_height=10,
                textstyle_opts=opts.TextStyleOpts(font_size=11),
            ),
            xaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(rotate=30, font_size=10),
            ),
            yaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(formatter="{value} 元", font_size=10),
            ),
        )
    )

    # 调整绘图区域边距，避免标题/图例与图表重叠
    bar.options["grid"] = {"top": "18%", "bottom": "14%", "left": "10%", "right": "8%"}

    return bar.render_embed()
