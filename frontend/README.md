# Aevum 薪火 OS - 前端

基于 Next.js + React 19 + TypeScript + Tailwind CSS 构建的前端界面。

> **注意**：当前版本 Next.js 有破坏性变更，API 和约定可能与训练数据不同。开发前请查阅 `node_modules/next/dist/docs/` 中的文档。

## 快速开始

```bash
# 安装依赖
npm install

# 开发服务器（热重载）
npm run dev
# 访问 http://localhost:3000

# 构建
npm run build

# 启动生产服务器
npm start
```

## 代码检查

```bash
# Lint
npm run lint

# 类型检查
npx tsc --noEmit

# 测试
npm test -- --ci --coverage --watchAll=false
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址（默认 `http://localhost:8000`） |

## 技术栈

- Next.js (App Router)
- React 19
- TypeScript (strict mode)
- Tailwind CSS + shadcn/ui
- ReactFlow (图谱可视化)
- Zustand (状态管理)
