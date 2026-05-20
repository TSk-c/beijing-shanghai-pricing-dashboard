import { useEffect, useState } from 'react';
import { ArrowDownOutlined, ArrowUpOutlined, MinusOutlined } from '@ant-design/icons';
import { Card, Typography } from 'antd';
import {
  BG_PRIMARY,
  BORDER,
  STATUS_DOWN,
  STATUS_UP,
  TEXT_MUTED,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
} from '../constants/colors';

export type KpiTrend = 'up' | 'down' | 'flat';

export interface KpiCardProps {
  /** 指标名称 */
  title: string;
  /** 静态主文案（无数字滚动） */
  valueText?: string;
  /** 数字动画目标值；提供时主数字区从 0 滚动到该值 */
  targetNumber?: number;
  /** 将动画中的数值格式化为展示字符串 */
  formatAnimated?: (n: number) => string;
  /** 相对变化趋势：上升红 / 下降绿 / 持平灰 */
  trend?: KpiTrend;
  /** 底部辅助说明 */
  footer?: string;
}

const DEFAULT_DURATION_MS = 900;

function useCountUp(target: number | undefined, enabled: boolean): number {
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!enabled || target == null) {
      const resetId = window.setTimeout(() => setValue(0), 0);
      return () => clearTimeout(resetId);
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DEFAULT_DURATION_MS);
      setValue(target * t);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      }
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, enabled]);

  return value;
}

export function KpiCard({
  title,
  valueText,
  targetNumber,
  formatAnimated = (n) => `${Math.round(n)}`,
  trend,
  footer,
}: KpiCardProps) {
  const animating = targetNumber != null;
  const animated = useCountUp(targetNumber, animating);
  const mainText = animating ? formatAnimated(animated) : (valueText ?? '—');

  const trendNode =
    trend === 'up' ? (
      <ArrowUpOutlined style={{ color: STATUS_UP, fontSize: 18, marginLeft: 8 }} />
    ) : trend === 'down' ? (
      <ArrowDownOutlined style={{ color: STATUS_DOWN, fontSize: 18, marginLeft: 8 }} />
    ) : trend === 'flat' ? (
      <MinusOutlined style={{ color: TEXT_MUTED, fontSize: 18, marginLeft: 8 }} />
    ) : null;

  return (
    <Card
      variant="outlined"
      style={{
        height: '100%',
        background: BG_PRIMARY,
        borderColor: BORDER,
      }}
    >
      <Typography.Text type="secondary" style={{ color: TEXT_MUTED, fontSize: 13 }}>
        {title}
      </Typography.Text>
      <div style={{ display: 'flex', alignItems: 'center', marginTop: 8, flexWrap: 'wrap' }}>
        <Typography.Title level={3} style={{ margin: 0, color: TEXT_PRIMARY, fontWeight: 700 }}>
          {mainText}
        </Typography.Title>
        {trendNode}
      </div>
      {footer ? (
        <Typography.Paragraph
          style={{ margin: '12px 0 0', color: TEXT_SECONDARY, fontSize: 12 }}
        >
          {footer}
        </Typography.Paragraph>
      ) : null}
    </Card>
  );
}
