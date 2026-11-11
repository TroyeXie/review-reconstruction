# review-reconstruction

面向医学综述的历史重构、批判性阅读和新题写作。版本：0.3.1-development（2026-11-11）。本版包含63条候选规则、367条原有分析主张及其来源连接，补齐十篇案例的结构选择和三个“证据组—段落—章节”范例。全量引用分析仍在进行；本版不是全库完成报告。公开仓库为[www.github.com/TroyeXie/review-reconstruction](https://github.com/TroyeXie/review-reconstruction)。

## 使用

将本目录整体放入目标Codex环境的技能目录，或在支持直接读取本地技能的任务中指定本目录。入口为`SKILL.md`。本项目尚未自动安装到用户全局技能目录。

示例请求：

- 使用`$review-reconstruction`，按现有索引重构这篇临床综述的选文、证据综合、章节和图表，保留历史版本及未知事项。
- 使用`$review-reconstruction`，为明确的新临床问题编写叙述性综述，先建立候选与主张映射，再形成提纲、原创图表和正文。

建议从[从问题到综述正文](references/method-decisions.md)开始：选范围、建立证据组、形成章节判断，再写段落和图表。`references/workflow.md`分别说明两种模式；`references/case-decisions.md`保留具体决策及适用边界。`assets/section-plan.csv`用于章节卡，其余模板按实际研究类型使用，不要求非临床文献填写虚假的临床参数。

63条规则所引的361条主张全部包含在`references/source-claims.csv`，另有6条图表解释范例主张。`claim-source-map.csv`区分母综述上下文、已有来源连接和未解析标记；`source-identities.csv`保留125个身份条目及其现有版本/阅读状态。多个身份可能指向同一报告，不能以身份行数计算独立研究数。导出保留原有科学限制和阅读范围；空字段不等于已核实。6个未解析来源标记没有被补造或隐藏。规则中缺少的来源位置由支持主张展开并注明，原本空缺的D/I/U未自动补值。

## 记录检查

Python 3.10以上，无第三方依赖：

```text
python scripts/review_records.py audit --index path/to/reference-index.csv --readings path/to/readings.csv
python scripts/review_records.py locate --index path/to/reference-index.csv --root path/to/library --paper-id PAPER_ID
```

索引接受项目原中文字段（编码、记录ID、PDF相对路径），或等义英文`reference_code,paper_id,pdf_path`。阅读记录使用`paper_id,reading_status,read_scope`；可带`reference_code`。`full_text_read`为已实际全文读；`mother_full_read`单列母综述；`partial_read`和`not_yet_read`均不计全文读。相同文献跨综述不重复计数。

检查器只核身份、字段、重复编码、源文件路径及阅读记录分母。不存在阅读记录不会被认定为缺失全文。`locate`只输出文件路径，不读取或上传内容；路径越出所指定资料根目录、同ID对应多个文件、缺失文件均明确报错。

## 验证状态

本版来源连接与字段检查已执行，全部规则支持主张可解析；原始资料索引、科学主张总表和旧冻结副本保持不变。本版新增规则与范例尚未完成新的未见题对照测试。

旧0.3.0冻结版曾完成两个新题的有限测试：聚焦超声与子宫肌瘤、非超声的心衰药物证据。普通指令与冻结技能各两份输出，匿名代理均评18/18，未显示技能增益。格式偏差、评估上限和入口探测边界见[有限验证记录](evals/validation-summary.md)。该结果只属于旧冻结版，不能转用于本版新增内容。规范检查与代理路由探测也不证明宿主自动激活、全量案例完成或普遍医学写作有效。

## 权利与发布

本仓库包含原创方法、代码、模板、简短原创分析和书目链接。案例论文及其图件权利属于原权利人，不随本目录分发。开放获取不自动意味着本项目复制全文。按仓库所有者的明确选择，本次公开交付暂不添加开源许可证；第三方论文及图件不随仓库分发。版本与文件内容以具体提交为准。

来源协议沿用项目既有`review-reconstruction`方法及2026-11-09更新任务，已修正T05不同在线阶段和T09正式版检索说明的处理。学习与封装不是模型参数训练，也不改变长期记忆。
