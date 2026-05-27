-- Personal-KB PostgreSQL 初始化脚本
-- 此脚本在容器首次启动时自动执行

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 创建数据库（如果不存在）
-- 注：POSTGRES_DB 环境变量已自动创建数据库，此处仅作备份逻辑
SELECT 'CREATE DATABASE personal_kb'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'personal_kb')\gexec

-- 设置默认搜索路径
ALTER DATABASE personal_kb SET search_path TO public;

-- 记录初始化完成
DO $$
BEGIN
    RAISE NOTICE 'PostgreSQL 初始化完成：数据库 personal_kb 已就绪';
END $$;
