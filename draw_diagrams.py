import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

OUT = Path(__file__).resolve().parent / "paper_figures"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    'font.family': ['SimHei'],
    'font.size': 10,
    'axes.unicode_minus': False,
    'figure.dpi': 300,
    'savefig.dpi': 300,
})

C = {
    'data': '#2C3E50',
    'service': '#2980B9',
    'display': '#16A085',
    'arrow': '#566573',
    'box_bg': '#F2F3F4',
    'border': '#B2BABB',
    'white': '#FFFFFF',
    'highlight': '#C0392B',
    'purple': '#8E44AD',
    'orange': '#F39C12',
}

def draw_architecture():
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')

    layer_y = {'data': 1.0, 'service': 3.5, 'display': 6.0}
    layer_h = 1.8
    layer_labels = {'data': '数据层', 'service': '服务层', 'display': '展示层'}
    layer_colors = {'data': C['data'], 'service': C['service'], 'display': C['display']}

    for key, y in layer_y.items():
        rect = FancyBboxPatch((0.5, y), 11, layer_h,
                               boxstyle="round,pad=0.15",
                               facecolor=C['box_bg'], edgecolor=layer_colors[key],
                               linewidth=2.0, alpha=0.3)
        ax.add_patch(rect)
        ax.text(0.8, y + layer_h - 0.3, layer_labels[key],
                fontsize=14, fontweight='bold', color=layer_colors[key])

    data_boxes = [
        (1.0, 1.3, 2.2, 1.0, 'SQLite\nair_hsr_pricing.db'),
        (3.8, 1.3, 2.2, 1.0, 'Parquet\nfeature_matrix_v5'),
        (6.6, 1.3, 2.2, 1.0, 'CSV\n12个评估文件'),
        (9.4, 1.3, 2.2, 1.0, 'JSON\nxgb_model_v5'),
    ]
    for x, y, w, h, txt in data_boxes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                               facecolor=C['white'], edgecolor=C['data'], linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, txt, ha='center', va='center', fontsize=8.5, color=C['data'])

    svc_boxes = [
        (1.0, 3.8, 2.5, 1.0, '数据查询服务\ndata_loader.py'),
        (4.0, 3.8, 2.5, 1.0, '模型预测服务\nmodel_service.py'),
        (7.0, 3.8, 2.5, 1.0, 'SHAP解释服务\nTreeExplainer'),
        (10.0, 3.8, 1.8, 1.0, 'FastAPI\n路由层'),
    ]
    for x, y, w, h, txt in svc_boxes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                               facecolor=C['white'], edgecolor=C['service'], linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, txt, ha='center', va='center', fontsize=8.5, color=C['service'])

    disp_boxes = [
        (1.0, 6.3, 2.2, 1.0, '票价分析\n3个页面'),
        (3.8, 6.3, 2.2, 1.0, '空铁竞争\n3个页面'),
        (6.6, 6.3, 2.2, 1.0, '模型洞察\n2个页面'),
        (9.4, 6.3, 2.2, 1.0, '定价系统\n1个页面'),
    ]
    for x, y, w, h, txt in disp_boxes:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                               facecolor=C['white'], edgecolor=C['display'], linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, txt, ha='center', va='center', fontsize=8.5, color=C['display'])

    ax.annotate('', xy=(6, 3.5), xytext=(6, 2.8),
                arrowprops=dict(arrowstyle='->', color=C['arrow'], lw=2))
    ax.text(6.3, 3.1, '查询/加载', fontsize=8, color=C['arrow'])

    ax.annotate('', xy=(6, 6.0), xytext=(6, 5.3),
                arrowprops=dict(arrowstyle='->', color=C['arrow'], lw=2))
    ax.text(6.3, 5.6, 'RESTful API (JSON)', fontsize=8, color=C['arrow'])

    ax.text(6, 0.3, '图6-1  系统总体架构图', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUT / 'fig6_1_architecture.png', bbox_inches='tight', facecolor='white')
    plt.close()
    print("图6-1 已保存")


