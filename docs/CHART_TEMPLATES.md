# ECharts配置模板

## 模板1：双Y轴时序图（带阴影）

```typescript
export const dualAxisTimeConfig = (data: any) =&gt; ({
  tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
  legend: { top: 10, right: 10, backgroundColor: 'rgba(255,255,255,0.9)' },
  grid: { top: 60, right: 80, bottom: 60, left: 80 },
  xAxis: { 
    type: 'category', 
    data: data.dates,
    axisLabel: { formatter: (v: string) =&gt; v.slice(5) } // 显示MM-DD
  },
  yAxis: [
    { 
      type: 'value', 
      name: '航空均价（元）',
      position: 'left',
      axisLine: { lineStyle: { color: '#2C3E50' } }
    },
    { 
      type: 'value', 
      name: 'RPA',
      position: 'right',
      axisLine: { lineStyle: { color: '#2980B9' } },
      splitLine: { show: false }
    }
  ],
  series: [
    {
      name: '航空均价',
      type: 'line',
      data: data.airPrices,
      smooth: true,
      lineStyle: { color: '#2C3E50', width: 2 },
      itemStyle: { color: '#2C3E50' }
    },
    {
      name: 'RPA',
      type: 'line',
      yAxisIndex: 1,
      data: data.rpaValues,
      smooth: true,
      lineStyle: { color: '#2980B9', width: 2, type: 'dashed' },
      itemStyle: { color: '#2980B9' }
    }
  ],
  // 周末/节假日阴影使用graphic或markArea实现
});
```
## 模板2：直方图+KDE

```typescript
export const priceDistributionConfig = (data: any) => ({
  tooltip: { trigger: 'axis' },
  xAxis: { 
    type: 'value', 
    name: '票价（元）',
    min: 0,
    max: 2500,
    interval: 100
  },
  yAxis: [
    { type: 'value', name: '频数', position: 'left' },
    { type: 'value', name: '密度', position: 'right', splitLine: { show: false } }
  ],
  series: [
    {
      name: '票价分布',
      type: 'bar',
      data: data.histogram,
      barWidth: '95%',
      itemStyle: { color: 'rgba(41, 128, 185, 0.6)' }
    },
    {
      name: 'KDE',
      type: 'line',
      yAxisIndex: 1,
      data: data.kde,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#C0392B', width: 2 }
    }
  ],
  markLine: {
    silent: true,
    data: [
      { xAxis: data.median, label: { formatter: '中位数={c}元' }, lineStyle: { type: 'dashed', color: '#2980B9' } },
      { xAxis: data.mean, label: { formatter: '均值={c}元' }, lineStyle: { type: 'dashed', color: '#2C3E50' } }
    ]
  }
});
```

## 模板3：热力图

```typescript
export const heatmapConfig = (data: any) => ({
  tooltip: { position: 'top' },
  grid: { top: 60, right: 80, bottom: 60, left: 80 },
  xAxis: { 
    type: 'category', 
    data: ['0-2天', '3-6天', '7-13天', '14-20天', '21-30天', '30天+'],
    name: '提前期'
  },
  yAxis: { 
    type: 'category', 
    data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    name: '星期'
  },
  visualMap: {
    min: 600,
    max: 1200,
    calculable: true,
    orient: 'horizontal',
    left: 'center',
    bottom: 10,
    inRange: {
      color: ['#2980B9', '#F2F3F4', '#C0392B']
    }
  },
  series: [{
    name: '平均票价',
    type: 'heatmap',
    data: data.heatmapData,
    label: { show: true, formatter: '{c}' },
    emphasis: {
      itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' }
    }
  }]
});
```

## 模板4：SHAP蜂群图（散点模拟）

```typescript
export const shapBeeswarmConfig = (data: any) => ({
  tooltip: {
    formatter: (params: any) => {
      return `${params.data.feature}<br/>SHAP值: ${params.data.shap.toFixed(2)}<br/>特征值: ${params.data.value.toFixed(2)}`;
    }
  },
  xAxis: { type: 'value', name: 'SHAP值（对预测的影响）' },
  yAxis: { 
    type: 'category', 
    data: data.features,
    inverse: true // 重要性从上到下
  },
  series: data.features.map((feat: string, idx: number) => ({
    name: feat,
    type: 'scatter',
    data: data.shapValues[idx].map((d: any) => [d.shap, idx, d.value]),
    symbolSize: 6,
    itemStyle: {
      color: (params: any) => {
        const val = params.data[2];
        // 红=高值，蓝=低值
        return val > 0.5 ? '#C0392B' : '#2980B9';
      },
      opacity: 0.7
    }
  }))
});
```

## 模板5：箱线图

```typescript
export const boxplotConfig = (data: any) => ({
  tooltip: { trigger: 'item' },
  xAxis: { 
    type: 'category', 
    data: data.categories,
    name: '提前期区间'
  },
  yAxis: { type: 'value', name: '票价（元）' },
  series: [{
    name: '票价分布',
    type: 'boxplot',
    data: data.boxData,
    itemStyle: { color: 'rgba(41, 128, 185, 0.3)', borderColor: '#2980B9' },
    // 中位数线样式在ECharts boxplot中通过data配置
  }],
  markLine: {
    silent: true,
    data: [{ yAxis: data.overallMedian, label: { formatter: '全样本中位数' }, lineStyle: { type: 'dashed', color: '#C0392B' } }]
  }
});
```