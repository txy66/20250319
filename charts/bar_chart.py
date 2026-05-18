"""
charts/bar_chart.py - 收支对比柱状图

根据时段粒度（本周/本月/本年）生成对应的收入/支出对比柱状图。
"""

from pyecharts.charts import Bar
from pyecharts import options as opts


def generate_bar_chart(
    data: list[dict],
    title: str = "收支对比",
    subtitle: str = "",
    x_label_key: str = "month",
) -> str:
    """
    生成收支对比柱状图。

    Args:
        data: 统计数据列表，每项需含 income/expense 和 x_label_key 字段
        title: 图表标题
        subtitle: 副标题
        x_label_key: x轴标签的 key（"month" / "label" / "week"）

    Returns:
        HTML 字符串
    """
    labels = [item[x_label_key] for item in data]
    incomes = [item["income"] for item in data]
    expenses = [item["expense"] for item in data]

    # x轴标签旋转角度
    rotate = 30 if len(labels) > 10 else 0

    bar = (
        Bar(init_opts=opts.InitOpts(
            width="100%",
            height="350px",
            theme="light",
        ))
        .add_xaxis(labels)
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
                title=title,
                subtitle=subtitle,
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
                axislabel_opts=opts.LabelOpts(rotate=rotate, font_size=10),
            ),
            yaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(formatter="{value} 元", font_size=10),
            ),
        )
    )

    bar.options["grid"] = {"top": "18%", "bottom": "14%", "left": "10%", "right": "8%"}

    return bar.render_embed()
