# review-reconstruction

面向医学综述的历史重构、批判性阅读和新题写作。版本：**0.3.5-development**（方法冻结于2026-11-12；公开说明更新于2026-11-14）。本版在既有选文、综合、章节和图表流程上，落实两项成文改进、澄清六个早期来源标记，并修复更正/辅助来源的记录兼容，保留63条候选规则及其适用边界。本包包含与方法调用有关的分析子集，来源阅读范围和未核事项按逐项记录保留；不随包发布完整私有语料库。

## 使用

入口为[SKILL.md](SKILL.md)。在Codex项目中使用时，将完整的`review-reconstruction`目录置于项目的`.agents/skills/`下，再开启该项目的新任务。也可在支持读取本地技能的环境中明确指定本目录。本项目未自动安装全局技能；其他宿主的发现方式须按其实际环境核对。

聚焦超声综述的安装位置、模式选择和可复制请求见[聚焦超声综述调用指南](references/focused-ultrasound-writing.md)。连接GitHub或打开仓库链接本身不等于已经安装或启用技能。

- 重构已有综述：`使用 $review-reconstruction，依据现有全文和索引，重构这篇综述的历史范围、选文、证据综合、章节和图表，并独立评价其判断。`
- 撰写新综述：`使用 $review-reconstruction，为指定读者和医学问题形成有来源的综述。先确定体裁、时间窗与新增价值，再完成检索、取舍、证据组、章节、图表和正文。`

先按[工作流](references/workflow.md)选择模式A或B；需要作出具体写作决定时，读取[从问题到综述正文](references/method-decisions.md)。[八类规则入口](references/rule-use.md)按当前问题调取必要检查，不要求逐条运行全部规则或生成所有模板。只需修改一个段落或图表时，沿用户范围处理。

## 本版怎样帮助成文

[跨案例方法](references/cross-case-methods.md)保留已有十案示例，并接入四组已核来源：

- 经骨聚焦：根据读者问题，决定实现背景与工程比较各占多少篇幅。
- 病理与功能：把不同模型、终点和组合比较组成证据组，再确定段落之间的关系。
- 组织碎化监测：将“更好”落到早期显影、定位或进展监测等具体任务，用表格保存比较参照。
- 经皮递送：辨认后续报告的新贡献及复用数据，按运输、屏障读出、机制和恢复组织论证。

科学综合与教学解释分开。实例展示怎样形成判断和章节出口；新题写作仍需自己的检索、来源与时间窗，不能继承案例的结论。四组来源支持现有方法的具体用法，不增加规则数量，也不构成未见题验证。

来源按需查阅[source-claims.csv](references/source-claims.csv)、[claim-source-map.csv](references/claim-source-map.csv)和[source-identities.csv](references/source-identities.csv)。本版含441条分析主张、910条来源连接及151条身份记录。六个早期标记经[定点说明](references/source-clarifications-v035.md)分别收窄为母文观察/解释或官方当前登记别名：删除五条非文献占位来源，保留母文连接，另将原登记token连接到既有身份。原主张ID、63条规则、页段及未知边界保留；这不增加全文阅读或历史登记核查，连接可解析也不等于科学证据已全部核实。提供稿主文已读不等于正式版或补充材料均已核，会议摘要也不计为研究全文。来源身份和记录行数不代表独立研究数。

## 记录工具

Python 3.10 以上，无第三方依赖；在方法包根目录运行：

```text
python scripts/review_records.py audit --index path/to/reference-index.csv --readings path/to/readings.csv
python scripts/review_records.py audit --index path/to/reference-index.csv --readings path/to/readings.csv --aliases path/to/reviewed-aliases.json
python scripts/review_records.py locate --index path/to/reference-index.csv --root path/to/library --paper-id PAPER_ID
python -m unittest discover -s evals -p "test*.py" -v
```

索引接受原中文字段或等义英文 `reference_code,paper_id,pdf_path`。阅读表保留 `paper_id,reading_status,read_scope`；规范状态还须提供 `record_kind`。阅读类别接受 `literature`、`mother_review`、`mother_supplement`、`registry`、`correction`、`analyst_associated_literature`，不从题名或编号推测。

| 状态体系 | 精确接受的值 |
|---|---|
| 精简模板 | `full_text_read`、`mother_full_read`、`partial_read`、`not_yet_read`、`source_missing`、`abstract_only` |
| 规范项目状态 | `MAIN_TEXT_READ`、`PROVIDED_VERSION_MAIN_TEXT_READ_VOR_UNVERIFIED`、`PARTIAL_READ`、`PUBLISHED_ABSTRACT_READ`、`PUBLISHED_CORRECTION_READ`、`NOT_YET_READ`、`SOURCE_UNAVAILABLE`、`SOURCE_GAP`、`REGISTRY_CURRENT_RECORD_READ_HISTORY_UNVERIFIED`、`REGISTRY_REVIEW_PENDING` |

