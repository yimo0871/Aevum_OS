# Aevum（薪火）OS - 部署指南

## 开发环境

### 前置要求

- Docker Desktop（含 Docker Compose）
- Git

### 快速启动

```bash
# 1. 克隆仓库
git clone <repository-url>
cd Aevum_薪火OS

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY 等配置

# 3. 启动全部服务
docker-compose up -d

# 4. 验证服务
# 后端 API: http://localhost:8000/docs
# 前端: http://localhost:3000
# 健康检查: http://localhost:8000/health
```

### 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 数据库 + pgvector |
| Redis | 6379 | 缓存 + 任务队列 |
| Backend API | 8000 | FastAPI 后端 |
| Celery Worker | - | 异步任务处理 |
| Frontend | 3000 | Next.js 前端 |

### 数据库迁移

```bash
# 进入后端容器执行迁移
docker-compose exec backend alembic upgrade head

# 回滚迁移
docker-compose exec backend alembic downgrade -1

# 查看迁移状态
docker-compose exec backend alembic current
```

### 运行测试

```bash
# 后端测试
docker-compose exec backend pytest -v --cov=app

# 前端测试
docker-compose exec frontend npm test
```

---

## 生产环境部署

### 方式一：Docker Compose

```bash
# 1. 配置生产环境变量
cp .env.example .env
# 编辑 .env，设置生产配置：
#   APP_DEBUG=false
#   POSTGRES_PASSWORD=<strong-password>
#   SECRET_KEY=<strong-secret-key>
#   OPENAI_API_KEY=<your-key>

# 2. 启动生产环境
docker-compose -f docker-compose.prod.yml up -d

# 3. 执行数据库迁移
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### 方式二：分别部署

#### 后端部署

```bash
cd backend

# 构建 Docker 镜像
docker build -t aevum-backend .

# 运行
docker run -d \
  --name aevum-backend \
  -p 8000:8000 \
  --env-file ../.env \
  -e POSTGRES_HOST=db \
  -e REDIS_HOST=redis \
  aevum-backend
```

#### 前端部署

```bash
cd frontend

# 构建
npm run build

# 运行
npm start
# 或使用 Docker
docker build -t aevum-frontend .
docker run -d -p 3000:3000 aevum-frontend
```

### Nginx 反向代理配置

生产环境使用 Nginx 作为反向代理，配置文件已提供在 `nginx.conf`。

```bash
# 启动 Nginx（包含在 docker-compose.prod.yml 中）
docker-compose -f docker-compose.prod.yml up -d nginx
```

---

## 环境变量说明

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_ENV` | development | 运行环境 |
| `APP_DEBUG` | true | 调试模式 |
| `POSTGRES_HOST` | localhost | 数据库主机 |
| `POSTGRES_PORT` | 5432 | 数据库端口 |
| `POSTGRES_DB` | aevum | 数据库名 |
| `POSTGRES_USER` | aevum | 数据库用户 |
| `POSTGRES_PASSWORD` | - | 数据库密码 |
| `REDIS_HOST` | localhost | Redis 主机 |
| `REDIS_PORT` | 6379 | Redis 端口 |
| `OPENAI_API_KEY` | - | OpenAI API Key（用于 embedding） |
| `EMBEDDING_MODEL` | text-embedding-3-small | Embedding 模型 |
| `SECRET_KEY` | - | JWT 密钥 |
| `CORS_ORIGINS` | ["http://localhost:3000"] | CORS 允许的源 |

---

## 冷启动（Bootstrap）

首次部署后，需要生成种子经验数据：

```bash
# 生成 10,000 条种子经验（Phase 7 实现）
docker-compose exec backend python scripts/bootstrap_seeds.py
```

---

## 故障排查

### 后端无法连接数据库

```bash
# 检查数据库状态
docker-compose exec db pg_isready -U aevum

# 查看后端日志
docker-compose logs backend
```

### 前端无法连接后端

```bash
# 检查后端是否运行
curl http://localhost:8000/health

# 检查前端环境变量
cat frontend/.env.local
```

### pgvector 扩展未安装

```bash
# 进入数据库检查
docker-compose exec db psql -U aevum -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# 手动安装
docker-compose exec db psql -U aevum -c "CREATE EXTENSION IF NOT EXISTS vector;"
```
