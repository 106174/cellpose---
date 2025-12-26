import os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import glob


class ImageCutter:
    def __init__(self, root):
        self.root = root
        self.root.title("图片裁剪工具（带裁剪标注）")

        # 初始化变量
        self.folder_path = ""
        self.image_files = []
        self.current_index = 0
        self.selected_region = None
        self.original_image = None
        self.tk_image = None
        self.cropped_image = None
        self.scale_ratio = 1.0  # 图片缩放比例
        self.zoom_factor = 1.0  # 手动缩放因子
        self.crop_count = 0  # 当前图片的裁剪次数（用于文件名）
        self.cropped_regions = []  # 存储已裁剪的区域（原始坐标）和序号：[(x1,y1,x2,y2, 序号), ...]
        self.is_dragging_existing = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        # 创建界面组件
        self.create_widgets()

        # 让用户选择文件夹
        self.select_folder()

        # 固定裁剪尺寸（原图像素）
        self.fixed_crop_w = 640
        self.fixed_crop_h = 640

        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_resize)
        # 绑定鼠标滚轮缩放
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)  # Windows
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)  # Linux
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)  # Linux

    def create_widgets(self):
        # 创建顶部按钮框架
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=10)

        # 选择文件夹按钮
        self.select_folder_btn = tk.Button(top_frame, text="选择文件夹", command=self.select_folder)
        self.select_folder_btn.pack(side=tk.LEFT, padx=5)

        # 全屏切换按钮
        self.fullscreen_btn = tk.Button(top_frame, text="切换全屏", command=self.toggle_fullscreen)
        self.fullscreen_btn.pack(side=tk.LEFT, padx=5)

        # 缩放控制按钮
        self.zoom_in_btn = tk.Button(top_frame, text="放大", command=lambda: self.zoom(0.1))
        self.zoom_in_btn.pack(side=tk.LEFT, padx=5)

        self.zoom_out_btn = tk.Button(top_frame, text="缩小", command=lambda: self.zoom(-0.1))
        self.zoom_out_btn.pack(side=tk.LEFT, padx=5)

        # 清除标注按钮
        self.clear_marks_btn = tk.Button(top_frame, text="清除所有标注", command=self.clear_crop_marks)
        self.clear_marks_btn.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self.status_label = tk.Label(top_frame, text="请选择包含图片的文件夹")
        self.status_label.pack(side=tk.LEFT, padx=20)

        # 创建图片显示框架（占满大部分窗口）
        self.image_frame = tk.Frame(self.root)
        self.image_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 画布用于显示图片和选择区域（支持滚动）
        self.canvas_frame = tk.Frame(self.image_frame)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        # 滚动条
        self.vscroll = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.hscroll = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.canvas = tk.Canvas(
            self.canvas_frame,
            cursor="cross",
            yscrollcommand=self.vscroll.set,
            xscrollcommand=self.hscroll.set
        )

        self.vscroll.config(command=self.canvas.yview)
        self.hscroll.config(command=self.canvas.xview)

        self.vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        # 鼠标拖动画布
        self.canvas.bind("<ButtonPress-2>", self.on_pan_start)
        self.canvas.bind("<B2-Motion>", self.on_pan_move)

        # 创建底部按钮框架
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=10)

        # 确认按钮（改为"裁剪当前区域"）
        self.confirm_btn = tk.Button(bottom_frame, text="裁剪当前区域", command=self.confirm_crop, state=tk.DISABLED)
        self.confirm_btn.pack(side=tk.LEFT, padx=20)

        # 上一张按钮 (新增)
        self.prev_btn = tk.Button(bottom_frame, text="上一张图片", command=self.prev_image, state=tk.DISABLED)
        self.prev_btn.pack(side=tk.RIGHT, padx=5)  # 放在下一张按钮左边
        # 下一张按钮
        self.next_btn = tk.Button(bottom_frame, text="下一张图片", command=self.next_image, state=tk.DISABLED)
        self.next_btn.pack(side=tk.RIGHT, padx=20)

        # 裁剪预览标签
        self.preview_label = tk.Label(bottom_frame, text="裁剪预览:")
        self.preview_label.pack(side=tk.LEFT, padx=10)

        # 预览区域
        self.preview_frame = tk.Frame(bottom_frame, bd=1, relief=tk.SOLID, width=100, height=100)
        self.preview_frame.pack(side=tk.LEFT, padx=10)
        self.preview_label = tk.Label(self.preview_frame)
        self.preview_label.pack()

        # 裁剪计数标签
        self.crop_count_label = tk.Label(bottom_frame, text="当前图片已裁剪: 0次")
        self.crop_count_label.pack(side=tk.LEFT, padx=20)

        # 全屏相关变量
        self.fullscreen = False
        self.root.bind("<Escape>", self.exit_fullscreen)  # ESC键退出全屏

        # 平移相关变量
        self.pan_start_x = 0
        self.pan_start_y = 0

    def select_folder(self):
        """让用户选择图片所在的文件夹"""
        self.folder_path = filedialog.askdirectory(title="选择图片文件夹")
        if not self.folder_path:
            return

        # 获取文件夹中所有图片文件
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp']
        self.image_files = []
        for ext in image_extensions:
            self.image_files.extend(glob.glob(os.path.join(self.folder_path, ext)))

        if not self.image_files:
            messagebox.showinfo("提示", "所选文件夹中没有图片文件")
            self.status_label.config(text="所选文件夹中没有图片文件")
            return

        # 创建cutoff文件夹（如果不存在）
        self.cutoff_folder = os.path.join(self.folder_path, "cutoff")
        os.makedirs(self.cutoff_folder, exist_ok=True)

        # 重置索引并显示第一张图片
        self.current_index = 0
        self.zoom_factor = 1.0  # 重置缩放因子
        self.crop_count = 0  # 重置裁剪计数
        self.cropped_regions = []  # 重置已裁剪区域记录
        self.show_current_image()

        # 更新状态
        self.status_label.config(text=f"共 {len(self.image_files)} 张图片，当前: {self.current_index + 1}")
        self.confirm_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.NORMAL)

        # 初始最大化窗口
        self.root.state('zoomed')  # Windows系统最大化

        self.prev_btn.config(state=tk.NORMAL)

    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        self.fullscreen_btn.config(text="退出全屏" if self.fullscreen else "切换全屏")
        # 重新调整图片大小以适应新窗口
        if self.original_image:
            self.show_current_image()

    def exit_fullscreen(self, event=None):
        """退出全屏模式"""
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)
        self.fullscreen_btn.config(text="切换全屏")
        if self.original_image:
            self.show_current_image()

    def zoom(self, amount):
        """缩放图片"""
        if not self.original_image:
            return

        # 限制缩放范围（0.1倍到5倍）
        new_zoom = self.zoom_factor + amount
        if 0.1 <= new_zoom <= 5.0:
            self.zoom_factor = new_zoom
            self.show_current_image()

    def on_mouse_wheel(self, event):
        """鼠标滚轮缩放"""
        if event.num == 4 or event.delta > 0:  # 放大
            self.zoom(0.1)
        elif event.num == 5 or event.delta < 0:  # 缩小
            self.zoom(-0.1)

    def on_pan_start(self, event):
        """开始平移图片"""
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.canvas.config(cursor="fleur")

    def on_pan_move(self, event):
        """平移图片"""
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.canvas.xview_scroll(-dx, "units")
        self.canvas.yview_scroll(-dy, "units")
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def on_window_resize(self, event=None):
        """窗口大小变化时重新调整图片显示"""
        # 避免窗口初始化时的无效调用
        if event and (event.widget != self.root or not self.original_image):
            return
        self.show_current_image()

    def show_current_image(self):
        """显示当前索引的图片，同时绘制已裁剪区域标注"""
        if self.current_index >= len(self.image_files):
            messagebox.showinfo("完成", "所有图片处理完毕")
            self.root.quit()
            return

        # 打开图片
        file_path = self.image_files[self.current_index]
        self.original_image = Image.open(file_path)

        # 调整图片大小（结合窗口自适应和手动缩放）
        self.tk_image = self.resize_image(self.original_image)

        # 在画布上显示图片（先清空所有内容）
        self.canvas.delete("all")
        self.canvas.image = self.tk_image  # 保持引用，防止被垃圾回收
        self.canvas.create_image(0, 0, image=self.tk_image, anchor=tk.NW)

        # 绘制已裁剪区域的标注（半透明绿色矩形+序号）
        self.draw_cropped_marks()

        # 设置画布滚动区域
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

        # 重置选择区域
        self.selected_region = None
        self.preview_label.config(image="")

        # 更新状态
        file_name = os.path.basename(file_path)
        self.status_label.config(
            text=f"图片 {self.current_index + 1}/{len(self.image_files)}: {file_name} "
                 f"| 缩放: {self.zoom_factor:.1f}x"
        )

        # 更新裁剪计数显示
        self.crop_count_label.config(text=f"当前图片已裁剪: {self.crop_count}次")

        # 如果是第一张，禁用“上一张”按钮
        self.prev_btn.config(state=tk.NORMAL if self.current_index > 0 else tk.DISABLED)
        # 如果是最后一张，禁用“下一张”按钮
        self.next_btn.config(state=tk.NORMAL if self.current_index < len(self.image_files) - 1 else tk.DISABLED)
        
    def resize_image(self, image):
        """调整图片大小，允许放大到全屏"""
        # 获取窗口可用空间
        window_width = self.root.winfo_width() - 40  # 减去边距
        window_height = self.root.winfo_height() - 150  # 减去顶部和底部组件高度

        # 确保窗口尺寸有效
        if window_width <= 0 or window_height <= 0:
            window_width = 800
            window_height = 600

        # 计算基础缩放比例（适应窗口）
        base_width_ratio = window_width / image.width
        base_height_ratio = window_height / image.height
        base_ratio = min(base_width_ratio, base_height_ratio)

        # 结合手动缩放因子（允许放大）
        self.scale_ratio = base_ratio * self.zoom_factor

        new_width = int(image.width * self.scale_ratio)
        new_height = int(image.height * self.scale_ratio)

        # 调整大小并转换为Tkinter可用格式
        resized_image = image.resize((new_width, new_height), Image.LANCZOS)
        return ImageTk.PhotoImage(resized_image)

    def draw_cropped_marks(self):
        """绘制已裁剪区域标注：半透明绿色矩形 + 白色序号文字"""
        if not self.cropped_regions:
            return

        for (x1, y1, x2, y2, crop_idx) in self.cropped_regions:
            # 将原图坐标转换成当前显示图像坐标（考虑缩放：窗口缩放 × 用户缩放）
            scale = self.scale_ratio * self.zoom_factor

            draw_x1 = x1 * scale
            draw_y1 = y1 * scale
            draw_x2 = x2 * scale
            draw_y2 = y2 * scale

            # 绘制半透明绿色矩形（用 stipple 模拟半透明）
            self.canvas.create_rectangle(
                draw_x1, draw_y1, draw_x2, draw_y2,
                fill="#00ff00",
                stipple="gray50",
                outline="#009900",
                width=2,
                tags="crop_mark"
            )

            # 绘制序号（居中显示）
            center_x = (draw_x1 + draw_x2) / 2
            center_y = (draw_y1 + draw_y2) / 2

            self.canvas.create_text(
                center_x, center_y,
                text=str(crop_idx),
                fill="white",
                font=("Arial", 14, "bold"),
                tags="crop_mark"
            )

    def clear_crop_marks(self):
        """清除当前图片上所有裁剪标注（不删除已裁剪文件）"""
        self.canvas.delete("crop_mark")
        self.cropped_regions = []  # 清空记录
        messagebox.showinfo("提示", "所有裁剪标注已清除")

    # def on_mouse_down(self, event):
    #     """鼠标按下事件：记录选择区域的起点"""
    #     # 考虑滚动偏移
    #     x = self.canvas.canvasx(event.x)
    #     y = self.canvas.canvasy(event.y)
    #     self.start_x = x
    #     self.start_y = y
    #     self.canvas.delete("selection_rect")

    def on_mouse_down(self, event):
        """鼠标按下：判断是移动现有的框，还是开始新的选择"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        # 检查是否点在了已有的红框范围内
        if self.selected_region:
            # 将原始坐标转为当前画布坐标
            s = self.scale_ratio
            x1, y1, x2, y2 = [coord * s for coord in self.selected_region]

            if x1 <= x <= x2 and y1 <= y <= y2:
                # 激活拖拽模式：记录鼠标点击位置与框中心的偏移量
                self.is_dragging_existing = True
                self.drag_offset_x = x - (x1 + x2) / 2
                self.drag_offset_y = y - (y1 + y2) / 2
                return

        # 如果没点中旧框，则视为重新定位
        self.is_dragging_existing = False
        self.center_x = x
        self.center_y = y
        self.update_selection_from_mouse(x, y)

    def on_mouse_drag(self, event):
        """鼠标拖动：移动框或更新位置"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)

        if hasattr(self, 'is_dragging_existing') and self.is_dragging_existing:
            # 移动现有框：根据偏移量计算新的中心点
            new_cx = x - self.drag_offset_x
            new_cy = y - self.drag_offset_y
            self.update_selection_from_mouse(new_cx, new_cy)
        else:
            # 新建/重置框
            self.update_selection_from_mouse(x, y)

        # 拖动时实时显示预览（可选，增强交互感）
        self.show_preview()

    def update_selection_from_mouse(self, cx, cy):
        """根据中心点 cx, cy 重新计算区域并绘制红框"""
        self.center_x, self.center_y = cx, cy

        half_w = (self.fixed_crop_w * self.scale_ratio) / 2
        half_h = (self.fixed_crop_h * self.scale_ratio) / 2

        x1, y1 = cx - half_w, cy - half_h
        x2, y2 = cx + half_w, cy + half_h

        # 更新画布上的红框
        self.canvas.delete("selection_rect")
        self.canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="red", dash=(5, 2), width=3, tags="selection_rect"
        )

        # 同步转换回原图坐标，供裁剪使用
        self.selected_region = (
            int((cx - self.fixed_crop_w / 2)),
            int((cy - self.fixed_crop_h / 2)),
            int((cx + self.fixed_crop_w / 2)),
            int((cy + self.fixed_crop_h / 2))
        )

    def on_mouse_up(self, event):
        if not self.selected_region: return

        x1, y1, x2, y2 = self.selected_region
        # 越界修正逻辑
        img_w, img_h = self.original_image.size

        shift_x = 0
        if x1 < 0:
            shift_x = -x1
        elif x2 > img_w:
            shift_x = img_w - x2

        shift_y = 0
        if y1 < 0:
            shift_y = -y1
        elif y2 > img_h:
            shift_y = img_h - y2

        # 应用修正
        self.selected_region = (x1 + shift_x, y1 + shift_y, x2 + shift_x, y2 + shift_y)
        self.show_current_image_with_rect()  # 重新刷新一下位置
        self.show_preview()

    def show_preview(self):
        """显示裁剪区域的预览"""
        if not self.selected_region or not self.original_image:
            return

        # 裁剪图片
        cropped = self.original_image.crop(self.selected_region)

        # 调整预览大小
        preview_size = (100, 100)
        cropped.thumbnail(preview_size, Image.LANCZOS)

        # 显示预览
        self.preview_image = ImageTk.PhotoImage(cropped)
        self.preview_label.config(image=self.preview_image)

    def confirm_crop(self):
        """裁剪当前区域并保存，同时记录区域并绘制标注"""
        if not self.selected_region:
            messagebox.showwarning("警告", "请先选择裁剪区域")
            return

        # 增加裁剪计数
        self.crop_count += 1
        crop_idx = self.crop_count

        # 记录已裁剪区域（原始坐标+序号）
        x1, y1, x2, y2 = self.selected_region
        self.cropped_regions.append((x1, y1, x2, y2, crop_idx))

        # 裁剪图片
        self.cropped_image = self.original_image.crop(self.selected_region)

        # 生成保存路径（包含裁剪次数）
        original_path = self.image_files[self.current_index]
        file_name, file_ext = os.path.splitext(os.path.basename(original_path))
        new_file_name = f"{file_name}_cut_{crop_idx}{file_ext}"
        save_path = os.path.join(self.cutoff_folder, new_file_name)

        # 保存图片
        self.cropped_image.save(save_path)

        # 清除当前选择区域，准备下一次裁剪
        self.selected_region = None
        self.canvas.delete("selection_rect")
        self.preview_label.config(image="")

        # 更新裁剪计数显示
        self.crop_count_label.config(text=f"当前图片已裁剪: {self.crop_count}次")

        # 重新绘制图片和标注（让新标注生效）
        self.show_current_image()

    def prev_image(self):
        """切换到上一张图片"""
        if self.current_index > 0:
            self.current_index -= 1
            # 切换图片时重置当前图片的临时状态
            self.crop_count = 0
            self.cropped_regions = []
            # 注意：这里不一定要重置 zoom_factor，保持缩放可以方便连续操作
            self.show_current_image()
        else:
            messagebox.showinfo("提示", "已经是第一张图片了")

    def next_image(self):
        """切换到下一张图片"""
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.crop_count = 0
            self.cropped_regions = []
            self.show_current_image()
        else:
            messagebox.showinfo("完成", "已经是最后一张图片了")



if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCutter(root)
    root.mainloop()