import { Skeleton, Table } from 'antd';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import { BG_PRIMARY, BORDER } from '../constants/colors';

export interface DataTableProps<T extends object> {
  columns: ColumnsType<T>;
  dataSource: T[];
  rowKey: keyof T | ((record: T) => string);
  loading?: boolean;
  pagination?: false | TablePaginationConfig;
}

/** 通用表格：排序、筛选、分页 + 加载骨架 */
export function DataTable<T extends object>({
  columns,
  dataSource,
  rowKey,
  loading = false,
  pagination = { pageSize: 10, showSizeChanger: true, pageSizeOptions: [5, 10, 20, 50] },
}: DataTableProps<T>) {
  if (loading) {
    return (
      <div
        style={{
          padding: 16,
          background: BG_PRIMARY,
          border: `1px solid ${BORDER}`,
          borderRadius: 8,
        }}
      >
        <Skeleton active title={{ width: '40%' }} paragraph={{ rows: 6 }} />
      </div>
    );
  }

  return (
    <Table<T>
      size="middle"
      bordered
      columns={columns}
      dataSource={dataSource}
      rowKey={rowKey}
      pagination={pagination}
      scroll={{ x: 'max-content' }}
      style={{ background: BG_PRIMARY }}
    />
  );
}
