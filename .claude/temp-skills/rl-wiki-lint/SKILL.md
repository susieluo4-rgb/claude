---
name: rl-wiki-lint
description: Wiki健康检查Skill — 自动检查Wiki页面的断裂引用、过期数据、缺失Section，并统计覆盖率。当用户说"wiki lint"、"检查wiki健康度"、"wiki健康检查"时触发。
metadata:
    version: 1.0
    type: wiki-lint
    position: 知识管理层
---

# rl-wiki-lint — Wiki健康检查Skill

## 角色定位

Wiki Lint Agent 是 Karpathy LLM Wiki 架构中的**检查层**，确保 Wiki 页面的质量和一致性。

```
Wiki 页面集合
    ↓
【Wiki Lint】7 项检查
    ↓
健康报告 + 修复建议
```

## 触发方式

| 触发词 | 示例 |
|--------|------|
| `wiki lint` | "wiki lint" |
| `检查wiki健康度` | "检查wiki健康度" |
| `wiki健康检查` | "wiki健康检查" |
| `wiki 检查` | "wiki 检查" |

## 检查项（7 项）

### 1. 断裂交叉引用
- 扫描所有 Wiki 页面中的 `→ [[xxx]]` 引用
- 检查每个引用对应的页面是否存在
- 报告断裂的引用和所在页面

**实现方式**：
```
Grep 所有 *.md 文件中的 `→ \[\[.+?\]\]`
对于每个匹配项，解析目标文件名
Glob 检查目标文件是否存在于 wiki/ 目录下
```

### 2. 过期数据 — 财务
- 检查每个公司页面的"最后更新"日期
- 财务数据超过 90 天未更新标记为过期
- 报告过期页面列表

### 3. 过期数据 — 估值
- 估值数据超过 14 天未更新标记为过期

### 4. 过期数据 — 投资逻辑
- 投资逻辑超过 180 天未更新标记为过期

### 5. 缺失必填 Section
- 检查每个公司页面是否包含 7 个必填 Section
- Section 标题必须严格匹配 Schema 定义
- 报告缺失的 Section

**检查的 7 个 Section**：
1. `## 1. 公司概况` 或 `## 公司概况`
2. `## 2. 投资逻辑` 或 `## 投资逻辑`
3. `## 3. 财务摘要` 或 `## 财务摘要`
4. `## 4. 估值水平` 或 `## 估值水平`
5. `## 5. 风险因素` 或 `## 风险因素`
6. `## 6. 交叉引用` 或 `## 交叉引用`
7. `## 7. 最后更新` 或 `## 最后更新`

### 6. Wiki 覆盖率统计
- 统计已建 Wiki 的公司数
- 对比 Vault_公司基本面Agent 中的公司总数
- 计算覆盖率

**计算方式**：
```
已建 Wiki 公司数 = wiki/companies/ 下所有 *.md 文件数
总公司数 = Vault_公司基本面Agent/11_公司列表/ 下所有公司文件夹数
覆盖率 = 已建 / 总数
```

### 7. 日志一致性检查
- 检查 `wiki/log.md` 中的记录与实际文件是否一致
- 报告有记录但文件不存在的条目
- 报告文件存在但日志无记录的条目

## 输出格式

```markdown
## Wiki 健康检查报告

### 概览
- 📊 总页面数：{N}
- ✅ 健康页面：{N}
- ⚠️ 有问题页面：{N}
- 📈 Wiki 覆盖率：{X}%

### 问题详情

#### 断裂交叉引用（{N} 处）
| 所在页面 | 断裂引用 | 建议修复 |
|---------|---------|---------|
| ... | → [[xxx]] | 页面不存在，请确认引用是否正确 |

#### 过期数据（{N} 处）
| 公司 | 过期类型 | 最后更新 | 建议 |
|------|---------|---------|------|
| ... | 财务 | 2025-12-31 | 调用 rl-wiki-ingest 更新 |
| ... | 估值 | 2026-03-01 | 调用 rl-wiki-ingest 更新 |

#### 缺失 Section（{N} 处）
| 公司 | 缺失 Section |
|------|-------------|
| ... | 交叉引用、最后更新 |

### 覆盖率统计
| 类别 | 已建 | 总数 | 覆盖率 |
|------|------|------|--------|
| 公司 | {N} | {N} | {X}% |
| 行业 | {N} | {N} | {X}% |
| 概念 | {N} | {N} | {X}% |

### 修复建议
按优先级排序：
1. 🔴 高优先级：{建议}
2. 🟡 中优先级：{建议}
3. 🟢 低优先级：{建议}
```

