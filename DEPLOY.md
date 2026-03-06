# 如何部署到 GitHub 仓库

按下面步骤即可把本项目推送到你的 GitHub 个人仓库。

## 一、在 GitHub 上创建仓库

1. 打开 [GitHub 新建仓库](https://github.com/new)。
2. **Repository name** 填：`openclaw-api-monitor`（或你喜欢的名字）。
3. 选择 **Public**，**不要**勾选 "Add a README"（本地已有代码）。
4. 点击 **Create repository**。

## 二、在本地用 Git 推送

在项目根目录（包含 `README.md`、`src/` 的目录）打开终端，依次执行：

```bash
# 进入项目目录（请改成你的实际路径）
cd openclaw-api-monitor

# 初始化 Git
git init

# 添加所有文件（会按 .gitignore 排除 config.yaml、__pycache__ 等）
git add .

# 首次提交
git commit -m "Initial commit: OpenClaw API failure monitor and recovery watch"

# 主分支命名为 main（若已默认是 main 可跳过）
git branch -M main

# 添加你的 GitHub 远程仓库（示例：EndlessWaltz-Xi）
git remote add origin https://github.com/EndlessWaltz-Xi/openclaw-api-monitor.git

# 推送到 GitHub
git push -u origin main
```

若使用 SSH：

```bash
git remote add origin git@github.com:EndlessWaltz-Xi/openclaw-api-monitor.git
git push -u origin main
```

## 三、推送时若提示需要登录

- **HTTPS**：会提示输入 GitHub 用户名和密码；密码处需使用 [Personal Access Token](https://github.com/settings/tokens)（不再支持账号密码）。
- **SSH**：需先在 GitHub 添加 SSH 公钥，再使用上面的 `git@github.com:...` 地址。

完成以上步骤后，在浏览器打开 `https://github.com/YOUR_USERNAME/openclaw-api-monitor` 即可看到代码。