def draw_predict_flow():
    fig, ax = plt.subplots(figsize=(14, 4.5))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 4.5)
    ax.axis('off')

    steps = [
        (0.3,  '输入参数',        '航班号+出发日期\n+提前天数',     C['data']),
        (2.2,  '航班验证',        '查询Parquet\n验证航班存在',      C['service']),
        (4.1,  '特征行构建',      '思路C：日期特征+\n高铁历史均值',  C['service']),
        (6.0,  'XGBoost推理',    '42维特征→\n预测价格',            C['highlight']),
        (7.9,  'SHAP计算',       'TreeExplainer\n边际贡献分解',     C['purple']),
        (9.8,  '置信区间',        '1.96×RMSE×0.7\n95%区间',        C['orange']),
        (11.7, 'JSON封装',        '预测价+SHAP+\n区间+建议',        C['display']),
    ]

    box_w, box_h = 1.6, 2.2
    y_center = 2.2

    for i, (x, title, desc, color) in enumerate(steps):
        y = y_center - box_h/2
        rect = FancyBboxPatch((x, y), box_w, box_h, boxstyle="round,pad=0.12",
                               facecolor=C['white'], edgecolor=color, linewidth=1.8)
        ax.add_patch(rect)
        ax.text(x + box_w/2, y + box_h - 0.35, title,
                ha='center', va='center', fontsize=9.5, fontweight='bold', color=color)
        ax.text(x + box_w/2, y + box_h/2 - 0.2, desc,
                ha='center', va='center', fontsize=7.5, color=C['data'], linespacing=1.4)

        if i < len(steps) - 1:
            next_x = steps[i+1][0]
            ax.annotate('', xy=(next_x, y_center), xytext=(x + box_w, y_center),
                        arrowprops=dict(arrowstyle='->', color=C['arrow'], lw=1.8))

    ax.text(7, 0.3, '图6-2  预测服务处理流程', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUT / 'fig6_2_predict_flow.png', bbox_inches='tight', facecolor='white')
    plt.close()
    print("图6-2 已保存")


def draw_page_layout():
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis('off')

    sidebar = FancyBboxPatch((0, 0.5), 1.8, 6.0, boxstyle="round,pad=0.05",
                              facecolor=C['data'], edgecolor=C['data'], linewidth=1.5, alpha=0.9)
    ax.add_patch(sidebar)
    ax.text(0.9, 6.0, '京沪空铁\n定价', ha='center', va='center',
            fontsize=10, fontweight='bold', color=C['white'])
    menu_items = ['首页', '数据全景', '票价分析', '空铁竞争', '模型洞察', '定价系统']
    for i, item in enumerate(menu_items):
        ax.text(0.9, 5.2 - i*0.7, item, ha='center', va='center',
                fontsize=8, color='#B2BABB')

    header = FancyBboxPatch((2.0, 5.8), 7.8, 0.7, boxstyle="round,pad=0.05",
                             facecolor=C['box_bg'], edgecolor=C['border'], linewidth=1.0)
    ax.add_patch(header)
    ax.text(5.9, 6.15, '定价规则解读  |  首页 > 定价系统 > 定价规则解读',
            ha='center', va='center', fontsize=8.5, color=C['data'])

    form = FancyBboxPatch((2.0, 4.7), 7.8, 0.95, boxstyle="round,pad=0.08",
                           facecolor=C['white'], edgecolor=C['border'], linewidth=1.0)
    ax.add_patch(form)
    ax.text(2.3, 5.3, '查询表单', fontsize=9, fontweight='bold', color=C['data'])
    ax.text(2.3, 5.0, '航班号[搜索框]    出发日期[日期选择]    提前天数[数字输入]    [查询]',
            fontsize=7.5, color=C['data'])

    areas = [
        (2.0, 2.8, 3.8, 1.7, '预测结果区\n预测价 | 基准价 | 偏移\n置信区间 | 购买建议', C['highlight']),
        (6.0, 2.8, 3.8, 1.7, '价格曲线区\n1-30天预测价格折线\n最优购买时点标注', C['service']),
        (2.0, 0.7, 3.8, 1.9, 'SHAP归因瀑布图\n红色=推高因素\n蓝色=压低因素', C['purple']),
        (6.0, 0.7, 3.8, 1.9, '类别贡献对比\n时间|节假日|航班|高铁\n绝对贡献 vs 净贡献', C['display']),
    ]
    for x, y, w, h, txt, color in areas:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                               facecolor=C['white'], edgecolor=color, linewidth=1.5, linestyle='--')
        ax.add_patch(rect)
        ax.text(x + w/2, y + h/2, txt, ha='center', va='center',
                fontsize=8, color=color, linespacing=1.5)

    ax.text(5.9, 0.2, '图6-3  定价规则解读页面布局', ha='center', fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(OUT / 'fig6_3_page_layout.png', bbox_inches='tight', facecolor='white')
    plt.close()
    print("图6-3 已保存")


if __name__ == '__main__':
    draw_architecture()
    draw_predict_flow()
    draw_page_layout()
    print(f"\n三张图已保存到 {OUT}")
