import csv
import os
import shutil
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk


# =========================
# 分类配置
# =========================

CATEGORIES = {
    "high_risk": ["蹲在地上", "流血受伤", "呕吐", "爬到高处", "躺在地上"],
    "low_risk": ["使用手表", "使用手机", "使用PAD"],
    "mid_risk": ["不盖被子睡觉", "看书离得太近", "使用明火_着火", "小孩坐姿"],
    "positive": ["看书", "扫地", "小孩拖地", "写作业", "整理床铺", "整理书桌"],
}

RISK_ORDER = ["high_risk", "mid_risk", "low_risk", "positive"]

RISK_ICONS = {
    "high_risk": "🚨",
    "mid_risk": "⚠️",
    "low_risk": "🛡️",
    "positive": "👍",
}

RISK_COLORS = {
    "high_risk": "#ef4444",
    "mid_risk": "#f97316",
    "low_risk": "#22c55e",
    "positive": "#1677ff",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


# =========================
# 工具函数
# =========================

def ensure_dirs(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "skipped").mkdir(parents=True, exist_ok=True)
    (root / "deleted").mkdir(parents=True, exist_ok=True)
    for risk, labels in CATEGORIES.items():
        for label in labels:
            (root / risk / label).mkdir(parents=True, exist_ok=True)


def list_pending_images(root: Path):
    if not root.exists():
        return []
    return sorted(
        [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
        key=lambda p: p.name.lower(),
    )


def count_images(folder: Path):
    if not folder.exists():
        return 0
    return len([p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS])


def unique_path(path: Path):
    if not path.exists():
        return path
    i = 1
    while True:
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def write_log(root: Path, action: str, src: Path, dst: Path, risk="", label=""):
    log_path = root / "review_log.csv"
    need_header = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if need_header:
            writer.writerow(["time", "action", "risk", "label", "source", "destination"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            action,
            risk,
            label,
            str(src),
            str(dst),
        ])


# =========================
# 主应用
# =========================

class ImageReviewApp:
    def __init__(self, master):
        self.master = master
        self.master.title("图片审核分类工具")
        self.master.geometry("1500x900")
        self.master.minsize(1200, 760)

        self.root_dir = Path("./dataset").resolve()
        self.images = []
        self.index = 0
        self.selected_risk = "positive"
        self.selected_label = CATEGORIES["positive"][0]
        self.last_move = None
        self.current_photo = None
        self.thumb_photos = []

        self.setup_styles()
        self.build_ui()
        self.bind_keys()

        ensure_dirs(self.root_dir)
        self.path_var.set(str(self.root_dir))
        self.refresh_all()

    # ---------------------
    # 样式
    # ---------------------

    def setup_styles(self):
        self.master.configure(bg="#f6f8fb")
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure("TFrame", background="#f6f8fb")
        self.style.configure("Card.TFrame", background="#ffffff", relief="solid", borderwidth=1)
        self.style.configure("Sidebar.TFrame", background="#eef2f7")
        self.style.configure("Title.TLabel", background="#f6f8fb", foreground="#0f172a", font=("Arial", 20, "bold"))
        self.style.configure("Section.TLabel", background="#ffffff", foreground="#0f172a", font=("Arial", 15, "bold"))
        self.style.configure("Text.TLabel", background="#ffffff", foreground="#0f172a", font=("Arial", 11))
        self.style.configure("Muted.TLabel", background="#ffffff", foreground="#64748b", font=("Arial", 10))
        self.style.configure("Sidebar.TLabel", background="#eef2f7", foreground="#0f172a", font=("Arial", 11))
        self.style.configure("SidebarTitle.TLabel", background="#eef2f7", foreground="#0f172a", font=("Arial", 16, "bold"))
        self.style.configure("Big.TButton", font=("Arial", 12, "bold"), padding=10)
        self.style.configure("Normal.TButton", font=("Arial", 11), padding=8)

    # ---------------------
    # UI
    # ---------------------

    def build_ui(self):
        self.main = ttk.Frame(self.master, padding=16)
        self.main.pack(fill="both", expand=True)

        # 三栏布局
        self.sidebar = ttk.Frame(self.main, style="Sidebar.TFrame", padding=16, width=300)
        self.sidebar.pack(side="left", fill="y", padx=(0, 16))
        self.sidebar.pack_propagate(False)

        self.center = ttk.Frame(self.main, padding=0)
        self.center.pack(side="left", fill="both", expand=True)

        self.right = ttk.Frame(self.main, padding=16, width=380, style="Card.TFrame")
        self.right.pack(side="right", fill="y", padx=(16, 0))
        self.right.pack_propagate(False)

        self.build_sidebar()
        self.build_center()
        self.build_right_panel()

    def build_sidebar(self):
        ttk.Label(self.sidebar, text="分类目录", style="SidebarTitle.TLabel").pack(anchor="w", pady=(0, 14))

        ttk.Label(self.sidebar, text="数据集根目录", style="Sidebar.TLabel").pack(anchor="w")
        path_row = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        path_row.pack(fill="x", pady=(6, 14))

        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(path_row, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True)

        browse_btn = ttk.Button(path_row, text="📁", width=3, command=self.choose_folder)
        browse_btn.pack(side="left", padx=(6, 0))

        set_btn = ttk.Button(self.sidebar, text="应用路径 / 刷新", command=self.apply_path)
        set_btn.pack(fill="x", pady=(0, 16))

        self.tree_frame = ttk.Frame(self.sidebar, style="Sidebar.TFrame")
        self.tree_frame.pack(fill="both", expand=True)

        self.stats_frame = ttk.Frame(self.sidebar, padding=14, style="Card.TFrame")
        self.stats_frame.pack(fill="x", pady=(14, 0))

        self.stats_label = ttk.Label(self.stats_frame, text="", style="Text.TLabel", justify="left")
        self.stats_label.pack(anchor="w")

    def build_center(self):
        top = ttk.Frame(self.center)
        top.pack(fill="x", pady=(0, 12))

        ttk.Label(top, text="🔴 🟡 🟢　图片审核分类工具", style="Title.TLabel").pack(side="left")

        status_row = ttk.Frame(self.center, style="Card.TFrame", padding=12)
        status_row.pack(fill="x", pady=(0, 12))

        self.progress_label = ttk.Label(status_row, text="当前图片：0 / 0", style="Text.TLabel")
        self.progress_label.pack(side="left", padx=(0, 18))

        ttk.Button(status_row, text="← 上一张", command=self.prev_image, style="Normal.TButton").pack(side="left", padx=6)
        ttk.Button(status_row, text="下一张 →", command=self.next_image, style="Normal.TButton").pack(side="left", padx=6)
        ttk.Button(status_row, text="跳过 (S)", command=self.skip_image, style="Normal.TButton").pack(side="left", padx=6)
        ttk.Button(status_row, text="删除 (D)", command=self.delete_image, style="Normal.TButton").pack(side="left", padx=6)
        ttk.Button(status_row, text="撤销 (Z)", command=self.undo, style="Normal.TButton").pack(side="left", padx=6)

        self.image_card = ttk.Frame(self.center, style="Card.TFrame", padding=12)
        self.image_card.pack(fill="both", expand=True)

        self.image_canvas = tk.Canvas(self.image_card, bg="#ffffff", highlightthickness=0)
        self.image_canvas.pack(fill="both", expand=True)
        self.image_canvas.bind("<Configure>", lambda e: self.render_current_image())

        bottom = ttk.Frame(self.center, style="Card.TFrame", padding=12)
        bottom.pack(fill="x", pady=(12, 0))

        self.pending_title = ttk.Label(bottom, text="待处理图片 (0)", style="Section.TLabel")
        self.pending_title.pack(anchor="w")

        self.thumb_canvas = tk.Canvas(bottom, height=116, bg="#ffffff", highlightthickness=0)
        self.thumb_canvas.pack(fill="x", pady=(10, 6))

        self.path_label = ttk.Label(bottom, text="当前路径：", style="Muted.TLabel")
        self.path_label.pack(anchor="w")

    def build_right_panel(self):
        ttk.Label(self.right, text="1. 选择风险等级", style="Section.TLabel").pack(anchor="w", pady=(0, 12))

        self.risk_buttons = {}
        for risk in RISK_ORDER:
            btn = tk.Button(
                self.right,
                text=f"{RISK_ICONS[risk]}  {risk}",
                font=("Arial", 12, "bold"),
                height=2,
                relief="solid",
                bd=1,
                command=lambda r=risk: self.select_risk(r),
            )
            btn.pack(fill="x", pady=5)
            self.risk_buttons[risk] = btn

        ttk.Separator(self.right).pack(fill="x", pady=20)

        ttk.Label(self.right, text="2. 选择具体类别", style="Section.TLabel").pack(anchor="w", pady=(0, 12))

        self.label_buttons_frame = ttk.Frame(self.right, style="Card.TFrame")
        self.label_buttons_frame.pack(fill="x")
        self.label_buttons = []

        self.hint_label = ttk.Label(self.right, text="请先选择风险等级，再选择具体类别", style="Muted.TLabel")
        self.hint_label.pack(anchor="w", pady=(12, 0))

        ttk.Separator(self.right).pack(fill="x", pady=22)

        ttk.Label(self.right, text="3. 操作", style="Section.TLabel").pack(anchor="w", pady=(0, 12))

        self.move_btn = tk.Button(
            self.right,
            text="📁  移动到该分类 (Enter)",
            font=("Arial", 13, "bold"),
            bg="#1677ff",
            fg="white",
            height=2,
            relief="flat",
            command=self.classify_current,
        )
        self.move_btn.pack(fill="x", pady=(0, 20))

        help_box = ttk.Frame(self.right, padding=14, style="Card.TFrame")
        help_box.pack(fill="x")

        help_text = (
            "快捷键\n\n"
            "1 / 2 / 3 / 4    选择风险等级\n"
            "Q / W / E / R / T / Y    选择具体类别\n"
            "Enter    移动到该分类\n"
            "S        跳过\n"
            "D        删除\n"
            "Z        撤销\n"
            "← / →    上一张 / 下一张"
        )
        ttk.Label(help_box, text=help_text, style="Text.TLabel", justify="left").pack(anchor="w")

        self.update_selection_ui()

    # ---------------------
    # 数据刷新
    # ---------------------

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=str(self.root_dir))
        if folder:
            self.path_var.set(folder)
            self.apply_path()

    def apply_path(self):
        self.root_dir = Path(self.path_var.get()).expanduser().resolve()
        ensure_dirs(self.root_dir)
        self.index = 0
        self.refresh_all()

    def refresh_all(self):
        self.images = list_pending_images(self.root_dir)
        if self.index >= len(self.images):
            self.index = max(0, len(self.images) - 1)
        self.refresh_sidebar()
        self.refresh_center()

    def refresh_sidebar(self):
        for widget in self.tree_frame.winfo_children():
            widget.destroy()

        for risk, labels in CATEGORIES.items():
            total = count_images(self.root_dir / risk)
            row = ttk.Frame(self.tree_frame, style="Sidebar.TFrame")
            row.pack(fill="x", pady=(8, 0))
            ttk.Label(row, text=f"📁 {risk}", style="Sidebar.TLabel").pack(side="left")
            ttk.Label(row, text=str(total), style="Sidebar.TLabel").pack(side="right")

            for label in labels:
                n = count_images(self.root_dir / risk / label)
                sub = ttk.Frame(self.tree_frame, style="Sidebar.TFrame")
                sub.pack(fill="x", padx=(22, 0), pady=1)
                ttk.Label(sub, text=f"📂 {label}", style="Sidebar.TLabel").pack(side="left")
                ttk.Label(sub, text=str(n), style="Sidebar.TLabel").pack(side="right")

        classified = sum(count_images(self.root_dir / r) for r in CATEGORIES)
        skipped = count_images(self.root_dir / "skipped")
        deleted = count_images(self.root_dir / "deleted")
        total = len(self.images) + classified + skipped + deleted

        self.stats_label.configure(
            text=(
                "统计信息\n\n"
                f"总图片：{total}\n"
                f"待处理：{len(self.images)}\n"
                f"已分类：{classified}\n"
                f"跳过：{skipped}\n"
                f"删除：{deleted}"
            )
        )

    def refresh_center(self):
        self.progress_label.configure(text=f"当前图片： {self.index + 1 if self.images else 0} / {len(self.images)}")
        self.pending_title.configure(text=f"待处理图片 ({len(self.images)})")

        if self.images:
            self.path_label.configure(text=f"当前路径：{self.images[self.index]}")
        else:
            self.path_label.configure(text=f"当前路径：{self.root_dir}")

        self.render_current_image()
        self.render_thumbnails()

    # ---------------------
    # 图片显示
    # ---------------------

    def render_current_image(self):
        self.image_canvas.delete("all")

        if not self.images:
            self.image_canvas.create_text(
                self.image_canvas.winfo_width() // 2,
                self.image_canvas.winfo_height() // 2,
                text=f"没有待审核图片\n请把图片直接放入：\n{self.root_dir}",
                fill="#64748b",
                font=("Arial", 16),
                justify="center",
            )
            return

        path = self.images[self.index]

        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
        except Exception as e:
            self.image_canvas.create_text(
                40, 40,
                text=f"图片读取失败：{e}",
                fill="#ef4444",
                anchor="nw",
                font=("Arial", 14),
            )
            return

        cw = max(self.image_canvas.winfo_width(), 400)
        ch = max(self.image_canvas.winfo_height(), 300)
        margin = 16

        img_ratio = img.width / img.height
        box_w = cw - margin * 2
        box_h = ch - margin * 2
        box_ratio = box_w / box_h

        if img_ratio > box_ratio:
            new_w = box_w
            new_h = int(box_w / img_ratio)
        else:
            new_h = box_h
            new_w = int(box_h * img_ratio)

        display = img.resize((new_w, new_h), Image.LANCZOS)
        self.current_photo = ImageTk.PhotoImage(display)

        x = cw // 2
        y = ch // 2
        self.image_canvas.create_image(x, y, image=self.current_photo, anchor="center")

    def render_thumbnails(self):
        self.thumb_canvas.delete("all")
        self.thumb_photos = []

        if not self.images:
            return

        start = max(0, self.index - 4)
        visible = self.images[start:start + 9]

        x = 8
        for i, path in enumerate(visible):
            try:
                img = Image.open(path)
                img = ImageOps.exif_transpose(img)
                img.thumbnail((96, 80))
                photo = ImageTk.PhotoImage(img)
                self.thumb_photos.append(photo)

                item_x = x + 48
                self.thumb_canvas.create_image(item_x, 46, image=photo, anchor="center")

                real_index = start + i
                if real_index == self.index:
                    self.thumb_canvas.create_rectangle(x, 4, x + 100, 92, outline="#1677ff", width=3)
                else:
                    self.thumb_canvas.create_rectangle(x, 4, x + 100, 92, outline="#e5e7eb", width=1)

                self.thumb_canvas.create_text(x + 8, 8, text=str(real_index + 1), anchor="nw", fill="#0f172a", font=("Arial", 9, "bold"))

                self.thumb_canvas.tag_bind(
                    self.thumb_canvas.create_rectangle(x, 4, x + 100, 92, outline="", fill="", tags=f"thumb_{real_index}"),
                    "<Button-1>",
                    lambda e, idx=real_index: self.jump_to(idx),
                )

                x += 112
            except Exception:
                pass

    # ---------------------
    # 选择 UI
    # ---------------------

    def select_risk(self, risk):
        self.selected_risk = risk
        self.selected_label = CATEGORIES[risk][0]
        self.update_selection_ui()

    def select_label(self, label):
        self.selected_label = label
        self.update_selection_ui()

    def update_selection_ui(self):
        for risk, btn in self.risk_buttons.items():
            if risk == self.selected_risk:
                btn.configure(bg=RISK_COLORS[risk], fg="white", activebackground=RISK_COLORS[risk])
            else:
                btn.configure(bg="#ffffff", fg="#0f172a", activebackground="#f1f5f9")

        for widget in self.label_buttons_frame.winfo_children():
            widget.destroy()
        self.label_buttons.clear()

        labels = CATEGORIES[self.selected_risk]
        shortcuts = ["Q", "W", "E", "R", "T", "Y"]

        for i, label in enumerate(labels):
            key = shortcuts[i] if i < len(shortcuts) else str(i + 1)
            selected = label == self.selected_label
            btn = tk.Button(
                self.label_buttons_frame,
                text=f"{key}. {label}",
                font=("Arial", 11, "bold" if selected else "normal"),
                height=2,
                relief="solid",
                bd=1,
                bg=RISK_COLORS[self.selected_risk] if selected else "#ffffff",
                fg="white" if selected else "#0f172a",
                activebackground=RISK_COLORS[self.selected_risk] if selected else "#f1f5f9",
                command=lambda l=label: self.select_label(l),
            )
            btn.pack(fill="x", pady=5)
            self.label_buttons.append(btn)

        self.move_btn.configure(bg=RISK_COLORS[self.selected_risk])

    # ---------------------
    # 操作
    # ---------------------

    def current_path(self):
        if not self.images:
            return None
        return self.images[self.index]

    def move_current(self, dst_dir: Path, action: str, risk="", label=""):
        src = self.current_path()
        if src is None:
            return

        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = unique_path(dst_dir / src.name)
        shutil.move(str(src), str(dst))
        write_log(self.root_dir, action, src, dst, risk, label)
        self.last_move = {
            "src": str(src),
            "dst": str(dst),
            "risk": risk,
            "label": label,
            "action": action,
        }

        self.images = list_pending_images(self.root_dir)
        if self.index >= len(self.images):
            self.index = max(0, len(self.images) - 1)

        self.refresh_sidebar()
        self.refresh_center()

    def classify_current(self):
        self.move_current(
            self.root_dir / self.selected_risk / self.selected_label,
            "classify",
            self.selected_risk,
            self.selected_label,
        )

    def skip_image(self):
        self.move_current(self.root_dir / "skipped", "skip")

    def delete_image(self):
        self.move_current(self.root_dir / "deleted", "delete")

    def undo(self):
        if not self.last_move:
            messagebox.showinfo("提示", "没有可撤销的操作。")
            return

        src = Path(self.last_move["src"])
        dst = Path(self.last_move["dst"])

        if not dst.exists():
            messagebox.showwarning("无法撤销", "上一步移动后的文件不存在。")
            return

        restored = unique_path(src)
        shutil.move(str(dst), str(restored))
        write_log(self.root_dir, "undo", dst, restored, self.last_move.get("risk", ""), self.last_move.get("label", ""))

        self.last_move = None
        self.images = list_pending_images(self.root_dir)
        try:
            self.index = self.images.index(restored)
        except ValueError:
            self.index = 0

        self.refresh_all()

    def prev_image(self):
        if self.images:
            self.index = max(0, self.index - 1)
            self.refresh_center()

    def next_image(self):
        if self.images:
            self.index = min(len(self.images) - 1, self.index + 1)
            self.refresh_center()

    def jump_to(self, idx):
        if 0 <= idx < len(self.images):
            self.index = idx
            self.refresh_center()

    # ---------------------
    # 快捷键
    # ---------------------

    def bind_keys(self):
        self.master.bind("<Left>", lambda e: self.prev_image())
        self.master.bind("<Right>", lambda e: self.next_image())
        self.master.bind("<Return>", lambda e: self.classify_current())
        self.master.bind("s", lambda e: self.skip_image())
        self.master.bind("S", lambda e: self.skip_image())
        self.master.bind("d", lambda e: self.delete_image())
        self.master.bind("D", lambda e: self.delete_image())
        self.master.bind("z", lambda e: self.undo())
        self.master.bind("Z", lambda e: self.undo())

        risk_keys = {
            "1": "high_risk",
            "2": "mid_risk",
            "3": "low_risk",
            "4": "positive",
        }
        for key, risk in risk_keys.items():
            self.master.bind(key, lambda e, r=risk: self.select_risk(r))

        label_keys = ["q", "w", "e", "r", "t", "y"]
        for i, key in enumerate(label_keys):
            self.master.bind(key, lambda e, idx=i: self.select_label_by_index(idx))
            self.master.bind(key.upper(), lambda e, idx=i: self.select_label_by_index(idx))

    def select_label_by_index(self, idx):
        labels = CATEGORIES[self.selected_risk]
        if 0 <= idx < len(labels):
            self.select_label(labels[idx])


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageReviewApp(root)
    root.mainloop()
