---
name: rabyte
description: 彬元投资 Rabyte API。查询点评数据、公开纪要、公开路演、个股热搜、题材热度等。当用户说"查一下纪要"、"最近的公开路演"、"个股热搜"、"题材热度"、"分析师点评"时触发。
---

# 彬元投资 Rabyte API Skill

## 基本信息

| 项目 | 值 |
|------|-----|
| 测试环境地址 | `https://open-api.rabyte.cn` |
| App ID | `ogvmBxuXfUbWWtWKeAGR9vBZ` |
| 调用方式 | HTTP POST |
| 数据接口路径 | `/alpha/open-api/v1/data-manager/query` |
| 文件下载路径 | `/alpha/open-api/v1/file/download` |
| 单次最大返回 | 3000 条 |

---

## 认证方式

请求时在 Header 中增加 `app-agent`，value 为 app_id：

```
app-agent: ogvmBxuXfUbWWtWKeAGR9vBZ
Content-Type: application/json
```

---

## 通用请求格式

```json
{
  "apiName": "<接口名称>",
  "params": {
    "start_time": "2025-01-01 00:00:00",
    "end_time": "",
    "size": 10
  },
  "fields": []
}
```

| 参数 | 类型 | 说明 |
|------|------|------|
| apiName | string | **必选**，接口名称 |
| params.start_time | string | **必传**，上一次同步的最大更新时间，初次设为 `2025-01-01 00:00:00` |
| params.end_time | string | 结束时间，不填则查到最后 |
| params.size | int | 返回数量 |
| fields | array | 返回字段，**必填**，空数组表示返回所有字段 |

---

## 五大数据接口

### 1. get_comment_info_bytz — 获取点评数据

分析师/机构对个股的点评内容、业绩交流纪要等。

**特有参数：** 无（通用参数即可）

**返回字段示例：**
| 字段 | 说明 |
|------|------|
| cmnt_hcode | 点评ID |
| title | 点评标题 |
| content | 点评正文 |
| psn_name | 分析师姓名 |
| team_cname | 团队名称 |
| inst_cname | 机构名称 |
| cmnt_date | 点评日期 |
| hcreatetime | 创建时间 |
| hupdatetime | 更新时间 |
| hisvalid | 是否有效 |

**Python 调用示例：**
```python
import requests
import json

url = "https://open-api.rabyte.cn/alpha/open-api/v1/data-manager/query"
payload = json.dumps({
    "apiName": "get_comment_info_bytz",
    "params": {
        "start_time": "2025-01-01 00:00:00",
        "end_time": "",
        "size": 10
    },
    "fields": []
})
headers = {
    'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
```

---

### 2. get_summary_roadshow_info_bytz — 获取公开纪要信息

路演/策略会/业绩交流的纪要列表信息。

**返回字段示例：**
| 字段 | 说明 |
|------|------|
| trans_id | 纪要ID |
| roadshow_id | 路演ID |
| trans_title | 纪要标题 |
| show_title | 显示标题 |
| company | 主办券商/机构 |
| inst_cname | 机构名称 |
| host | 主持人/分析师 |
| guest | 嘉宾 |
| stime | 开始时间 |
| browsecount | 浏览次数 |
| playcount | 播放次数 |
| word_count | 字数 |
| est_reading_time | 预计阅读时间 |
| content | 纪要内容存储路径（用于文件下载） |
| sec_json | 涉及股票 JSON |
| ind_json | 涉及行业 JSON |
| hcreatetime | 创建时间 |
| hupdatetime | 更新时间 |
| hisvalid | 是否有效 |

**Python 调用示例：**
```python
import requests
import json

url = "https://open-api.rabyte.cn/alpha/open-api/v1/data-manager/query"
payload = json.dumps({
    "apiName": "get_summary_roadshow_info_bytz",
    "params": {
        "start_time": "2025-01-01 00:00:00",
        "end_time": "",
        "size": 10
    },
    "fields": []
})
headers = {
    'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
```

---

### 3. get_public_roadshow_bytz — 获取公开路演信息

路演活动的公开信息（不含纪要内容）。

**返回字段示例：**
| 字段 | 说明 |
|------|------|
| roadshow_id | 路演ID |
| title | 路演标题 |
| type | 路演类型 |
| scope | 路演范围（一对多等） |
| platform | 平台（进门财经等） |
| guest | 嘉宾 |
| guest_title | 嘉宾职位 |
| industry_name | 行业 |
| stime | 开始时间 |
| etime | 结束时间 |
| livecount | 观看人数 |
| address | 路演链接 |
| hcreatetime | 创建时间 |
| hupdatetime | 更新时间 |
| hisvalid | 是否有效 |

**Python 调用示例：**
```python
import requests
import json

url = "https://open-api.rabyte.cn/alpha/open-api/v1/data-manager/query"
payload = json.dumps({
    "apiName": "get_public_roadshow_bytz",
    "params": {
        "start_time": "2025-01-01 00:00:00",
        "end_time": "",
        "size": 10
    },
    "fields": []
})
headers = {
    'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
```

---

### 4. get_user_behavior_stock_bytz — 获取个股热搜

投资者搜索个股的热搜排行数据。

