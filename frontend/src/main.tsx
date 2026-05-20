import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App as AntApp, ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import App from './App';
import { PRIMARY } from './constants/colors';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: PRIMARY,
          fontSize: 17,
          fontSizeLG: 19,
          fontSizeSM: 15,
          fontSizeXL: 21,
          fontSizeHeading1: 42,
          fontSizeHeading2: 34,
          fontSizeHeading3: 26,
          fontSizeHeading4: 22,
          fontSizeHeading5: 19,
        },
      }}
    >
      <AntApp>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  </StrictMode>,
);
