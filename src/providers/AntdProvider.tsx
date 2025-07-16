// components/AntdProvider.tsx hoặc /providers/AntdProvider.tsx

"use client";

import { StyleProvider } from "@ant-design/cssinjs";
import { App, ConfigProvider } from "antd";
import type { PropsWithChildren, FC } from "react";

// ⚠️ Đây là điểm QUAN TRỌNG: Patch phải nằm trong một Client Component
import "@ant-design/v5-patch-for-react-19";

const AntdProvider: FC<PropsWithChildren> = ({ children }) => {
    return (
        <StyleProvider hashPriority="high">
            <ConfigProvider>
                <App>{children}</App>
            </ConfigProvider>
        </StyleProvider>
    );
};

export default AntdProvider;
