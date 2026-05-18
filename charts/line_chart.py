"""
charts/line_chart.py - 收支趋势折线图

根据时段粒度（本周/本月/本年）生成对应的收入/支出/净利润折线图。
"""

from pyecharts.charts import Line
from pyecharts import options as opts


def generate_trend_chart(
    data: list[dict],
    title: str = "收支趋势",
    subtitle: str = "",
    x_label_key: str = "month",
) -> str:
    """
    生成收支趋势折线图。

    Args:
        data: 统计数据列表，每项需含 income/expense/balance 和 x_label_key 字段
        title: 图表标题
        subtitle: 副标题
        x_label_key: x轴标签的 key（"month" / "label" / "week"）

    Returns:
        HTML 字符串
    """
    labels = [item[x_label_key] for item in data]
    incomes = [item["income"] for item in data]
    expenses = [item["expense"] for item in data]
    balances = [item["balance"] for item in data]

    # x轴标签旋转角度，标签多时旋转
    rotate = 30 if len(labels) > 10 else 0

    line = (
        Line(init_opts=opts.InitOpts(
            width="100%",
            height="350px",
            theme="light",
        ))
        .add_xaxis(labels)
        .add_yaxis(
            "收入",
            incomes,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=3),
            itemstyle_opts=opts.ItemStyleOpts(color="#22c55e"),
            markpoint_opts=opts.MarkPointOpts(
                data=[opts.MarkPointItem(type_="max", name="最大收入")]
            ),
        )
        .add_yaxis(
            "支出",
            expenses,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=3),
            itemstyle_opts=opts.ItemStyleOpts(color="#ef4444"),
            markpoint_opts=opts.MarkPointOpts(
                data=[opts.MarkPointItem(type_="max", name="最大支出")]
            ),
        )
        .add_yaxis(
            "净利润",
            balances,
            label_opts=opts.LabelOpts(is_show=False),
            linestyle_opts=opts.LineStyleOpts(width=2, type_="dashed"),
            itemstyle_opts=opts.ItemStyleOpts(color="#3b82f6"),
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
                    "支出：{c1} 元<br/>"
                    "净利润：{c2} 元"
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
            datazoom_opts=[opts.DataZoomOpts(type_="inside")],
        )
    )

    line.options["grid"] = {"top": "18%", "bottom": "14%", "left": "10%", "right": "8%"}

    return line.render_embed()
