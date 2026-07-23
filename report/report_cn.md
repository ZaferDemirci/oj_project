# 在线评测（OJ）系统

**此文件仅供参考，请查阅原始文件：report.md。此文件是用翻译app生成的。**

## 1. 项目概述

### 项目目标

本项目旨在使用Python和FastAPI构建一个功能完整的在线评测（OJ）系统。系统支持用户角色（学生、教师、管理员）、题目管理、异步代码提交与评测、基于角色的结构化日志记录、备份/恢复，以及一个可选的代码相似度检测模块。

### 已完成功能

* 用户注册、登录、登出（基于会话，bcrypt密码哈希）
* 基于角色的权限（学生、教师、管理员），支持`is_active`状态
* 题目CRUD（创建、读取、更新、删除），包含字段验证和隐藏测试用例
* 使用`asyncio.create_task`进行异步代码提交（Python）
* 多测试用例评测，使用子进程隔离
* 检测AC、WA、RE、TLE、SE
* 每个测试用例的结构化日志，基于角色进行截断和脱敏
* 敏感操作审计追踪（重判、查看完整日志、用户更新、备份/恢复）
* JSON持久化，支持原子写入和错误处理
* 管理员备份/恢复（带安全副本）
* 前端（服务端Jinja2模板），涵盖所有必要工作流
* 高级模块3：代码相似度检测（基于AST）

### 未完成功能

* 未实现内存限制（MLE未实现）
* 无Special Judge（高级1）或安全隔离（高级2）
* 仅支持Python代码

### 持久化方式

使用**JSON文件**进行数据存储。所有数据存储在`data/`目录中，用户、题目、提交记录、审计日志和相似度报告分别存放在独立文件中。使用临时文件和`os.replace()`实现原子写入。

### 已完成的高级模块

* **高级3：代码相似度检测** – 已完整实现（API + 界面）。

---

## 2. 系统架构

系统遵循分层架构，关注点分离清晰。

```
┌─────────────────────────────────────────────────────────────┐
│                     前端层                                   │
│  Jinja2模板 + 静态CSS（服务端渲染）                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      路由层                                  │
│  FastAPI路由：认证、题目、提交、日志、                         │
│  管理员、用户、相似度                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     服务层                                   │
│  业务逻辑：similarity_service.py                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    仓储层                                    │
│  使用原子I/O进行JSON文件访问（BaseRepository）                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     评测层                                   │
│  执行器（子进程）、比较器（输出标准化）、                       │
│  管理器（多测试用例逻辑）、运行器（异步任务）                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     工具层                                   │
│  依赖项（认证/权限）、密码哈希、                               │
│  脱敏（截断+路径混淆）、                                      │
│  管理员初始化                                                │
└─────────────────────────────────────────────────────────────┘
```

**架构图（简化）：**

```
用户浏览器 → FastAPI（路由） → 服务 → 仓储 → JSON文件
                  ↓
               评测器（异步）
                  ↓
               子进程（学生代码）
```

* **路由层**：FastAPI路由处理HTTP请求，应用权限依赖，并将请求委托给服务或仓储。
* **服务层**：包含业务逻辑（目前为相似度服务）。
* **仓储层**：抽象数据访问；所有文件操作均为原子操作。
* **评测层**：管理子进程执行、输出标准化和结果汇总。
* **工具层**：认证、哈希、脱敏。

前端使用Jinja2模板进行服务端渲染，因此无需独立的前端服务器。

---

## 3. 数据设计

所有数据使用Pydantic建模，并以JSON格式持久化。

### 主要模型

**用户**

```json
{
  "id": "uuid",
  "username": "字符串（3-32字符）",
  "password_hash": "bcrypt哈希",
  "role": "student | teacher | admin",
  "is_active": true,
  "created_at": "ISO时间戳",
  "updated_at": "ISO时间戳"
}
```

**题目**