**返回字段示例：**
| 字段 | 说明 |
|------|------|
| sec_name | 股票名称 |
| sec_hcode | 股票代码 |
| comb_symbol | 交易所代码 |
| item_group | 搜索类型（综合搜索等） |
| num_rank | 排名 |
| num | 搜索数量 |
| add_seq | 追加序号 |
| trading_day | 交易日期 |
| time_begin | 开始时间 |
| time_end | 结束时间 |
| inst_type | 投资者类型（公募等） |
| event_name | 事件名称 |
| hisvalid | 是否有效 |

**Python 调用示例：**
```python
import requests
import json

url = "https://open-api.rabyte.cn/alpha/open-api/v1/data-manager/query"
payload = json.dumps({
    "apiName": "get_user_behavior_stock_bytz",
    "params": {
        "start_time": "2025-01-01 00:00:00",
        "end_time": "",
        "size": 10
    },
    "fields": []
})
headers = {
    'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
```

---

### 5. get_concept_times_bytz — 获取题材热度

概念板块的热度数据，包括相关研报、路演、点评数量等。

**返回字段示例：**
| 字段 | 说明 |
|------|------|
| concept_hcode | 题材代码 |
| concept_name | 题材名称 |
| type | 类型 |
| freq | 频率（DAY等） |
| end_date | 结束日期 |
| cmnt | 点评数 |
| cmnt_3 | 3日点评数 |
| research_report | 研报数 |
| research_report_3 | 3日研报数 |
| roadshow | 路演数 |
| roadshow_3 | 3日路演数 |
| sum_all | 总热度 |
| sum_all_3 | 3日总热度 |
| sum_all_qoq_3 | 3日环比 |
| hisvalid | 是否有效 |

**Python 调用示例：**
```python
import requests
import json

url = "https://open-api.rabyte.cn/alpha/open-api/v1/data-manager/query"
payload = json.dumps({
    "apiName": "get_concept_times_bytz",
    "params": {
        "start_time": "2025-01-01 00:00:00",
        "end_time": "",
        "size": 10
    },
    "fields": []
})
headers = {
    'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
```

---

## 文件下载接口

纪要和报告附件的下载。

**路径：** `POST /alpha/open-api/v1/file/download`

**请求参数：**
| 参数 | 类型 | 说明 |
|------|------|------|
| type | string | 文件类型 |
| filePath | string | 文件路径（来自纪要接口的 content 字段） |

**Python 调用示例：**
```python
import requests
import json

url = "https://open-api.rabyte.cn/alpha/open-api/v1/file/download"
payload = json.dumps({
    "type": "2",
    "filePath": "performance_meeting/AI_summary/2026/01/12/AI纪要_浙商交运 航空一刻钟（42）：行业反内卷，航司盈利加速修复____RS000000000378704.json"
})
headers = {
    'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
    'Content-Type': 'application/json'
}
response = requests.request("POST", url, headers=headers, data=payload)
print(response.status_code)
print(response.text)
```

---

## 统一调用函数

```python
import requests
import json

def call_rabyte(api_name, start_time="2025-01-01 00:00:00", end_time="", size=10, fields=None):
    """
    彬元投资 Rabyte API 统一调用函数

    :param api_name: 接口名称
    :param start_time: 开始时间
    :param end_time: 结束时间
    :param size: 返回数量
    :param fields: 返回字段列表，空列表返回所有字段
    """
    url = "https://open-api.rabyte.cn/alpha/open-api/v1/data-manager/query"
    payload = json.dumps({
        "apiName": api_name,
        "params": {
            "start_time": start_time,
            "end_time": end_time,
            "size": size
        },
        "fields": fields if fields is not None else []
    })
    headers = {
        'app-agent': 'ogvmBxuXfUbWWtWKeAGR9vBZ',
        'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return response.json()


# 使用示例
if __name__ == "__main__":
    # 查询最新点评
    result = call_rabyte("get_comment_info_bytz", size=5)
    print(result)

    # 查询公开纪要
    result = call_rabyte("get_summary_roadshow_info_bytz", size=5)
    print(result)

    # 查询个股热搜
    result = call_rabyte("get_user_behavior_stock_bytz", size=10)
    print(result)

    # 查询题材热度
    result = call_rabyte("get_concept_times_bytz", size=10)
    print(result)
```

---

## 响应格式

所有接口返回格式统一：

```json
{
  "code": 200000,
  "message": "success",
  "data": {
    "data": [ /* 数据数组 */ ],
    "hasMore": true,
    "count": 63296
  }
}
```

| 字段 | 说明 |
|------|------|
| code | 状态码，200000 表示成功 |
| message | 状态信息 |
| data.data | 数据数组 |
| data.hasMore | 是否还有更多数据 |
| data.count | 总数据量 |

---

## 增量同步策略

所有数据接口通过 `start_time` 字段实现增量同步：

1. **首次同步**：设置 `start_time` 为 `2025-01-01 00:00:00`
2. **后续同步**：使用上一次返回结果中的最大 `hupdatetime`（更新时间）作为新的 `start_time`
3. **持续增量**：每次查询后更新 `start_time`，避免重复拉取

---

## 注意事项

1. **单次最大返回 3000 条**，大批量同步需分页
2. **start_time 必传**，否则接口会报错
3. **fields 空数组 `[]` 表示返回所有字段**
4. **文件下载**：纪要正文通过单独的文件下载接口获取，路径来自 `content` 字段
5. **hisvalid = 1** 表示数据有效，查询时应过滤无效数据
