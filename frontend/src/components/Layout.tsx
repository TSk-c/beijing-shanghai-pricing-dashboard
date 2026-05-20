import { useEffect, useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { App as AntApp, Breadcrumb, Drawer, Layout as AntLayout, Menu, Spin } from 'antd';
import type { BreadcrumbProps, MenuProps } from 'antd';
import {
  BarChartOutlined,
  HomeOutlined,
  LineChartOutlined,
  MenuOutlined,
  PieChartOutlined,
  RocketOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { BG_SECONDARY, BORDER, PRIMARY, TEXT_PRIMARY } from '../constants/colors';
import { useDashboardStore } from '../store/dashboardStore';
import { setMessageInstance } from '../services/messageHolder';

const { Header, Sider, Content } = AntLayout;

const BREADCRUMB_BY_PATH: Record<string, string[]> = {
  '/': ['首页'],
  '/data-overview': ['数据全景'],
  '/price-analysis/distribution': ['票价分析', '票价分布'],
  '/price-analysis/advance-booking': ['票价分析', '提前天数分析'],
  '/price-analysis/airline-heatmap': ['票价分析', '航司与热力图'],
  '/rail-air-competition/rpa-analysis': ['空铁竞争', 'RPA综合分析'],
  '/rail-air-competition/air-hsr-comparison': ['空铁竞争', '空铁价格与余票'],
  '/rail-air-competition/holiday-expo': ['空铁竞争', '节假日与展会'],
  '/model-insights/comparison': ['模型洞察', '模型对比'],
  '/model-insights/performance': ['模型洞察', 'XGBoost性能'],
  '/pricing-system/single-flight': ['定价系统', '定价规则解读'],
};

const PAGE_TITLE_BY_PATH: Record<string, string> = {
  '/': '首页 - 京沪空铁定价',
  '/data-overview': '数据全景 - 京沪空铁定价',
  '/price-analysis/distribution': '票价分布 - 京沪空铁定价',
  '/price-analysis/advance-booking': '提前天数分析 - 京沪空铁定价',
  '/price-analysis/airline-heatmap': '航司与热力图 - 京沪空铁定价',
  '/rail-air-competition/rpa-analysis': 'RPA综合分析 - 京沪空铁定价',
  '/rail-air-competition/air-hsr-comparison': '空铁价格与余票 - 京沪空铁定价',
  '/rail-air-competition/holiday-expo': '节假日与展会 - 京沪空铁定价',
  '/model-insights/comparison': '模型对比 - 京沪空铁定价',
  '/model-insights/performance': 'XGBoost性能 - 京沪空铁定价',
  '/pricing-system/single-flight': '定价规则解读 - 京沪空铁定价',
};

const MENU_ITEMS: MenuProps['items'] = [
  { key: '/', icon: <HomeOutlined />, label: '首页' },
  { key: '/data-overview', icon: <PieChartOutlined />, label: '数据全景' },
  {
    key: 'grp-price',
    icon: <BarChartOutlined />,
    label: '票价分析',
    children: [
      { key: '/price-analysis/distribution', label: '票价分布' },
      { key: '/price-analysis/advance-booking', label: '提前天数分析' },
      { key: '/price-analysis/airline-heatmap', label: '航司与热力图' },
    ],
  },
  {
    key: 'grp-rail',
    icon: <LineChartOutlined />,
    label: '空铁竞争',
    children: [
      { key: '/rail-air-competition/rpa-analysis', label: 'RPA综合分析' },
      { key: '/rail-air-competition/air-hsr-comparison', label: '空铁价格与余票' },
      { key: '/rail-air-competition/holiday-expo', label: '节假日与展会' },
    ],
  },
  {
    key: 'grp-model',
    icon: <ThunderboltOutlined />,
    label: '模型洞察',
    children: [
      { key: '/model-insights/comparison', label: '模型对比' },
      { key: '/model-insights/performance', label: 'XGBoost性能' },
    ],
  },
  {
    key: 'grp-pricing',
    icon: <RocketOutlined />,
    label: '定价系统',
    children: [{ key: '/pricing-system/single-flight', label: '定价规则解读' }],
  },
];

const MOBILE_BREAKPOINT = 768;

export function Layout() {
  const { message: antMessage } = AntApp.useApp();
  const location = useLocation();
  const navigate = useNavigate();
  const loading = useDashboardStore((s) => s.loading);
  const setPage = useDashboardStore((s) => s.setPage);
  const [routeSpin, setRouteSpin] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth < MOBILE_BREAKPOINT);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    setMessageInstance(antMessage);
  }, [antMessage]);

  useEffect(() => {
    const onResize = () => setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    setPage(location.pathname);
  }, [location.pathname, setPage]);

  useEffect(() => {
    document.title = PAGE_TITLE_BY_PATH[location.pathname] ?? '京沪空铁定价';
  }, [location.pathname]);

  useEffect(() => {
    let cancelled = false;
    const startId = window.setTimeout(() => {
      if (!cancelled) setRouteSpin(true);
    }, 0);
    const endId = window.setTimeout(() => {
      if (!cancelled) setRouteSpin(false);
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(startId);
      clearTimeout(endId);
    };
  }, [location.pathname]);

  const breadcrumbItems: BreadcrumbProps['items'] = useMemo(() => {
    const labels = BREADCRUMB_BY_PATH[location.pathname] ?? ['未知页面'];
    return labels.map((title) => ({ title }));
  }, [location.pathname]);

  const onMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key.startsWith('/')) {
      navigate(key);
      setDrawerOpen(false);
    }
  };

  const siderContent = (
    <>
      <div
        style={{
          height: 48,
          margin: 16,
          color: BG_SECONDARY,
          fontWeight: 600,
          fontSize: 18,
          lineHeight: '48px',
          textAlign: 'center',
        }}
      >
        京沪空铁定价
      </div>
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[location.pathname]}
        defaultOpenKeys={['grp-price', 'grp-rail', 'grp-model', 'grp-pricing']}
        style={{ background: PRIMARY, borderInlineEnd: 'none', fontWeight: 500 }}
        items={MENU_ITEMS}
        onClick={onMenuClick}
      />
    </>
  );

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      {isMobile ? (
        <Drawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          placement="left"
          width={256}
          styles={{ body: { padding: 0, background: PRIMARY } }}
        >
          {siderContent}
        </Drawer>
      ) : (
        <Sider
          width={220}
          style={{
            overflow: 'auto',
            height: '100vh',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            background: PRIMARY,
            borderRight: `1px solid ${BORDER}`,
          }}
        >
          {siderContent}
        </Sider>
      )}
      <AntLayout
        style={{
          marginLeft: isMobile ? 0 : 220,
          minHeight: '100vh',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          transition: 'margin-left 0.2s',
        }}
      >
        <Header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 1,
            padding: isMobile ? '0 12px' : '0 24px',
            background: BG_SECONDARY,
            borderBottom: `1px solid ${BORDER}`,
            display: 'flex',
            alignItems: 'center',
            height: 56,
            lineHeight: '56px',
            gap: 12,
          }}
        >
          {isMobile && (
            <MenuOutlined
              style={{ fontSize: 18, cursor: 'pointer', color: TEXT_PRIMARY }}
              onClick={() => setDrawerOpen(true)}
            />
          )}
          <Breadcrumb items={breadcrumbItems} />
        </Header>
        <Content
          style={{
            margin: 0,
            flex: 1,
            minHeight: 0,
            overflow: 'auto',
            background: BG_SECONDARY,
            color: TEXT_PRIMARY,
          }}
        >
          <Spin spinning={loading || routeSpin} tip="加载中…">
            <div style={{ minHeight: 200 }}>
              <Outlet />
            </div>
          </Spin>
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