```json
{
  "id": "字符串（1-32，字母数字_-）",
  "title": "字符串",
  "description": "字符串",
  "input_description": "字符串",
  "output_description": "字符串",
  "samples": [{"input": "...", "output": "..."}],
  "constraints": "字符串（可选）",
  "time_limit": 浮点数,
  "memory_limit": 整数,
  "difficulty": "easy | medium | hard",
  "tags": ["字符串"],
  "test_cases": [
    {
      "case_id": "字符串",
      "input": "字符串",
      "output": "字符串",
      "score": 整数,
      "is_hidden": 布尔值
    }
  ]
}
```

**提交记录**

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "problem_id": "字符串",
  "language": "python",
  "source_code": "字符串",
  "status": "pending | running | finished | failed",
  "result": "AC | WA | RE | TLE | SE | null",
  "score": 整数,
  "total_time": 浮点数（可选）,
  "created_at": "ISO时间戳",
  "started_at": "ISO时间戳",
  "finished_at": "ISO时间戳",
  "judge_result": {
    "result": "...",
    "score": 整数,
    "total_time": 浮点数,
    "cases": [
      {
        "case_id": "字符串",
        "result": "...",
        "score": 整数,
        "time_used": 浮点数,
        "exit_code": 整数,
        "stdout": "字符串（截断）",
        "stderr": "字符串（截断）",
        "input_data": "字符串（截断）",
        "expected_output": "字符串（截断）",
        "is_hidden": 布尔值
      }
    ]
  }
}
```

**审计日志**

```json
{
  "id": "uuid",
  "operator_id": "uuid",
  "action": "VIEW_FULL_JUDGE_LOG | REJUDGE_SUBMISSION | UPDATE_USER_ROLE | DISABLE_USER | CREATE_BACKUP | RESTORE_BACKUP",
  "target_type": "submission | user | problem | backup",
  "target_id": "字符串（可选）",
  "success": 布尔值,
  "detail": "字符串（可选）",
  "created_at": "ISO时间戳"
}
```

**相似度报告**（存储在`similarity_reports.json`中，key为problem_id）

```json
{
  "problem_id": "P1001",
  "total_submissions": 5,
  "threshold": 0.8,
  "pairs": [
    {
      "submission_a": "uuid",
      "submission_b": "uuid",
      "similarity": 0.87,
      "method": "ast"
    }
  ],
  "created_at": "ISO时间戳"
}
```

## 4. 核心实现

### 异步评测器

当创建提交记录时（`POST /api/submissions`），端点立即返回HTTP 202和提交ID。评测器作为后台任务使用`asyncio.create_task(run_judge(submission.id))`启动。

*`run_judge`协程（`app/judge/runner.py`）将提交状态更新为`running`，调用评测器（`app/judge/manager.py`），存储结构化结果，并将状态设置为`finished`或`failed`。

### 子进程执行与终止

每个测试用例在隔离的临时目录中使用`asyncio.to_thread(subprocess.run)`（`app/judge/executor.py`）执行。子进程通过stdin运行学生的`main.py`并传入测试输入。使用`subprocess.run`的`timeout`参数强制超时。如果超时到期，捕获`TimeoutExpired`异常，测试用例标记为TLE。子进程由超时机制自动终止。

### 结果检测逻辑

* **AC**：所有测试用例通过。
* **WA**：程序退出码为0但输出不同（标准化后）。
* **RE**：程序退出码非零。
* **TLE**：程序超过时间限制。
* **SE**：评测器本身遇到错误（例如，题目缺失、源代码无效）。

在比较之前，在`app/judge/comparator.py`中应用标准化（换行符、尾随空格）。

### 输出标准化

在`app/judge/comparator.py`中实现（`normalize_output`和`compare_outputs`）：

1. `\r\n`和`\r` → `\n`
2. 移除每行的尾随空格和制表符
3. 移除尾随空行
4. 保留前导空格和内部空格

### 权限检查

权限在两个层级强制执行：

* **依赖注入**（`app/utils/dependencies.py`）：`get_current_user`检查登录状态、存在性和`is_active`；然后`require_teacher`和`require_admin`检查角色。
* **端点逻辑**（`app/routers/`）：即使依赖通过，端点也会执行额外的所有权检查（例如，学生不能访问他人的提交记录）。

### 隐藏测试用例

* 对于学生，`ProblemPublic`模型（`app/models/problem.py`）完全省略`test_cases`。
* 对于日志，`sanitize_for_student`（`app/utils/sanitize.py`）移除任何`is_hidden: true`的测试用例，并从非隐藏用例中剥离`input_data`和`expected_output`。

### 日志脱敏与截断

* 所有日志字段（`stdout`、`stderr`、`input_data`、`expected_output`）在持久化前使用`truncate_text`（`app/utils/sanitize.py`）截断至4000字符。
* 绝对路径（Linux/Windows）使用`sanitize_paths`（`app/utils/sanitize.py`）替换为`<submission>/main.py`。

### 数据持久化与原子写入

`BaseRepository`（`app/repositories/base.py`）提供`_load_data`（损坏时抛出错误）和`_save_data`（写入临时文件+`os.replace`）。这确保不会发生部分写入，也不会静默丢失数据。

### 备份与恢复

* 备份（`app/routers/admin.py`）：将所有JSON文件复制到`data/backups/{timestamp}/`，并附带`manifest.json`。
* 恢复（`app/routers/admin.py`）：验证清单，创建当前数据的安全副本，然后从备份复制文件。如果在恢复过程中发生任何错误，系统从安全副本回滚以维护数据完整性。

### 前端会话管理

前端使用服务端会话（Starlette `SessionMiddleware`，在`app/main.py`中配置）。登录后，`user_id`存储在会话中。每个页面（`app/main.py`）检查会话以确定当前用户和角色。前端从不存储密码或令牌。

---

## 5. API描述

所有端点以`/api`为前缀，返回`{code, message, data}`。

| 方法 | 端点 | 权限 | 描述 |
|--------|----------|-------------|-------------|
| **认证**（`app/routers/auth.py`） ||||
| POST | `/api/auth/register` | 公开 | 注册新用户（默认为学生） |
| POST | `/api/auth/login` | 公开 | 登录，设置会话 |
| POST | `/api/auth/logout` | 公开（已登录） | 登出，清除会话 |
| GET | `/api/auth/me` | 已登录 | 获取当前用户信息 |
| **用户**（`app/routers/users.py`） ||||
| GET | `/api/users` | 管理员 | 列出用户（分页） |
| GET | `/api/users/{user_id}` | 管理员 | 获取用户详情 |
| PUT | `/api/users/{user_id}` | 管理员 | 更新角色/is_active（不能禁用自己） |
| **题目**（`app/routers/problems.py`） ||||
| GET | `/api/problems` | 已登录 | 列出题目（公开信息） |
| GET | `/api/problems/{id}` | 已登录 | 获取题目；学生看到公开信息，教师看到完整信息 |
| POST | `/api/problems` | 教师/管理员 | 创建题目（验证字段，分值总和=100） |
| PUT | `/api/problems/{id}` | 教师/管理员 | 更新题目（ID不变） |
| DELETE | `/api/problems/{id}` | 教师/管理员 | 删除题目 |
| **提交记录**（`app/routers/submissions.py`） ||||
| POST | `/api/submissions` | 已登录，激活 | 提交代码；返回202 + submission_id |
| GET | `/api/submissions` | 已登录 | 列出提交记录并支持过滤；学生仅能看到自己的 |
| GET | `/api/submissions/{id}` | 已登录 | 获取提交详情；学生看到自己的，教师看到所有 |
| POST | `/api/submissions/{id}/rejudge` | 教师/管理员 | 重新评测；仅对finished/failed状态有效 |
| **日志**（`app/routers/logs.py`） ||||
| GET | `/api/submissions/{id}/logs` | 已登录 | 获取评测日志；学生仅能看自己的，教师看完整版 |
| GET | `/api/logs` | 教师/管理员 | 搜索日志并支持过滤 |
| GET | `/api/audit-logs` | 管理员 | 过滤审计日志 |
| **备份**（`app/routers/admin.py`） ||||
| POST | `/api/admin/backups` | 管理员 | 创建备份 |
| GET | `/api/admin/backups` | 管理员 | 列出备份 |
| POST | `/api/admin/backups/{id}/restore` | 管理员 | 从备份恢复 |
| **相似度（高级3）**（`app/routers/similarity.py`） ||||
| POST | `/api/problems/{id}/similarity-check` | 教师/管理员 | 运行相似度检测 |
| GET | `/api/problems/{id}/similarity-reports` | 教师/管理员 | 获取已保存的报告 |

**错误响应**：

* 400：请求逻辑无效（例如，管理员禁用自己）
* 401：未登录
* 403：权限不足
* 404：资源未找到
* 409：冲突（重复、状态冲突）
* 422：验证错误（Pydantic）
* 500：内部服务器错误

---

## 6. 测试结果

所有测试使用`pytest`和`httpx`编写（`tests/test_api.py`）。测试套件运行44个测试，涵盖所有强制性功能和高级相似度模块。

### 摘要

```
44 passed in 20.80s
```

### 主要测试领域

| 测试类别 | 包含的测试 | 状态 |
|---------------|----------------|--------|
| **题目管理** | 创建（有效、重复、无效分值）、列表、详情、更新、删除；学生不能看到test_cases；权限检查 | 全部通过 |
| **评测器** | AC、WA、RE、TLE、输出标准化（尾随空格）、空源代码、源代码大小限制 | 全部通过 |
| **认证与权限** | 注册（有效、重复、短密码）、登录（有效、无效、已禁用）、登出；学生不能访问教师端点；教师不能访问管理员端点 | 全部通过 |
| **提交记录** | 创建、状态转换、学生仅看自己的、教师看到所有、重判（有效和冲突）、重判审计 | 全部通过 |
| **日志** | 学生日志隐藏隐藏测试用例、教师日志显示所有、教师日志搜索、学生不能搜索、审计日志 | 全部通过 |
| **备份与恢复** | 创建备份、列表、恢复、删除题目并恢复 | 全部通过 |
| **相似度（高级3）** | 提交相似代码、相似度检查返回配对、报告检索、学生访问被拒绝 | 全部通过 |
| **用户管理** | 管理员列表、获取、更新角色、不能禁用自己；学生访问被拒绝 | 全部通过 |

所有测试无需任何人工干预运行（无外部服务模拟）。测试时服务器单独启动。

---

## 7. 问题与解决方案

### 问题1：原子写入与数据损坏

**问题**：开发过程中，仓储直接写入JSON文件。如果在写入过程中发生崩溃，文件可能损坏，下一次`_load_data`会返回空列表/字典，静默擦除所有数据。

**解决方案**：

* 引入`BaseRepository`（`app/repositories/base.py`），使用临时文件和`os.replace`实现原子写入的`_save_data`。
* 修改`_load_data`，在`JSONDecodeError`时抛出`RuntimeError`而非返回空数据。
* API随后返回500错误，不会擦除数据。

### 问题2：日志字段缺失与截断

**问题**：最初，评测结果不包含`input_data`或`expected_output`；且日志在持久化前未被截断，可能导致磁盘膨胀。

**解决方案**：

* 在`app/judge/manager.py`中为每个测试用例结果添加`input_data`和`expected_output`。
* 在存储到提交记录之前，对`app/utils/sanitize.py`中所有输出字段（`stdout`、`stderr`、`input_data`、`expected_output`和错误信息）应用`truncate_text`。

### 问题3：`temp/`文件变更导致服务器重载

**问题**：使用`--reload`运行`uvicorn`时，每次评测器在`temp/`中创建临时文件都会导致服务器重启，杀死正在运行的子进程并返回RE。

**解决方案**：

* 使用`--reload-dir app`防止重载器监视`temp/`目录。
* 最终测试时，我们在没有`--reload`的情况下运行。

---

## 8. AI工具使用

### 使用的工具

* **DeepSeek** - 用于调试、架构建议、一般帮助（例如帮助配置SessionMiddleware、AST）和编写测试用例。
