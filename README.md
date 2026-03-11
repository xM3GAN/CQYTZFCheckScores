# 重庆移通学院教务系统成绩自动推送

> 基于 [NianBroken/ZFCheckScores](https://github.com/NianBroken/ZFCheckScores) 修改，适配重庆移通学院 **CAS 统一身份认证 + WebVPN + 正方教务系统** 的完整链路。

## 简介

每隔 30 分钟自动检测教务系统成绩是否更新，若有更新，**自动推送通知到微信**。

**使用前：** 早上看一遍教务系统、课间看一遍、吃饭看一遍、睡前看一遍……

**使用后：** 成绩一出，微信立刻收到通知。

## 与上游项目的区别

上游项目要求教务系统可从外网直接访问。重庆移通学院的教务系统在**内网**，外网必须通过 **WebVPN** 才能访问，且 WebVPN 需要先通过 **CAS 统一身份认证**。

本项目新增了 **CAS + WebVPN 前置认证模块**，完整链路如下：

```
GitHub Actions 定时触发
    ↓
CAS 统一身份认证登录 (AES-CBC 加密密码)
    ↓
获取 CAS ticket
    ↓
调用 VPN /api/access/auth/finish 接口
    ↓
获取 webvpn-token (JWT)
    ↓
携带 token 访问教务系统 (RSA 加密密码登录)
    ↓
获取成绩 → 比对是否更新 → 推送微信
```

### 新增 / 修改的文件

| 文件 | 说明 |
|------|------|
| `scripts/cas_vpn_login.py` | **新增** CAS 统一认证 + WebVPN token 获取模块 |
| `main.py` | **修改** 增加 CAS 前置认证分支，检测到 `CAS_PASSWORD` 时自动启用 |
| `scripts/user_login.py` | **修改** 支持注入 VPN token 后再走教务系统登录 |
| `.github/workflows/main.yml` | **修改** 新增 `pycryptodome` 依赖及 CAS 环境变量 |

## 功能

1. 每 30 分钟自动检测成绩更新，更新时微信推送通知
2. 显示成绩提交时间、提交人
3. 成绩按时间降序排列，最新的在最上面
4. 计算 GPA 和百分制 GPA
5. 对"及格""良好"等文字成绩强制显示数字分数
6. 显示未公布成绩的课程
7. 支持手动触发强制推送

## 使用方法

### 1. Fork 本仓库

点击页面右上角 `Fork` → `Create fork`

### 2. 开启工作流读写权限

`Settings` → `Actions` → `General` → `Workflow permissions` → 选择 `Read and write permissions` → `Save`

### 3. 添加 Secrets

`Settings` → `Secrets and variables` → `Actions` → `Secrets` → `Repository secrets` → `New repository secret`

需要添加以下 **6 个** Secrets：

| Name | 示例 | 说明 |
|------|------|------|
| `URL` | `https://abcd.com/jwglxt/` | 教务系统的 WebVPN 地址 |
| `USERNAME` | `5201314` | 学号 |
| `PASSWORD` | `abcdefg` | **教务系统**密码 |
| `TOKEN` | `abcdefg` | [Showdoc 推送 token](https://push.showdoc.com.cn/#/push) |
| `CAS_PASSWORD` | `MyP@ssw0rd` | **CAS 统一身份认证**密码（登录 ids.cqytxy.edu.cn 的密码） |
| `CAS_USERNAME` | `5201314` | （可选）CAS 用户名，默认与 `USERNAME` 相同，可不添加 |

> **注意：** `PASSWORD` 和 `CAS_PASSWORD` 可能不一样！`CAS_PASSWORD` 是你登录学校统一身份认证平台的密码，`PASSWORD` 是教务系统自己的密码。如果两个密码相同，都填一样的值即可。

> **注意：** Secrets 输入框是纯文本，密码中如果有 `\` 等特殊字符，直接输入即可，**不需要**转义。

#### 如何获取 Showdoc 推送 TOKEN？

1. 打开 [Showdoc 推送服务](https://push.showdoc.com.cn/#/push)
2. 微信扫码关注公众号
3. 页面上显示的字符串就是你的 TOKEN

### 4. 开启 Actions

`Actions` → `I understand my workflows, go ahead and enable them` → `CheckScores` → `Enable workflow`

### 5. 运行程序

`Actions` → `CheckScores` → `Run workflow` → `Run workflow`

程序正常运行后，之后每隔 30 分钟会自动检测一次成绩。

## 常见问题

### Q: CAS 认证成功但教务系统登录失败（code: 1002）

A: `PASSWORD` 填的不对。教务系统密码不一定和 CAS 密码相同。

### Q: CAS 登录失败，提示需要验证码

A: 短时间内登录失败次数过多会触发验证码。等待一段时间后重试。

### Q: 不填 CAS_PASSWORD 会怎样？

A: 程序会走原版的直接登录流程（不经过 CAS 和 VPN），适用于教务系统可直接访问的学校。

## 程序逻辑

1. CAS 统一身份认证登录，获取 ticket
2. 调用 VPN 接口，用 ticket 换取 `webvpn-token`
3. 携带 token 登录教务系统
4. 获取成绩，MD5 加密后与上次保存的对比
5. 如果不一致，说明成绩更新了，推送微信通知


## 致谢

- [NianBroken/ZFCheckScores](https://github.com/NianBroken/ZFCheckScores) — 上游项目
- [openschoolcn/zfn_api](https://github.com/openschoolcn/zfn_api) — 正方教务 API
