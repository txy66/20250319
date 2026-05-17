"""
charts/pie_chart.py - 支出分类占比饼图

使用 pyecharts 生成南丁格尔玫瑰图，展示各支出分类占比。
"""

from pyecharts.charts import Pie
from pyecharts import options as opts


def generate_expense_pie_chart(data: list[dict]) -> str:
    """
    生成本月支出分类占比饼图。

    Args:
        data: get_expense_by_category() 返回的列表

    Returns:
        HTML 字符串
    """
    # 准备数据对：["分类名", 金额]
    pairs = [[f"{item['icon']} {item['category']}", item["amount"]] for item in data]

    pie = (
        Pie(init_opts=opts.InitOpts(
            width="100%",
            height="350px",
            theme="light",
        ))
        .add(
            series_name="支出",
            data_pair=pairs,
            radius=["20%", "65%"],
            center=["50%", "55%"],
            rosetype="radius",
            label_opts=opts.LabelOpts(
                formatter="{b}: {d}%",
                font_size=12,
            ),
            tooltip_opts=opts.TooltipOpts(
                formatter="{b}: {c} 元 ({d}%)"
            ),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="支出分类占比"),
            legend_opts=opts.LegendOpts(
                orient="vertical",
                pos_left="left",
                pos_top="15%",
            ),
        )
        .set_series_opts(
            label_opts=opts.LabelOpts(formatter="{b}: {d}%"),
        )
    )

    return pie.render_embed()
