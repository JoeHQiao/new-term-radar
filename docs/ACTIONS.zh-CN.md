# GitHub Actions 运行说明

本副本默认使用免费模式，生成中文报告。程序版本为 0.4.1，本次配置版本按 0.40 → 0.41 递增。

## 配置对比

| 项目 | 上游默认 | 本副本 |
|---|---|---|
| 报告语言 | 示例为英文，配置未提交 | 提交中文 `config.json` |
| 运行模式 | 直接调用全部配置功能 | 默认 `free`；主动设置 `full` 才调用付费功能 |
| 免费采集 | 未提供专用运行分支 | Hugging Face、GitHub、网站 sitemap |
| 完整模式 | 新站接口仍有已知问题 | 暂跳过新站信号，其余按配置和密钥运行 |
| 收入接口 | 工作流未传递密钥 | 支持可选 `TRUSTMRR_API_KEY` |
| 下载备份 | 报告和 SQLite 数据库 | 报告、数据库及全部增量快照 |

这次没有网页界面改动，上表即配置的前后对比。

## 开启与查看

在仓库 Settings → Secrets and variables → Actions → Variables 设置：

- `RADAR_ENABLED=true`：允许执行雷达。
- `RADAR_MODE=free`：免费模式；未设置时也默认免费。

在 Actions → New-term radar → Run workflow 中，先选择 `sources`，再选择 `daily`。报告在运行的 Summary，报告文件和完整 `state/` 可从 Artifacts 下载。首次采集主要建立对比基线，快讯无新线索时不生成报告属于正常情况。

沿用上游 UTC 日程，按越南时间（Asia/Ho_Chi_Minh，UTC+7）：

- 快讯：07:00、15:00、23:00。
- 日报：08:30。

GitHub 定时任务可能延迟。个人电脑关机不影响云端执行。启用状态以仓库 Variables 和工作流状态为准，代码存在本身不代表已启用。

## 切换完整分析

先自行在仓库 Actions Secrets 添加 `AISA_API_KEY`，再将 `RADAR_MODE` 改为 `full`。不要在聊天、配置文件、提交或日志中粘贴密钥。`GOANYAPI_API_KEY` 和 `TRUSTMRR_API_KEY` 按需要配置。

完整模式会产生 API 费用，金额取决于账号数量、调用频率和服务价格。上游示例约 15 美元/月只是作者估算。新站信号暂跳过，待上游接口实际验证恢复后再启用。

免费模式不提供模型判断、关键词搜索量、竞争分析和 14 天 Trends 复盘。未配置邮件通知时，请到 Actions 查看报告。

## 测试与验收步骤

1. 修改前运行 `python -m pytest -q tests`，记录基线。
2. 修改后再次运行同一套测试，并检查 `git diff --check`。
3. 在云端确认 Python 3.10 和 3.12 的 Tests 工作流通过。
4. 手动执行 `sources` 和 `daily`，核对运行的提交、语言、各数据源的成功数量及错误信息。
5. 确认后续任务成功恢复状态缓存，下载备份包含数据库和 Hugging Face、GitHub、sitemap 快照。
6. Actions 显示绿色不代表所有数据源都成功；程序可能把接口错误写入报告后正常退出，必须检查报告内容。

缓存不是永久存储，Artifacts 保留 30 天。需要保留长期复盘历史时，应定期下载完整状态备份。

## PR 描述

配置仓库自带 GitHub Actions，使用中文日报和默认免费模式。完整模式须主动设置变量并提供 AIsa 密钥；将快照纳入下载备份，避免仅恢复数据库时丢失增量基线。

验证包括修改前后单元测试、云端 Python 3.10/3.12 测试，以及真实 `sources`/`daily` 采集和缓存恢复检查。实际执行结果在部署记录中另行记载。
