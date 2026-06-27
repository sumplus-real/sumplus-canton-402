# Canton 黑客松 — 实际可用方案（给 xufei）

> 赛道 3：支付、新型银行与 Agent 商业。截止 6/29 晚 8 点（北京）。
> 这份文档是给你回来拍板用的。代码已经写好，正在本机编译验证。

## 一句话

把我们 **CAEL grant 提案里排到 M2–M3（Q3–Q4 2026）的 Daml 支付合约套件，提前做成一个能跑的垂直切片**：一个企业把"花钱权限"用 Daml 合约（mandate）发给自己的 AI agent，agent 就能在额度内自主买服务，每一笔都是**原子结算 + 子交易隐私 + 防篡改回执**。对评委是"真能用的 Agent 商业产品"，对 grant 评审是"我们提案最难那块 Daml 真做出来了"。

## 为什么是这个，不是别的

- **配合现有产品**（你的硬要求）：Maria 策略层 → `Mandate` 合约；Arsenal 付费 skill → `ServiceOffer`；可验证 agent 的链式哈希回执（EVM 上已经在跑）→ 链上 `PaymentReceipt`。不是新造轮子，是把三个现有产品在 Canton 上拼成一个产品。
- **踩中赛道红线的正面**：评委明说"要像真能被企业/个人用的产品，不是套层 AI"。这个东西本身就是个产品：**Agent 时代的企业卡**——可编程额度、白名单、可审计、默认隐私。
- **用足 Canton 的独门武器**：隐私（只有交易双方 + 审计方看得见）+ 原子结算（付款与交付同一笔交易，不可能只付钱不交付）。这两点公链做不到，正好是 Canton 该赢的地方。
- **跟 grant 互补、不打架**：grant 是"未来要做"，黑客松是"已经能跑的证据"。互相加分。

## ✅ 已端到端验证跑通（本机，2026-06-27）

环境从零搭好：Daml SDK 2.10.4 + OpenJDK 17（本机原本无 Java、无 Daml）。

1. **`daml test --all` 三个脚本全绿**：`demo`（18 合约 / 13 笔交易，含 2 笔成功支付 + 链式回执校验 + 3 个越权当场被拒 + 隐私断言）、`narrate`（演示叙述版）、`setup`（种子）。
2. **真 ledger 跑通**：`daml start`（Canton sandbox + JSON API）→ `seed.sh`（真实 party 分配）→ 网关 → agent，全链路通。
3. **自主 agent 端到端**：`agent.py` 发现服务 → 收 HTTP 402 → 付款 → 网关把 `PayAndCall` 提交到真 ledger → 拿回执哈希。回执哈希与 `daml test` 完全一致（确定性）。
4. **策略护栏链上生效（经网关验证）**：连跑到日累计 240，再买 60 触发链上拒绝「spend would bring today's total to 300.0, over the daily cap 250.0」，网关如实回传。agent 无法越权。
5. **隐私在真 ledger 成立**：auditor 看到全部结算回执，rival 看到 **0**，每个 vendor 只看到自己那几笔。

## 代码结构（已写完）

```
daml/Canton402/Asset.daml      结算资产（发行方签名的持有凭证，= Canton Coin / 代币化存款占位）
daml/Canton402/Mandate.daml    Maria 策略层上链：单笔上限/日上限/白名单/审计方，Authorize 逐笔校验
daml/Canton402/Commerce.daml   ServiceOffer + 原子 PayAndCall（策略校验→结算→交付→链式回执）
daml/Test/Demo.daml            端到端验收脚本：成功流 + 3 个越权被拒 + 隐私断言
README.md / docs/ARCHITECTURE.md / scripts/demo.sh
```

**`daml test` 一条命令验证的东西**（这是 demo 视频和评审的硬证据）：
1. 两笔成功的原子 pay-and-call，回执链式哈希正确（第 2 条嵌第 1 条哈希）。
2. 三种越权当场被链上拒绝：超单笔上限、付给白名单外的供应商、超日累计上限。
3. 隐私断言：竞争对手方看到 Acme 的回执/持有/凭证 **数量为 0**；审计方恰好看到全部结算回执；每个供应商只看得到自己那几笔。

## 还要做的（到 6/29 的清单）

| # | 事项 | 谁 | 状态 |
|---|---|---|---|
| 1 | `daml test` 跑绿 | 我 | ✅ 完成 |
| 2 | Canton 402 网关（HTTP 402 + MCP 适配器）| 我 | ✅ HTTP 402 网关 + MCP stdio 服务都已跑通验证 |
| 3 | Agent 自主 demo 脚本 | 我 | ✅ 完成并验证 |
| 4 | 提交字段文本 | 我 | ✅ 见 `SUBMISSION.txt`（CMO 直接粘） |
| 5 | 录屏（3-5 分钟）| 你/CMO | 脚本已备好 `docs/DEMO_SCRIPT.md`；最省事=只录 `daml test --all` 一屏 |
| 6 | 1-pager / 简短 deck | 我 | 可选；要的话我出 |
| 7 | 建公开 GitHub repo + push | 你 | 你建空仓 + 贴 deploy key，或并入 `sumplus-real/cael` |
| 8 | 提交表 | CMO（橘猫/Grizzily）| 他负责；字段文本已备 |

## 关键决策点（等你拍）

1. **repo 放哪**：(a) 独立新仓 `sumplus-canton-402`；(b) 直接并入 grant 仓 `sumplus-real/cael` 当作 M2–M3 实现切片（对 grant 叙事最强，但要动那个进行中的分支）。我倾向 (b)，但先建在独立目录、可逆。
2. **网关语言**：Python（跟 trading-agent 一致、我出错率低）还是 TS（grant 文档写的是 TS/Java）。我倾向 Python 先跑通。
3. **要不要上真 Canton devnet**：`daml test` / `daml start` 用的是 Canton 同款 Daml 运行时，合约不改就能部署。1.5 天内本地 sandbox 足够拿分；真 devnet 可作为加分项，时间够再上。

## 风险与对冲

- **SDK / 环境**：本机无 Java、无 Daml，已绕开 GitHub API 限流直接装 SDK（自带 JVM）。这是唯一的环境不确定项，装完即消除。
- **时间**：核心（能跑的 Daml）已写完，剩下是网关 + 录屏 + 提交，都是确定性工作。
- **不造假**（红线）：全部是真合约、真断言、真隐私语义，没有任何摆拍或伪造状态。

---
*状态：代码已写完，SDK 安装中，待编译验证。我会一路推进到 `daml test` 跑绿 + 网关跑通，再更新这份文档。*
