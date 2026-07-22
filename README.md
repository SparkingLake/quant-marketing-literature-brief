# Quant Marketing Literature Brief

这是一个每天自动更新的文献简报工具，追踪 Econ Top Five、Marketing Science、Journal of Marketing、Journal of Marketing Research、Management Science，以及 NBER 与 SSRN 中关于pricing、digital platform、information economics等话题的 quantitaive marketing 与 IO 领域的papers。

## 筛选规则

1. **时间**：只收录运行当天往前五年内发表或发布的论文；没有可靠日期的记录不会入选。
2. **相关性**：标题必须命中一个高精度主题词，例如 `market power`、`digital platform`、`dynamic pricing` 或 `consumer choice`。`pricing`、`brand`、`retail` 等泛词只能辅助判断，不能单独让论文入选。
3. **数量**：每天最多 10 篇，按相关性分数排序。

期刊名本身不会让一篇论文自动入选。完整词表和阈值在 `config/topics.json`，可以随时调整。

## 不使用模型，不消耗 token

每日工作流只运行 Python 标准库代码和 Crossref 元数据查询；它**不调用任何 LLM**，因此模型 token 消耗为 **0**。GitHub Actions 只会消耗少量运行时间和网络请求。项目也不会下载论文 PDF 或保存全文。

## 每日运行

`.github/workflows/daily.yml` 定在北京时间 08:37 运行，也可以从 GitHub 的 **Actions** 页面手动运行。它会把生成的 Markdown 简报与去重状态提交回 `main`。

注意事项：受限于GitHub Actions的资源分配，通常会晚于设定时间推送，但一般在北京时间中午12点左右会完成当日推送。

可选：在仓库的 **Settings → Secrets and variables → Actions** 中添加 `CROSSREF_MAILTO`（联系邮箱），作为 Crossref 请求的礼貌池标识。它不是必需项。

## 本地运行

项目只使用 Python 标准库：

```powershell
python src/main.py --dry-run
python src/main.py
```

`--dry-run` 只展示结果，不写入文件。默认回看近 7 天的 Crossref 更新，以防元数据延迟；发表日期的五年硬限制仍然生效。

## 输出

每天的简报保存在 `briefs/YYYY/MM/YYYY-MM-DD.md`；已收录 DOI 保存在 `data/seen_papers.json`，避免重复推送。
