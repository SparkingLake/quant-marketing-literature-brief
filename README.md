# Quant Marketing Literature Brief

一个可在 GitHub Actions 上每天自动运行的文献追踪器，面向：

- Econ Top Five：AER、QJE、JPE、Econometrica、REStud
- Marketing Science、Journal of Marketing、Journal of Marketing Research、Management Science
- NBER 与 SSRN working papers

它从 Crossref 拉取新近索引的元数据，按 `config/topics.json` 中的主题词做可解释的初筛，去重后把当天结果写入 `briefs/YYYY/MM/YYYY-MM-DD.md`。所有已见论文的标识保存在 `data/seen_papers.json`，所以重复运行不会重复收录。

## 首次运行

本项目只用 Python 标准库。需要 Python 3.11 或更新版本。

```powershell
py -3.11 src/main.py --dry-run
py -3.11 src/main.py
```

`--dry-run` 不会修改 `briefs/` 或 `data/`。默认回看 7 天，以降低元数据延迟造成的漏报风险。

## 调整范围

- 期刊和 DOI 前缀见 `config/sources.json`。
- 主题词、阈值和每日上限见 `config/topics.json`。
- 默认只保留与 industrial organization、information/digital economy、quantitative marketing 有明确关联的论文；期刊名本身不会自动使文章入选。

目前的简报是确定性、可审计的关键词筛选：每条会展示命中的领域和关键词。第二阶段可接入 LLM 生成中文研究问题、方法和贡献摘要；密钥应放在 GitHub Actions Secret，绝不能提交到仓库。

## GitHub Actions

`.github/workflows/daily.yml` 会在北京时间约 08:37 运行，也可从 Actions 页面手动运行。工作流将生成的简报和去重状态自动提交回 `main`。

在仓库 **Settings → Actions → General** 中确认 Actions 已启用。工作流已在 YAML 内声明 `contents: write`，用于回写简报。

可选：在仓库 **Settings → Secrets and variables → Actions** 中新增 `CROSSREF_MAILTO`（你的联系邮箱）。它会作为 Crossref 请求的礼貌池标识，不会写入仓库。

## 输出与限制

- 保存标题、作者、DOI/链接、来源、日期、匹配标签和短说明；不保存 PDF 或完整摘要。
- Crossref 的索引时间不等同于正式 online-publication 时间；简报会保留链接供核验。
- NBER 通常按周发布，SSRN 的分发与收录可能存在滞后。因此“每日”指每日检查和更新，不代表每天都有新增。