精简模板未提供类别时，`mother_full_read` 归入母综述，其余归入文献，以兼容旧模板。规范状态缺类别、未知状态、类别冲突、无来源索引的文献或注册记录、主文已读却没有阅读范围，均报错并返回退出码 2。两个 `REGISTRY_` 状态仅能搭配 `registry`；`PUBLISHED_CORRECTION_READ`与`correction`必须配对，且原索引中须为该文献身份。更正与同ID普通文献阅读冲突会报错。`analyst_associated_literature`仅接受明确位于原索引之外的辅助来源，不把未知文献自动改为辅助。明确标为母综述或母补充材料的记录允许使用其独立身份。成功返回 0。

各类记录使用各自分母。普通主文、仅已读提供版本而 VOR 未核的主文、母综述、母补充材料、注册记录、更正和分析者关联来源单列；主文已读不能推出补充材料已读。同一 ID 的多个引用关系及重复阅读行不增加记录数。`records_without_full_read_record` 表示索引文献中尚无直接主文阅读记录的 ID 数（包括部分阅读或只读摘要者）；`unread_literature_record_count`进一步排除部分阅读、只读摘要及完整更正已读者。更正保留原库分母但不算主文；辅助阅读按状态单列，始终不进入原库分母、覆盖或别名。这些数值不是独立研究数，也不认证科学完成。

`--aliases` 是显式可选输入。它接受精确 ID 映射 `{ "alias_id": "directly_read_canonical_id" }`，也接受含 `reviewed_shared_evidence_aliases` 对象的项目进度文件。映射方向为**索引别名 ID → 有直接主文阅读记录的规范 ID**；不以题名匹配。两端须为索引中的普通文献，更正和辅助来源不得作为别名端点；记录的非空文件路径、64 位 SHA-256 和已有的起始页须一致。自指、链式映射、未知端点、目标无直接主文阅读或记录元数据不符均报错；有任一无效映射时不应用整组别名。此检查比较已有索引元数据，不重新读取或计算 PDF 哈希，也不独立判定作品身份。

未指定别名时只报告直接记录。指定且验证通过时，直接计数保持不变，另报新增覆盖及扩展覆盖；已直接阅读的别名不会再次增加覆盖，VOR 未核也不会因别名而变成已核。`locate` 的既有行为保持：只定位文件；多路径、缺失文件或越出资料根目录均报错。


## 实际验证范围

0.3.4已完成两题各自检索到成文的有限比较：超声题普通35/方法36，非超声题普通36/方法35，四次原定写作及两次匿名独立上下文模型评阅均完成。已核范围未确认严重事实失败，但未确立稳定增益；执行隔离、资源计量和漏检检查均有限。两题的局部发现用于本版改进，不能再充当未见题，旧分数不转授0.3.5。

本版在成文后直接检查两点：影响适用性的已知限制是否进入相应主张；同一核心来源是否还有会限定总括句的相关测量。保留终点身份和不确定性，不按P值筛选，也不新增台账。尚无本版新的未见题科学对照；打包后已完成0.3.5本机项目发现及三类请求的实际调用检查，详见[验证记录](evals/validation-summary.md#035打包后的实际运行检查)。

[验证记录](evals/validation-summary.md)按版本区分结果。0.3.2已经完成两题、四套成文输出的有限对照：N1为原定配对，U1普通条件经过一次补跑，后者仅属探索性。结果未确立稳定、普遍的写作增益；输入为预置来源池，未覆盖独立检索到多节正文的完整流程。

0.3.3已经在本机项目范围实测发现、模式A隐式调用、模式B明确调用及普通润色不误触发。这是运行行为检查，不是科学效果验证。本版修订内容没有继承旧版评分；新比较仍须冻结实际受测版本、题目、权限和评价标准后执行。U1/N1及已用于归纳或修订的相关研究家族不再作为未见输入。

0.3.4另完成本机独立项目的三类请求检查，均正常结束：模式A实际读取入口和工作流，模式B实际读取三份配套方法，普通润色未出现命令或方法文件读取。模式B没有单独的入口读取事件，不能由现有日志独立确认其宿主自动装载方式；无工具读取也不证明宿主层全面隔离。该检查未检验真实科学成文。

本版不声称训练已普遍完成；案例分析、软件检查、调用成功和写作效果分别报告。学习与封装不是模型参数训练，也不改变长期记忆。

## 权利与发布

本目录仅含原创方法、模板、代码、教学图及允许公开的书目与分析；第三方全文、原始图件、截图和长段原文不随包分发。按所有者选择，暂不添加开源许可证。

[公开仓库](https://github.com/TroyeXie/review-reconstruction)本次按所有者授权从0.3.1-development更新至0.3.5-development。公开副本更新README及验证说明、新增聚焦超声调用指南，并将一处来源记录的实施细节收窄为写作方法所需的职责说明、替换两处包外私有记录路径；不改变原主张ID、科学终点和阅读状态。原冻结包及测试输出不覆盖，后续修订以仓库提交记录为准。
