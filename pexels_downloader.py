import argparse
import csv
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm


PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

VALID_SIZES = {
    "original", "large2x", "large", "medium",
    "small", "portrait", "landscape", "tiny"
}

VALID_ORIENTATIONS = {"landscape", "portrait", "square"}
VALID_API_SIZES = {"large", "medium", "small"}


def safe_name(text: str) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in text).strip()


def get_extension(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix
    return ext if ext else ".jpg"


def request_json(session, headers, params, retries=3):
    for attempt in range(retries):
        r = session.get(
            PEXELS_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=30,
        )

        if r.status_code == 429:
            wait = 60 * (attempt + 1)
            print(f"触发限流，等待 {wait} 秒后重试...")
            time.sleep(wait)
            continue

        if r.status_code != 200:
            raise RuntimeError(f"API 请求失败: {r.status_code} {r.text}")

        remaining = r.headers.get("X-Ratelimit-Remaining")
        if remaining is not None:
            print(f"API 剩余额度: {remaining}")

        return r.json()

    raise RuntimeError("API 请求多次失败。")


def fetch_photos(
    api_key,
    queries,
    count,
    orientation=None,
    api_size=None,
    color=None,
    locale=None,
    delay=0.25,
):
    headers = {"Authorization": api_key}
    session = requests.Session()

    all_photos = []
    seen_ids = set()

    per_page = 80

    for query in queries:
        page = 1

        while len(all_photos) < count:
            params = {
                "query": query,
                "per_page": per_page,
                "page": page,
            }

            if orientation:
                params["orientation"] = orientation

            if api_size:
                params["size"] = api_size

            if color:
                params["color"] = color

            if locale:
                params["locale"] = locale

            data = request_json(session, headers, params)
            photos = data.get("photos", [])

            if not photos:
                break

            for photo in photos:
                if photo["id"] not in seen_ids:
                    seen_ids.add(photo["id"])
                    all_photos.append(photo)

                if len(all_photos) >= count:
                    break

            print(f"关键词: {query} | 第 {page} 页 | 已收集: {len(all_photos)}")

            if "next_page" not in data:
                break

            page += 1
            time.sleep(delay)

        if len(all_photos) >= count:
            break

    return all_photos[:count]


def passes_local_filters(photo, min_width, min_height):
    if min_width and photo.get("width", 0) < min_width:
        return False

    if min_height and photo.get("height", 0) < min_height:
        return False

    return True


def download_one(photo, output_dir, image_size, timeout=60, retries=3):
    photo_id = str(photo["id"])
    url = photo["src"].get(image_size)

    if not url:
        return False, photo_id, f"没有该尺寸: {image_size}"

    ext = get_extension(url)
    filename = f"{photo_id}_{image_size}{ext}"
    file_path = output_dir / filename

    if file_path.exists() and file_path.stat().st_size > 0:
        return True, photo_id, "已存在，跳过"

    tmp_path = output_dir / f"{filename}.part"

    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, timeout=timeout) as r:
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")

                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 64):
                        if chunk:
                            f.write(chunk)

            tmp_path.rename(file_path)
            return True, photo_id, "下载成功"

        except Exception as e:
            if tmp_path.exists:
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

            if attempt == retries - 1:
                return False, photo_id, str(e)

            time.sleep(2 * (attempt + 1))

    return False, photo_id, "未知错误"


def save_metadata(photos, output_dir, image_size):
    rows = []

    for p in photos:
        rows.append({
            "id": p.get("id"),
            "width": p.get("width"),
            "height": p.get("height"),
            "url": p.get("url"),
            "photographer": p.get("photographer"),
            "photographer_url": p.get("photographer_url"),
            "photographer_id": p.get("photographer_id"),
            "avg_color": p.get("avg_color"),
            "alt": p.get("alt"),
            "download_url": p.get("src", {}).get(image_size),
            "attribution": f"Photo by {p.get('photographer')} on Pexels",
        })

    csv_path = output_dir / "metadata.csv"
    xlsx_path = output_dir / "metadata.xlsx"

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False)

    return csv_path, xlsx_path


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Pexels 官方 API 批量图片下载器"
    )

    parser.add_argument(
        "--query",
        nargs="+",
        required=True,
        help='搜索关键词，可多个，例如: --query "kid study" "children reading"',
    )

    parser.add_argument(
        "--count",
        type=int,
        default=500,
        help="最多下载图片数量",
    )

    parser.add_argument(
        "--out",
        default=None,
        help="输出目录，默认根据关键词自动生成",
    )

    parser.add_argument(
        "--size",
        default="large2x",
        choices=sorted(VALID_SIZES),
        help="下载图片尺寸",
    )

    parser.add_argument(
        "--orientation",
        choices=sorted(VALID_ORIENTATIONS),
        default=None,
        help="方向筛选",
    )

    parser.add_argument(
        "--api-size",
        choices=sorted(VALID_API_SIZES),
        default=None,
        help="API 侧尺寸筛选: large / medium / small",
    )

    parser.add_argument(
        "--color",
        default=None,
        help="颜色筛选，例如 red、blue、#ffffff",
    )

    parser.add_argument(
        "--locale",
        default="zh-CN",
        help="搜索语言区域，例如 zh-CN / en-US",
    )

    parser.add_argument(
        "--min-width",
        type=int,
        default=0,
        help="本地筛选最小宽度",
    )

    parser.add_argument(
        "--min-height",
        type=int,
        default=0,
        help="本地筛选最小高度",
    )

    parser.add_argument(
        "--threads",
        type=int,
        default=8,
        help="下载线程数",
    )

    args = parser.parse_args()

    api_key = os.getenv("PEXELS_API_KEY")

    if not api_key:
        raise RuntimeError("未找到 PEXELS_API_KEY，请在 .env 中配置。")

    if args.out:
        output_dir = Path(args.out)
    else:
        output_dir = Path("pexels_" + safe_name("_".join(args.query)))

    output_dir.mkdir(parents=True, exist_ok=True)

    photos = fetch_photos(
        api_key=api_key,
        queries=args.query,
        count=args.count,
        orientation=args.orientation,
        api_size=args.api_size,
        color=args.color,
        locale=args.locale,
    )

    photos = [
        p for p in photos
        if passes_local_filters(p, args.min_width, args.min_height)
    ]

    print(f"筛选后图片数: {len(photos)}")

    save_metadata(photos, output_dir, args.size)

    print("开始下载...")

    results = []

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = [
            executor.submit(download_one, p, output_dir, args.size)
            for p in photos
        ]

        for future in tqdm(as_completed(futures), total=len(futures)):
            results.append(future.result())

    success = sum(1 for ok, _, _ in results if ok)
    failed = len(results) - success

    log_path = output_dir / "download_log.csv"

    with open(log_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["success", "photo_id", "message"])
        writer.writerows(results)

    print(f"完成：成功 {success} 张，失败 {failed} 张")
    print(f"图片目录：{output_dir.resolve()}")
    print(f"元数据：{output_dir / 'metadata.csv'}")
    print(f"下载日志：{log_path}")


if __name__ == "__main__":
    main()