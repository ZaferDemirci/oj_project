# 在线评测（OJ）系统

**此文件仅供参考，请查阅原始文件：README.md。此文件是用翻译app生成的。**

基于 **Python**、**FastAPI** 和 **Jinja2** 模板构建的在线评测（OJ）系统。

本项目是作为大学课程作业开发的，支持：

* 用户注册、登录以及基于角色的权限（学生、教师、管理员）
* 题目的创建、编辑、删除（教师/管理员）
* 代码提交（Python）及异步评测
* 多测试用例评判：`AC`、`WA`、`RE`、`TLE`、`SE`
* 基于角色可见性的详细日志（隐藏测试用例对学生不可见）
* 敏感操作审计追踪
* 备份与恢复（仅限管理员）
* 代码相似度检测（可选高级功能）

---

## 环境要求

* 需要 Python 3.10 或更高版本。
* 所需 Python 包请参见 `requirements.txt`。

---

## 安装

1. **克隆仓库**（或解压项目文件夹）。

    ```bash
    git clone https://github.com/ZaferDemirci/oj_project.git
    ```

2. **创建并激活虚拟环境**（推荐）：

   ```
   python -m venv venv
   # Windows 系统：
   venv\Scripts\activate
   # Linux/macOS 系统：
   source venv/bin/activate
   ```

3. **安装依赖**：

   ```bash
   pip install -r requirements.txt
   ```

---

## 配置

所有设置均通过环境变量（或 `.env` 文件）进行管理。

* PowerShell

    ```powershell
    # 临时变量（仅当前会话有效）
    $env:MY_VAR = "some_value"

    # 删除方式：
    Remove-Item Env:MY_VAR`
    # 或
    $env:MY_VAR = $null


    # 当前用户的永久变量
    [Environment]::SetEnvironmentVariable("MY_VAR", "some_value", "User")

    # 本机所有用户的永久变量
    [Environment]::SetEnvironmentVariable("MY_VAR", "some_value", "Machine")
    
    # 删除方式：
    [Environment]::SetEnvironmentVariable("MY_VAR", $null, "User")
    # 或使用 "Machine" 进行系统级删除
    ```

* Bash
  
    ```bash
    # 临时变量（仅当前会话有效）
    export MY_VAR="some_value"

    # 删除方式：
    unset MY_VAR
    ```

  * 将 export 行添加到 shell 启动文件（如 ~/.bashrc、~/.profile、~/.bash_profile）中，如需全局生效可使用 /etc/environment 或 /etc/profile（需要 root 权限）。

在项目根目录下创建 `.env` 文件（可选），内容如下：

```env
SECRET_KEY=your-secret-key-here
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

如果未提供 `.env` 文件，应用程序将使用默认值（见下文）。

### 环境变量

| 变量名            | 默认值                          | 描述                                                                 |
|-------------------|---------------------------------|----------------------------------------------------------------------|
| `SECRET_KEY`      | `super-secret-dev-key-change-me` | **生产环境必须设置**，用于会话签名。请生成一个强密钥。                  |
| `ADMIN_USERNAME`  | `admin`                         | 初始管理员账户的用户名（首次启动时创建）。                             |
| `ADMIN_PASSWORD`  | `admin123`                      | 初始管理员账户的密码。**生产环境请务必修改！**                        |

---

## 运行应用程序

启动 FastAPI 服务器（开发模式下启用自动重载）：

```bash
uvicorn app.main:app --reload --reload-dir app
```

> ⚠️ `--reload-dir app` 参数可防止服务器在评测过程中因 temp/ 目录下创建临时文件而重启。

> 生产环境下，请勿使用 `--reload` 参数：
>
> ```bash
> uvicorn app.main:app
> ```

启动后，在浏览器中打开：

[http://localhost:8000](http://localhost:8000)

---

## 运行测试

使用 `pytest` 运行测试套件（可选择添加 --verbose 或 -v）：

```bash
pytest -v
```

所有测试必须通过才能视为构建成功。

---

## 默认管理员账户

**首次启动**时，系统会自动创建一个管理员用户：

* **用户名：** `admin`
* **密码：** `admin123`

> **重要提示：** 以上为**开发环境默认值**。

> 如需修改，请在启动服务器前设置环境变量 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`。

---

## 持久化与备份

* **持久化方式：** JSON 文件（存储在 `data/` 目录下）。
* **数据文件：**
  * `users.json`
  * `problems.json`
  * `submissions.json`
  * `audit_logs.json`
  * `similarity_reports.json`
* **备份：** 管理员通过 UI 或 API 创建，存储在 `data/backups/` 目录下。
* **临时评测文件：** 存储在 `temp/` 目录下，每次评测运行后自动清理（已排除在 Git 之外）。

---

## 前端

前端采用 **Jinja2** 模板进行**服务端渲染**。

项目说明文件中列出的 frontend/ 目录并不存在，实际使用的是 app/templates/ 和 app/static/。

无需单独的前端服务器，所有页面均由 FastAPI 直接提供。

静态文件（CSS 等）位于 `app/static/` 目录下。

---

## 已知限制

* 仅支持 **Python** 代码提交。
* 内存限制已存储但**未强制执行**（仅强制执行时间限制）。
* 评测在**独立子进程**中运行，但未使用 Docker 或高级隔离机制。
* 相似度检测基于 AST（抽象语法树）规范化，**并非**防抄袭工具，仅提供嫌疑度评分。

---

## 补充说明

* **API 文档**（由 FastAPI 自动生成）可在 `/docs` 和 `/redoc` 页面查看。
* 所有 API 端点均以 `/api/` 为前缀，并返回统一的 JSON 响应格式。

---

## 贡献者

* Zafer DEMİRCİ 杜哲胜
