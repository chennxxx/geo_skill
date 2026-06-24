# Competition Density Skill

这是一个用于门店竞争密度分析的 Codex/Agent skill。

用户提供目标门店 CSV、竞争对手点位 CSV 和评估半径后，skill 会对每个目标门店统计指定半径内的竞争点数量，计算竞争密度指标，并生成中文业务分析报告与 CSV 结果文件。

## 功能

- 识别目标门店和竞争点位 CSV 中的经纬度列
- 支持经纬度分列或 `lng,lat` 合并坐标列
- 支持 `km`、`m`、`公里`、`米` 等半径单位
- 使用 Haversine 公式计算球面距离
- 输出每个门店的竞争点数量、均值偏差和竞争强度等级
- 生成竞争热力 Grid 的 WKT CSV
- 用中文生成业务分析报告，指出竞争激烈门店、机会点和建议

## 文件说明

| 路径 | 说明 |
|------|------|
| `competition-density.skill` | 可直接导入的 skill 包 |
| `competition-density-skill/SKILL.md` | skill 的完整说明、触发条件和执行流程 |
| `competition-density-skill/scripts/haversine.py` | Haversine 距离计算脚本 |

## 触发场景

当用户提到以下内容时，适合使用这个 skill：

- 竞争密度
- 周边竞品
- 缓冲区分析
- 门店竞争评估
- 半径内竞争点
- 门店和竞品坐标 CSV 分析

## 输入要求

需要两份 CSV 文件和一个评估半径：

1. 目标图层 CSV：包含门店名称、经度、纬度
2. 竞争图层 CSV：包含竞争点经度、纬度，可选名称列
3. 评估半径：例如 `1km`、`500m`、`1.5公里`

坐标列名不需要完全固定，skill 会优先识别常见列名，例如：

- 经度：`lng`、`lon`、`longitude`、`经度`
- 纬度：`lat`、`latitude`、`纬度`
- 合并坐标：`lnglat`、`lonlat`、`coordinates`、`坐标`、`经纬度`

## 输出

运行后会生成：

- `competition_density_<YYYYMMDD>.csv`：门店竞争密度得分表
- `competition_grid_<YYYYMMDD>.csv`：Grid WKT 热力数据

对话中会展示数据摘要、中文分析报告、结果预览表和 Grid 摘要。

## 使用

下载或导入 `competition-density.skill` 到支持 `.skill` 的 Codex/Agent 环境中即可使用。

如果只想查看 skill 的具体逻辑，可以直接阅读 [`competition-density-skill/SKILL.md`](competition-density-skill/SKILL.md)。
