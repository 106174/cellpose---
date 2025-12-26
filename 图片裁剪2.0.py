import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import glob
import shutil


class ReferenceWindow:
    """参考图片窗口类"""

    def __init__(self, main_app, root):
        self.main_app = main_app  # 持有主程序的引用，用于交互
        self.window = tk.Toplevel(root)
        self.window.title("【参考图窗口】用于对照")
        self.window.geometry("600x600")

        # 变量初始化
        self.folder_path = ""
        self.image_files = []
        self.current_index = 0
        self.original_image = None
        self.tk_image = None
        self.zoom_factor = 1.0

        # UI组件
        self.create_widgets()

        # 绑定窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def create_widgets(self):
        # 顶部操作栏
        top_frame = tk.Frame(self.window)
        top_frame.pack(fill=tk.X, padx=5, pady=5)

        btn_select = tk.Button(top_frame, text="1. 选择参考图文件夹", command=self.select_folder)
        btn_select.pack(side=tk.LEFT, padx=5)

        # 匹配按钮
        self.btn_match = tk.Button(top_frame, text="2. 匹配文件名 (关联)", bg="#ffcccc", command=self.match_filename)
        self.btn_match.pack(side=tk.LEFT, padx=20)

        # 状态
        self.status_label = tk.Label(top_frame, text="未加载")
        self.status_label.pack(side=tk.RIGHT)

        # 图片显示区域
        self.canvas = tk.Canvas(self.window, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 底部导航
        btm_frame = tk.Frame(self.window)
        btm_frame.pack(fill=tk.X, pady=5)

        tk.Button(btm_frame, text="< 上一张", command=self.prev_image).pack(side=tk.LEFT, padx=10)
        tk.Button(btm_frame, text="下一张 >", command=self.next_image).pack(side=tk.RIGHT, padx=10)

    def select_folder(self):
        path = filedialog.askdirectory(title="选择参考图片文件夹")
        if not path: return
        self.folder_path = path

        # 获取图片
        exts = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
        self.image_files = []
        for ext in exts:
            self.image_files.extend(glob.glob(os.path.join(path, ext)))

        if self.image_files:
            self.current_index = 0
            self.show_image()
            self.status_label.config(text=f"已加载 {len(self.image_files)} 张")
        else:
            self.status_label.config(text="无图片")

    def show_image(self):
        if not self.image_files: return

        path = self.image_files[self.current_index]
        self.original_image = Image.open(path)

        # 简单缩放适应窗口显示（不做复杂交互，只做展示）
        w, h = self.original_image.size
        ratio = min(600 / w, 600 / h)
        new_w, new_h = int(w * ratio), int(h * ratio)

        img_resized = self.original_image.resize((new_w, new_h), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(img_resized)

        self.canvas.delete("all")
        # 居中显示
        cw = self.canvas.winfo_width() or 600
        ch = self.canvas.winfo_height() or 600
        self.canvas.create_image(cw // 2, ch // 2, image=self.tk_image)

        self.window.title(f"参考图: {os.path.basename(path)}")

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.show_image()

    def match_filename(self):
        """将当前参考图重命名为：主窗口文件名 + _对比"""
        if not self.image_files: return
        if not self.main_app.image_files:
            messagebox.showwarning("错误", "主窗口没有图片，无法匹配")
            return

        # 1. 获取主窗口当前文件名（不含后缀）
        main_path = self.main_app.image_files[self.main_app.current_index]
        main_name = os.path.splitext(os.path.basename(main_path))[0]

        # 2. 获取当前参考图信息
        current_ref_path = self.image_files[self.current_index]
        dir_name = os.path.dirname(current_ref_path)
        old_ext = os.path.splitext(current_ref_path)[1]

        # 3. 构建新名称
        new_name = f"{main_name}_对比{old_ext}"
        new_path = os.path.join(dir_name, new_name)

        # 4. 重命名文件
        try:
            os.rename(current_ref_path, new_path)
            # 更新列表中的路径
            self.image_files[self.current_index] = new_path
            self.show_image()  # 刷新标题
            messagebox.showinfo("成功", f"文件已重命名为:\n{new_name}")
        except Exception as e:
            messagebox.showerror("错误", f"重命名失败: {e}")

    def sync_crop_and_save(self, center_x, center_y, crop_index):
        """接收主窗口的中心点，进行700x700裁剪并保存"""
        if not self.original_image: return

        # 1. 设置保存路径: cutoff/对比参考
        save_dir = os.path.join(self.main_app.cutoff_folder, "对比参考")
        os.makedirs(save_dir, exist_ok=True)

        # 2. 计算裁剪区域 (700x700，基于传入的中心点)
        crop_w, crop_h = 700, 700
        x1 = int(center_x - crop_w / 2)
        y1 = int(center_y - crop_h / 2)
        x2 = int(center_x + crop_w / 2)
        y2 = int(center_y + crop_h / 2)

        # 3. 裁剪 (PIL允许坐标越界，会自动处理或需要我们手动补全？PIL crop越界会切掉，所以最好不做padding除非有需求，这里按直接裁处理)
        # 为了防止越界导致图片变小，通常建议先扩充边缘，或者接受变小。这里简单处理：直接Crop
        cropped = self.original_image.crop((x1, y1, x2, y2))

        # 4. 生成文件名
        ref_path = self.image_files[self.current_index]
        file_name, file_ext = os.path.splitext(os.path.basename(ref_path))
        # 保持与主窗口类似的命名逻辑
        new_file_name = f"{file_name}_cut_{crop_index}{file_ext}"
        save_path = os.path.join(save_dir, new_file_name)

        cropped.save(save_path)
        print(f"参考图已裁剪并保存至: {save_path}")

    def on_close(self):
        # 只是隐藏而不是销毁，或者销毁后主程序处理
        self.window.destroy()
        self.main_app.ref_window = None


class ImageCutter:
    def __init__(self, root):
        self.root = root
        self.root.title("主裁剪窗口 (640x640)")

        # === 变量初始化 ===
        self.folder_path = ""
        self.image_files = []
        self.current_index = 0
        self.selected_region = None  # (x1, y1, x2, y2) 原图坐标
        self.original_image = None
        self.tk_image = None
        self.scale_ratio = 1.0
        self.zoom_factor = 1.0
        self.crop_count = 0
        self.cropped_regions = []

        # 拖拽相关
        self.center_x = 0
        self.center_y = 0
        self.is_dragging_existing = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # 参考窗口实例
        self.ref_window = None

        # 固定裁剪尺寸（主窗口）
        self.fixed_crop_w = 640
        self.fixed_crop_h = 640

        self.create_widgets()
        self.select_folder()

        # 绑定事件
        self.root.bind("<Configure>", self.on_window_resize)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        # 右键平移
        self.canvas.bind("<ButtonPress-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_move)

        # 启动时尝试打开参考窗口
        self.open_ref_window()

    def open_ref_window(self):
        if self.ref_window is None:
            self.ref_window = ReferenceWindow(self, self.root)

    def create_widgets(self):
        # 顶部
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Button(top_frame, text="选择文件夹", command=self.select_folder).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="重开参考窗口", command=self.open_ref_window).pack(side=tk.LEFT, padx=5)
        self.status_label = tk.Label(top_frame, text="请选择文件夹")
        self.status_label.pack(side=tk.LEFT, padx=20)

        # 中间画布
        self.image_frame = tk.Frame(self.root)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.image_frame, cursor="cross", bg="#e0e0e0")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 底部
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        self.confirm_btn = tk.Button(bottom_frame, text="裁剪当前区域 (Enter)", command=self.confirm_crop,
                                     state=tk.DISABLED, bg="#ccffcc")
        self.confirm_btn.pack(side=tk.LEFT, padx=20)
        self.root.bind("<Return>", lambda event: self.confirm_crop())  # 绑定回车键

        # 预览图
        self.preview_label = tk.Label(bottom_frame, text="预览")
        self.preview_label.pack(side=tk.LEFT, padx=10)

        # 导航
        self.next_btn = tk.Button(bottom_frame, text="下一张 >", command=self.next_image, state=tk.DISABLED)
        self.next_btn.pack(side=tk.RIGHT, padx=10)
        self.prev_btn = tk.Button(bottom_frame, text="< 上一张", command=self.prev_image, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.RIGHT, padx=10)

        self.crop_count_label = tk.Label(bottom_frame, text="裁剪: 0")
        self.crop_count_label.pack(side=tk.LEFT, padx=20)

    def select_folder(self):
        self.folder_path = filedialog.askdirectory(title="选择主图片文件夹")
        if not self.folder_path: return

        exts = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
        self.image_files = []
        for ext in exts:
            self.image_files.extend(glob.glob(os.path.join(self.folder_path, ext)))

        if not self.image_files:
            messagebox.showinfo("提示", "无图片")
            return

        # 创建cutoff文件夹
        self.cutoff_folder = os.path.join(self.folder_path, "cutoff")
        os.makedirs(self.cutoff_folder, exist_ok=True)

        self.current_index = 0
        self.show_current_image()

        self.confirm_btn.config(state=tk.NORMAL)
        self.prev_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.NORMAL)

    def resize_image(self, image):
        # 简单的自适应逻辑
        w = self.root.winfo_width() - 40
        h = self.root.winfo_height() - 150
        if w <= 0: w, h = 800, 600

        base_ratio = min(w / image.width, h / image.height)
        self.scale_ratio = base_ratio * self.zoom_factor

        new_w = int(image.width * self.scale_ratio)
        new_h = int(image.height * self.scale_ratio)
        return ImageTk.PhotoImage(image.resize((new_w, new_h), Image.LANCZOS))

    def show_current_image(self):
        if not self.image_files: return

        path = self.image_files[self.current_index]
        self.original_image = Image.open(path)
        self.tk_image = self.resize_image(self.original_image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)

        # 绘制历史裁剪框
        self.draw_history_marks()

        self.selected_region = None
        self.preview_label.config(image="")
        self.status_label.config(text=f"{os.path.basename(path)} ({self.current_index + 1}/{len(self.image_files)})")
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def draw_history_marks(self):
        """绘制已裁剪区域的绿色半透明框"""
        for (x1, y1, x2, y2, idx) in self.cropped_regions:
            s = self.scale_ratio
            self.canvas.create_rectangle(x1 * s, y1 * s, x2 * s, y2 * s, outline="#00ff00", width=2)
            self.canvas.create_text((x1 + x2) / 2 * s, (y1 + y2) / 2 * s, text=str(idx), fill="#00ff00",
                                    font=("Arial", 14, "bold"))

    # === 鼠标操作核心 (拖动框) ===
    def on_mouse_down(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # 检查是否点中现有的红框 (用于拖动微调)
        if self.selected_region:
            s = self.scale_ratio
            sx1, sy1, sx2, sy2 = [v * s for v in self.selected_region]
            if sx1 < x < sx2 and sy1 < y < sy2:
                self.is_dragging_existing = True
                # 记录点击位置相对于中心的偏移
                cx = (sx1 + sx2) / 2
                cy = (sy1 + sy2) / 2
                self.drag_offset_x = x - cx
                self.drag_offset_y = y - cy
                return

        # 新建框
        self.is_dragging_existing = False
        self.update_box_center(x, y)

    def on_mouse_drag(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if self.is_dragging_existing:
            # 修正中心点
            new_cx = x - self.drag_offset_x
            new_cy = y - self.drag_offset_y
            self.update_box_center(new_cx, new_cy)
        else:
            self.update_box_center(x, y)

        self.show_preview()

    def on_mouse_up(self, event):
        # 边界检查防止移出图片
        if not self.selected_region: return
        x1, y1, x2, y2 = self.selected_region
        w, h = self.original_image.size

        # 简单的平移回正逻辑
        dx, dy = 0, 0
        if x1 < 0: dx = -x1
        if x2 > w: dx = w - x2
        if y1 < 0: dy = -y1
        if y2 > h: dy = h - y2

        if dx != 0 or dy != 0:
            self.selected_region = (x1 + dx, y1 + dy, x2 + dx, y2 + dy)
            # 重新绘制红框
            cx = (x1 + dx + x2 + dx) / 2 * self.scale_ratio
            cy = (y1 + dy + y2 + dy) / 2 * self.scale_ratio
            self.draw_red_box(cx, cy)

        self.show_preview()

    def update_box_center(self, cx_canvas, cy_canvas):
        """根据画布上的中心点更新红框和数据"""
        half_w = (self.fixed_crop_w * self.scale_ratio) / 2
        half_h = (self.fixed_crop_h * self.scale_ratio) / 2

        self.draw_red_box(cx_canvas, cy_canvas)

        # 转换回原图坐标
        raw_cx = cx_canvas / self.scale_ratio
        raw_cy = cy_canvas / self.scale_ratio

        self.selected_region = (
            int(raw_cx - self.fixed_crop_w / 2),
            int(raw_cy - self.fixed_crop_h / 2),
            int(raw_cx + self.fixed_crop_w / 2),
            int(raw_cy + self.fixed_crop_h / 2)
        )

    def draw_red_box(self, cx, cy):
        half_w = (self.fixed_crop_w * self.scale_ratio) / 2
        half_h = (self.fixed_crop_h * self.scale_ratio) / 2
        self.canvas.delete("selection_rect")
        self.canvas.create_rectangle(
            cx - half_w, cy - half_h, cx + half_w, cy + half_h,
            outline="red", dash=(5, 2), width=2, tags="selection_rect"
        )

    def show_preview(self):
        if not self.selected_region: return
        cropped = self.original_image.crop(self.selected_region)
        cropped.thumbnail((100, 100))
        self.preview_image = ImageTk.PhotoImage(cropped)
        self.preview_label.config(image=self.preview_image)

    # === 裁剪与保存 ===
    def confirm_crop(self):
        if not self.selected_region: return

        self.crop_count += 1

        # 1. 保存主图裁剪
        save_path = os.path.join(self.cutoff_folder, self.get_crop_filename(self.crop_count))
        self.original_image.crop(self.selected_region).save(save_path)

        # 记录历史
        self.cropped_regions.append((*self.selected_region, self.crop_count))

        # 2. **关键：触发参考窗口的联动裁剪**
        if self.ref_window:
            # 计算中心点传给参考窗口
            x1, y1, x2, y2 = self.selected_region
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            self.ref_window.sync_crop_and_save(center_x, center_y, self.crop_count)

        # 界面反馈
        self.canvas.delete("selection_rect")
        self.selected_region = None
        self.preview_label.config(image="")
        self.crop_count_label.config(text=f"裁剪: {self.crop_count}")
        self.show_current_image()  # 刷新显示绿色框

    def get_crop_filename(self, idx):
        base, ext = os.path.splitext(os.path.basename(self.image_files[self.current_index]))
        return f"{base}_cut_{idx}{ext}"

    # === 导航 ===
    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.reset_per_image_state()
            self.show_current_image()

    def next_image(self):
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.reset_per_image_state()
            self.show_current_image()

    def reset_per_image_state(self):
        self.crop_count = 0
        self.cropped_regions = []
        self.zoom_factor = 1.0  # 也可以选择不重置

    # === 辅助 ===
    def on_window_resize(self, event):
        if event.widget == self.root and self.original_image:
            self.show_current_image()

    def on_mouse_wheel(self, event):
        if event.delta > 0:
            self.zoom_factor += 0.1
        else:
            self.zoom_factor = max(0.1, self.zoom_factor - 0.1)
        self.show_current_image()

    def on_pan_start(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def on_pan_move(self, event):  # 未实现完全平移，仅预留
        pass


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x800")
    app = ImageCutter(root)
    root.mainloop()