## 自动化 Python 脚本

对于大规模检查，可使用以下 Python 脚本辅助：

```python
import os
import re
from pathlib import Path
from datetime import datetime, timedelta

WIKI_ROOT = Path("/Users/zhuang225/Research/Vault_共享知识库/wiki")

def check_broken_refs():
    """检查断裂交叉引用"""
    broken = []
    for md in WIKI_ROOT.rglob("*.md"):
        content = md.read_text()
        refs = re.findall(r'→ \[\[(.+?)\]\]', content)
        for ref in refs:
            # 解析引用路径
            if '/' in ref:
                target = WIKI_ROOT / f"{ref}.md"
            else:
                # 搜索所有 companies/industries/concepts
                found = False
                for sub in ["companies", "industries", "concepts", "portfolio"]:
                    for f in (WIKI_ROOT / sub).rglob("*.md"):
                        if ref in f.stem:
                            found = True
                            break
                if not found:
                    broken.append((md, ref))
    return broken

def check_stale_data():
    """检查过期数据"""
    stale = []
    today = datetime.now()
    for md in (WIKI_ROOT / "companies").rglob("*.md"):
        content = md.read_text()
        # 提取最后更新日期
        match = re.search(r'\*\*日期\*\*[:\s]*(\d{4}-\d{2}-\d{2})', content)
        if match:
            update_date = datetime.strptime(match.group(1), "%Y-%m-%d")
            days_since = (today - update_date).days
            if days_since > 90:
                stale.append((md.stem, "财务", match.group(1), days_since))
            elif days_since > 14:
                stale.append((md.stem, "估值", match.group(1), days_since))
    return stale

def check_missing_sections():
    """检查缺失必填Section"""
    missing = []
    required = ["公司概况", "投资逻辑", "财务摘要", "估值水平", "风险因素", "交叉引用", "最后更新"]
    for md in (WIKI_ROOT / "companies").rglob("*.md"):
        content = md.read_text()
        for section in required:
            if section not in content:
                missing.append((md.stem, section))
    return missing

def check_coverage():
    """检查覆盖率"""
    wiki_companies = list((WIKI_ROOT / "companies").rglob("*.md"))
    vault_root = Path("/Users/zhuang225/Research/Vault_公司基本面Agent/11_公司列表")
    total_companies = 0
    for letter_dir in vault_root.iterdir():
        if letter_dir.is_dir():
            total_companies += len(list(letter_dir.iterdir()))
    return len(wiki_companies), total_companies

if __name__ == "__main__":
    broken = check_broken_refs()
    stale = check_stale_data()
    missing = check_missing_sections()
    wiki_count, total_count = check_coverage()

    print(f"=== Wiki 健康检查 ===")
    print(f"断裂引用: {len(broken)}")
    print(f"过期数据: {len(stale)}")
    print(f"缺失Section: {len(missing)}")
    print(f"Wiki 覆盖率: {wiki_count}/{total_count} = {wiki_count/total_count*100:.1f}%")
```

## 执行流程

1. **运行检查**：使用上述脚本或手动逐项检查
2. **生成报告**：汇总所有检查结果
3. **输出修复建议**：按优先级排序
4. **更新索引**：将覆盖率统计写入 `wiki/index.md`

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| Wiki 目录不存在 | 提示"⚠️ Wiki 尚未初始化，请先运行 rl-wiki-ingest 初始化" |
| 页面读取失败 | 跳过该页面，报告"⚠️ 无法读取 {页面名}" |
| Python 脚本执行失败 | 降级为手动检查模式 |

## 注意事项

1. **只读操作**：本 Skill 只检查不修改，修复由用户决定是否执行
2. **建议而非强制**：过期数据和建议只是提醒，不自动修复
3. **支持部分检查**：可只运行特定检查项，如"只检查断裂引用"

---

*版本：v1.0 | 2026-04-11*
*核心职责：Wiki 健康检查与质量保障*
*Schema：Vault_共享知识库/wiki/CLAUDE.md*
