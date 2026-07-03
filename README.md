# **Pexels Downloader**

一个基于 **Pexels 官方 API** 的批量图片下载工具。

支持：

- ✅ 官方 API（无需爬虫）
- ✅ 多关键词搜索
- ✅ 自动翻页
- ✅ 多线程下载
- ✅ 自动去重
- ✅ 断点续传（已下载文件自动跳过）
- ✅ 图片方向筛选
- ✅ 图片尺寸筛选
- ✅ 最小分辨率筛选
- ✅ 导出 CSV / Excel 元数据
- ✅ 下载日志

------

# **目录结构**

```text
.
├── pexels_downloader.py
├── .env
├── README.md
└── pexels_kid_study/
    ├── 123456_large2x.jpg
    ├── 987654_large2x.jpg
    ├── metadata.csv
    ├── metadata.xlsx
    └── download_log.csv
```

------

# **环境要求**

- Python 3.9+
- Windows / macOS / Linux

------

# **安装**

克隆项目（或下载源码）：

```bash
git clone <your-repo>
cd <your-repo>
```

安装依赖：

```bash
pip install requests tqdm pandas python-dotenv openpyxl
```

------

# **获取 API Key**

访问 Pexels 官方网站申请免费的 API Key：

https://www.pexels.com/api/

创建 `.env` 文件：

```env
PEXELS_API_KEY=你的API密钥
```

例如：

```env
PEXELS_API_KEY=563492ad6f91700001000001xxxxxxxxxxxxxxxx
```

------

# **基本使用**

下载 500 张 **kid study** 图片：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --count 500
```

------

下载多个关键词（自动去重）：

```bash
python pexels_downloader.py \
    --query \
    "kid study" \
    "children reading" \
    "student homework" \
    --count 1000
```

------

指定输出目录：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --out ./dataset
```

------

下载 Original 原图：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --size original
```

------

下载 Large2x：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --size large2x
```

------

# **可下载尺寸**

| **参数**  | **说明** |
| --------- | -------- |
| original  | 原图     |
| large2x   | 超高清   |
| large     | 高清     |
| medium    | 中等     |
| small     | 小图     |
| portrait  | 竖图     |
| landscape | 横图     |
| tiny      | 缩略图   |

例如：

```bash
--size large2x
```

------

# **图片方向筛选**

仅下载横图：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --orientation landscape
```

支持：

- landscape
- portrait
- square

------

# **API 尺寸筛选**

Pexels API 支持：

```bash
--api-size large
```

可选：

- large
- medium
- small

------

# **本地分辨率筛选**

仅下载宽度 ≥1920，高度 ≥1080：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --min-width 1920 \
    --min-height 1080
```

------

# **颜色筛选**

例如下载蓝色图片：

```bash
python pexels_downloader.py \
    --query ocean \
    --color blue
```

也支持：

```text
red
orange
yellow
green
turquoise
blue
violet
pink
brown
black
gray
white
```

------

# **多线程下载**

默认：

```text
8 个线程
```

修改：

```bash
--threads 16
```

例如：

```bash
python pexels_downloader.py \
    --query "kid study" \
    --threads 16
```

------

# **输出文件**

下载完成后生成：

## **图片**

```text
123456_large2x.jpg
```

------

## **metadata.csv**

包含：

- 图片 ID
- 摄影师
- 摄影师主页
- 摄影师 ID
- 图片尺寸
- 图片链接
- 下载链接
- ALT 描述
- 平均颜色
- Attribution（署名信息）

------

## **metadata.xlsx**

Excel 格式元数据。

------

## **download_log.csv**

记录每张图片：

- 是否成功
- 图片 ID
- 错误信息

方便重新下载失败项。

------

# **断点续传**

如果图片已经存在：

```text
123456_large2x.jpg
```

程序会自动跳过，不会重复下载。

因此可以多次执行同一命令，无需担心重复。

------

# **常见问题**

## **下载速度慢**

可以增加线程：

```bash
--threads 16
```

注意不要设置过高，以免触发 API 限流。

------

## **出现 429 Too Many Requests**

表示请求频率过高。

程序会自动等待后重试。

------

## **下载数量不足**

Pexels 每页最多返回 80 张数据。

程序会自动翻页。

如果最终数量仍不足，说明当前关键词在 Pexels 上没有更多符合条件的图片。

------

## **Original 下载失败**

部分图片可能没有对应尺寸。

建议使用：

```bash
--size large2x
```

兼容性更好。

------

# **注意事项**

- 本工具基于 **Pexels 官方 API**，请遵守 Pexels API 使用条款。
- 请保留摄影师署名等必要信息（工具已在元数据中导出）。
- API 存在访问配额限制，请合理控制下载频率和数量。

------

# **License**

本项目仅作为学习和开发示例。

请遵守 Pexels 官方 API License 与 Terms of Service。