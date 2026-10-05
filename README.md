# envdiff

比较两个 `.env` 文件的差异：新增 / 删除 / 变更，一目了然。

最核心的设计：**值的原文默认打码，只显示长度**。因为 diff 输出经常被复制粘贴进工单、聊天窗口、CI 日志——明文密钥一旦进去就收不回来。要看原文必须显式加 `--show-values`，这是故意的摩擦。

## 安装

零依赖，Python 3.10+：

```bash
git clone https://github.com/ljiang9/envdiff.git
cd envdiff
python3 -m envdiff .env.old .env.new
```

## 用法

```bash
# 基本对比（值打码）
python3 -m envdiff .env.a .env.b

# 显示值的原文（确认输出不会泄漏再用）
python3 -m envdiff .env.a .env.b --show-values

# 忽略某些键（比如每次部署都变的构建号）
python3 -m envdiff .env.a .env.b --ignore BUILD_ID GIT_SHA

# 机器可读
python3 -m envdiff .env.a .env.b --json
```

示例输出：

```
~ DATABASE_URL: <38 字符> -> <33 字符>    （变更）
~ DEBUG: <4 字符> -> <5 字符>    （变更）
+ NEW_KEY = <10 字符>    （新增）
- OLD_KEY = <13 字符>    （删除）

共 4 处差异。
```

## 退出码

| 码 | 含义 |
|---|------|
| 0 | 两个文件完全一致 |
| 1 | 有差异 |
| 2 | 用法错误 / 文件读不了 |

适合放进 CI：部署前对比 `.env.example` 和实际配置，`--ignore` 掉环境相关项。

## 解析规则

- `KEY=value`、`export KEY=value`、`KEY="quoted"`、`KEY='quoted'` 都支持
- 行尾注释：`KEY=x  # 注释` 会被去掉，但**引号里的 `#` 不算注释**：`KEY="a#b"` → `a#b`
- 双引号内支持 `\n` `\t` `\"` `\\` 转义
- 键名必须是 `[A-Za-z_][A-Za-z0-9_]*`，不合法的行记警告并跳过
- 无法解析的行（比如没有 `=`）只记警告，**不崩溃**

## 诚实说明

- 这是**配置漂移**工具，不是密钥管理工具。它不存密钥、不轮换密钥、不校验密钥强度。
- 多行值（引号跨行）**不支持**，会产生警告并按单行处理——这是已知取舍。
- `--show-values` 的输出请确保不会进日志系统；打码是默认行为，请保持默认。
- 对比的是解析后的值，不是原始文本：`KEY="a"` 和 `KEY=a` 视为相同。
