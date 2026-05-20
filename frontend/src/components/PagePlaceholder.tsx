import { Typography } from 'antd';

interface PagePlaceholderProps {
  /** 页面展示文案 */
  text: string;
}

/** 阶段占位页：仅展示标题类文案 */
export function PagePlaceholder({ text }: PagePlaceholderProps) {
  return (
    <div style={{ padding: 24 }}>
      <Typography.Text>{text}</Typography.Text>
    </div>
  );
}
