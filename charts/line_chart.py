"""
charts/line_chart.py - 月度收支趋势折线图

使用 pyecharts 生成近 12 个月的收入/支出/净利润折线图。
"""

from pyecharts.charts import Line
from pyecharts import options as opts


def generate_monthly_trend_chart(data: list[dict]) -> str:
    """
    生成月度收支趋势折线图。

    Args:
        data: get_monthly_stats() 返回的列表

    Returns:
        HTML 字符串
    """
    months = [item["month"] for item in data]
    incomes = [item["income"] for item in data]
    expenses = [item["expense"] for item in data]
    balances = [item["balance"] for item in data]

    line = (
        Line(init_opts=opts.InitOpts(
            width="100%",
            height="350px",
            theme="light",
        ))
        .add_xaxis(months)
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
            title_opts=opts.TitleOpts(title="月度收支趋势", subtitle="近12个月"),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                formatter=(
                    "{b}<br/>"
                    "收入：{c0} 元<br/>"
                    "支出：{c1} 元<br/>"
                    "净利润：{c2} 元"
                ),
            ),
            legend_opts=opts.LegendOpts(pos_top="5%"),
            xaxis_opts=opts.AxisOpts(axislabel_opts=opts.LabelOpts(rotate=30)),
            yaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(formatter="{value} 元"),
            ),
            datazoom_opts=[opts.DataZoomOpts(type_="inside")],
        )
    )

    return line.render_embed()
