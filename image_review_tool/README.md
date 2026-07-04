# 本地图片审核分类工具：桌面版

这个版本改成了 **Tkinter 原生桌面应用**，不再依赖 Streamlit 页面刷新。

解决的问题：

- 标题显示不全的问题
- 点击选择分类时页面整体刷新、图片重新加载的问题
- 默认路径不带 `raw`
- 快捷键更稳定

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python image_review_desktop.py
```

## 使用

待审核图片直接放到数据集根目录，例如：

```text
dataset3/
├── 001.jpg
├── 002.jpg
├── 003.jpg
```

运行工具后，左侧选择或输入：

```text
./dataset3
```

工具会自动创建：

```text
high_risk/
low_risk/
mid_risk/
positive/
skipped/
deleted/
review_log.csv
```

## 分类结构

```text
high_risk/
├── 蹲在地上/
├── 流血受伤/
├── 呕吐/
├── 爬到高处/
└── 躺在地上/

low_risk/
├── 使用手表/
├── 使用手机/
└── 使用PAD/

mid_risk/
├── 不盖被子睡觉/
├── 看书离得太近/
├── 使用明火_着火/
└── 小孩坐姿/

positive/
├── 看书/
├── 扫地/
├── 小孩拖地/
├── 写作业/
├── 整理床铺/
└── 整理书桌/
```

## 快捷键

```text
1 / 2 / 3 / 4    选择风险等级
Q / W / E / R / T / Y    选择具体类别
Enter            移动到该分类
S                跳过
D                删除
Z                撤销
← / →            上一张 / 下一张
```

## 日志

所有操作都会记录到：

```text
review_log.csv
```
