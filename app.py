import customtkinter as ctk
from tkinter import filedialog, messagebox, Canvas
import os
import threading
from PIL import Image, ImageTk
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import mm

# ==========================================
# บังคับใช้ธีม Light (พื้นขาว ตัวหนังสือดำ)
# ==========================================
ctk.set_appearance_mode("Light") 
ctk.set_default_color_theme("blue")

PAGE_SIZES_MM = {
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
    "A5": (148.0, 210.0),
    "A6": (105.0, 148.0),
    "B4": (250.0, 353.0),
    "B5": (176.0, 250.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}

def get_image_aspect_ratio(img_path):
    try:
        with Image.open(img_path) as img:
            return img.height / img.width
    except Exception:
        return 1.0

class ImageGroupFrame(ctk.CTkFrame):
    def __init__(self, master, group_index, update_preview_callback, **kwargs):
        super().__init__(master, **kwargs)
        self.group_index = group_index
        self.folder_path = None
        self.image_files = []
        self.update_preview_callback = update_preview_callback

        self.lbl_title = ctk.CTkLabel(self, text=f"📂 กลุ่มที่ {self.group_index}", font=("Helvetica", 14, "bold"))
        self.lbl_title.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.btn_browse = ctk.CTkButton(self, text="เลือกโฟลเดอร์", command=self.browse_folder, width=100)
        self.btn_browse.grid(row=0, column=1, padx=10, pady=5)

        self.lbl_path = ctk.CTkLabel(self, text="ยังไม่ได้เลือก", text_color="gray")
        self.lbl_path.grid(row=0, column=2, padx=10, pady=5, sticky="w")

        self.lbl_x = ctk.CTkLabel(self, text="X(mm):")
        self.lbl_x.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.entry_x = ctk.CTkEntry(self, width=60)
        self.entry_x.insert(0, str(10 + (group_index-1)*50))
        self.entry_x.bind("<KeyRelease>", lambda e: self.update_preview_callback())
        self.entry_x.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.lbl_y = ctk.CTkLabel(self, text="Y(mm):")
        self.lbl_y.grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.entry_y = ctk.CTkEntry(self, width=60)
        self.entry_y.insert(0, "10")
        self.entry_y.bind("<KeyRelease>", lambda e: self.update_preview_callback())
        self.entry_y.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        self.lbl_w = ctk.CTkLabel(self, text="กว้าง(mm):")
        self.lbl_w.grid(row=1, column=4, padx=5, pady=5, sticky="e")
        self.entry_w = ctk.CTkEntry(self, width=60)
        self.entry_w.insert(0, "40")
        self.entry_w.bind("<KeyRelease>", lambda e: self.update_preview_callback())
        self.entry_w.grid(row=1, column=5, padx=5, pady=5, sticky="w")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path = folder
            valid_exts = ('.png', '.jpg', '.jpeg')
            files = [f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
            files.sort()
            self.image_files = [os.path.join(folder, f) for f in files]
            self.lbl_path.configure(text=f"พบ {len(self.image_files)} รูป", text_color="green")
            self.update_preview_callback()

    def get_config(self):
        try:
            return {
                "folder_path": self.folder_path,
                "images": self.image_files,
                "x_mm": float(self.entry_x.get()),
                "y_mm": float(self.entry_y.get()),
                "width_mm": float(self.entry_w.get())
            }
        except ValueError:
            return None


class PDFGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Image Layout to PDF Generator")
        
        w = self.winfo_screenwidth()
        h = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+0+0")
        try:
            self.state('zoomed') 
        except:
            pass 

        self.groups = []
        self.group_counter = 1
        self.preview_images = []

        self.lbl_header = ctk.CTkLabel(self, text="🔲 จัดเลย์เอาต์รูปภาพลง PDF", font=("Helvetica", 24, "bold"))
        self.lbl_header.pack(pady=10)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        self.left_panel = ctk.CTkFrame(self.main_frame, width=650)
        self.left_panel.pack(side="left", fill="y", padx=10)

        self.right_panel = ctk.CTkFrame(self.main_frame)
        self.right_panel.pack(side="right", fill="both", expand=True, padx=10)

        self.frame_page = ctk.CTkFrame(self.left_panel)
        self.frame_page.pack(pady=10, padx=10, fill="x")
        
        self.lbl_page_title = ctk.CTkLabel(self.frame_page, text="📄 ตั้งค่าหน้ากระดาษ", font=("Helvetica", 16, "bold"))
        self.lbl_page_title.grid(row=0, column=0, columnspan=4, pady=5, padx=10, sticky="w")

        self.lbl_size = ctk.CTkLabel(self.frame_page, text="ขนาด:")
        self.lbl_size.grid(row=1, column=0, padx=10, pady=5, sticky="e")
        
        self.page_size_var = ctk.StringVar(value="A4")
        self.opt_size = ctk.CTkOptionMenu(
            self.frame_page, 
            values=list(PAGE_SIZES_MM.keys()) + ["กำหนดเอง (Custom)"],
            variable=self.page_size_var,
            command=self.on_page_setting_change
        )
        self.opt_size.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.lbl_orient = ctk.CTkLabel(self.frame_page, text="แนว:")
        self.lbl_orient.grid(row=1, column=2, padx=10, pady=5, sticky="e")
        
        self.orient_var = ctk.StringVar(value="Portrait (แนวตั้ง)")
        self.opt_orient = ctk.CTkOptionMenu(
            self.frame_page, 
            values=["Portrait (แนวตั้ง)", "Landscape (แนวนอน)"],
            variable=self.orient_var,
            command=self.on_page_setting_change
        )
        self.opt_orient.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        self.frame_custom = ctk.CTkFrame(self.frame_page, fg_color="transparent")
        self.frame_custom.grid(row=2, column=0, columnspan=4, pady=0, sticky="w")
        
        self.lbl_custom_w = ctk.CTkLabel(self.frame_custom, text="กว้าง(mm):")
        self.entry_custom_w = ctk.CTkEntry(self.frame_custom, width=70)
        self.entry_custom_w.insert(0, "330") 
        self.entry_custom_w.bind("<KeyRelease>", lambda e: self.update_preview())

        self.lbl_custom_h = ctk.CTkLabel(self.frame_custom, text="สูง(mm):")
        self.entry_custom_h = ctk.CTkEntry(self.frame_custom, width=70)
        self.entry_custom_h.insert(0, "480") 
        self.entry_custom_h.bind("<KeyRelease>", lambda e: self.update_preview())

        self.scrollable_frame = ctk.CTkScrollableFrame(self.left_panel, width=600)
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.btn_add_group = ctk.CTkButton(self.left_panel, text="➕ เพิ่มกลุ่มรูปภาพ", command=self.add_group)
        self.btn_add_group.pack(pady=5)

        self.lbl_status = ctk.CTkLabel(self.left_panel, text="พร้อมทำงาน", font=("Helvetica", 14), text_color="gray")
        self.lbl_status.pack(pady=(15, 0))

        self.progress = ctk.CTkProgressBar(self.left_panel, width=400)
        self.progress.pack(pady=5)
        self.progress.set(0)

        self.btn_generate = ctk.CTkButton(self.left_panel, text="🖨️ สร้างไฟล์ PDF", fg_color="green", hover_color="darkgreen", command=self.start_generate_thread, font=("Helvetica", 16, "bold"), height=40)
        self.btn_generate.pack(pady=10)

        # --- ส่วนขวา: จอพรีวิว ---
        self.lbl_preview = ctk.CTkLabel(self.right_panel, text="👁️ จำลองหน้ากระดาษ (Preview)", font=("Helvetica", 16, "bold"))
        self.lbl_preview.pack(pady=10)
        
        # เปลี่ยนพื้นหลัง Canvas ให้เป็นเทาอ่อน เพื่อเน้นกระดาษขาว
        self.preview_canvas = Canvas(self.right_panel, bg="#ececec", highlightthickness=0)
        self.preview_canvas.pack(pady=10, fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda e: self.update_preview())

        self.on_page_setting_change() 
        self.add_group()

    def get_current_page_size_mm(self):
        size_name = self.page_size_var.get()
        if size_name == "กำหนดเอง (Custom)":
            try:
                w_mm = float(self.entry_custom_w.get())
                h_mm = float(self.entry_custom_h.get())
            except ValueError:
                w_mm, h_mm = 210.0, 297.0 
        else:
            w_mm, h_mm = PAGE_SIZES_MM[size_name]

        if "Landscape" in self.orient_var.get():
            final_w, final_h = max(w_mm, h_mm), min(w_mm, h_mm)
        else:
            final_w, final_h = min(w_mm, h_mm), max(w_mm, h_mm)
            
        return final_w, final_h

    def on_page_setting_change(self, *args):
        if self.page_size_var.get() == "กำหนดเอง (Custom)":
            self.lbl_custom_w.grid(row=0, column=0, padx=10, pady=5)
            self.entry_custom_w.grid(row=0, column=1, padx=5, pady=5)
            self.lbl_custom_h.grid(row=0, column=2, padx=10, pady=5)
            self.entry_custom_h.grid(row=0, column=3, padx=5, pady=5)
        else:
            self.lbl_custom_w.grid_forget()
            self.entry_custom_w.grid_forget()
            self.lbl_custom_h.grid_forget()
            self.entry_custom_h.grid_forget()
            
        self.update_preview()

    def add_group(self):
        new_group = ImageGroupFrame(self.scrollable_frame, self.group_counter, self.update_preview)
        new_group.pack(fill="x", pady=5, padx=5)
        self.groups.append(new_group)
        self.group_counter += 1
        self.update_preview()

    def update_preview(self):
        w_mm, h_mm = self.get_current_page_size_mm()
        if w_mm <= 0 or h_mm <= 0: return

        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()

        if canvas_width <= 1: canvas_width = 500
        if canvas_height <= 1: canvas_height = 600

        safe_w = canvas_width - 40
        safe_h = canvas_height - 40

        scale_x = safe_w / max(1, w_mm)
        scale_y = safe_h / max(1, h_mm)
        scale = min(scale_x, scale_y) 

        paper_w_px = w_mm * scale
        paper_h_px = h_mm * scale

        offset_x = (canvas_width - paper_w_px) / 2
        offset_y = (canvas_height - paper_h_px) / 2

        self.preview_canvas.delete("all")
        self.preview_images.clear() 
        
        self.preview_canvas.create_rectangle(
            offset_x, offset_y, offset_x + paper_w_px, offset_y + paper_h_px, 
            fill="white", outline="#999", width=2
        )
        
        colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c"]

        for idx, group in enumerate(self.groups):
            cfg = group.get_config()
            if cfg:
                color = colors[idx % len(colors)]
                x_mm, y_mm, img_w_mm = cfg["x_mm"], cfg["y_mm"], cfg["width_mm"]
                
                ratio = 1.0
                if cfg["images"]:
                    ratio = get_image_aspect_ratio(cfg["images"][0])
                img_h_mm = img_w_mm * ratio

                x_px = offset_x + (x_mm * scale)
                y_px = offset_y + (y_mm * scale)
                img_w_px = int(max(1, img_w_mm * scale))
                img_h_px = int(max(1, img_h_mm * scale))

                if (x_mm + img_w_mm) <= w_mm * 1.5: 
                    if cfg["images"]:
                        try:
                            first_img_path = cfg["images"][0]
                            img = Image.open(first_img_path)
                            img = img.resize((img_w_px, img_h_px), Image.LANCZOS)
                            tk_img = ImageTk.PhotoImage(img)
                            
                            self.preview_images.append(tk_img)
                            self.preview_canvas.create_image(x_px, y_px, anchor="nw", image=tk_img)
                            
                            self.preview_canvas.create_rectangle(
                                x_px, y_px, x_px + img_w_px, y_px + img_h_px, 
                                outline=color, width=3
                            )
                        except Exception as e:
                            print(f"โหลดภาพพรีวิวไม่สำเร็จ: {e}")
                    else:
                        self.preview_canvas.create_rectangle(
                            x_px, y_px, x_px + img_w_px, y_px + img_h_px, 
                            fill=f"{color}", stipple="gray50", outline=color, width=2
                        )
                        font_size = max(8, int(10 * scale / 2))
                        self.preview_canvas.create_text(
                            x_px + (img_w_px/2), y_px + (img_h_px/2), 
                            text=f"กลุ่ม {group.group_index}", fill="black", font=("Helvetica", font_size, "bold")
                        )

    def start_generate_thread(self):
        configs = []
        max_pages = 0

        for group in self.groups:
            cfg = group.get_config()
            if cfg is None:
                messagebox.showerror("ข้อผิดพลาด", f"กรุณากรอกตัวเลขพิกัดให้ถูกต้องในกลุ่มที่ {group.group_index}")
                return
            if not cfg["images"]:
                messagebox.showwarning("แจ้งเตือน", f"กลุ่มที่ {group.group_index} ยังไม่ได้เลือกโฟลเดอร์")
                return
            configs.append(cfg)
            if len(cfg["images"]) > max_pages:
                max_pages = len(cfg["images"])

        if max_pages == 0: return

        save_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not save_path: return

        page_w_mm, page_h_mm = self.get_current_page_size_mm()

        self.btn_generate.configure(state="disabled", text="กำลังประมวลผล...")
        self.progress.set(0)
        self.lbl_status.configure(text="เตรียมการสร้างไฟล์...", text_color="black")

        threading.Thread(target=self.generate_pdf_worker, args=(configs, max_pages, save_path, page_w_mm, page_h_mm), daemon=True).start()

    def generate_pdf_worker(self, configs, max_pages, save_path, page_w_mm, page_h_mm):
        try:
            page_w_pt = page_w_mm * mm
            page_h_pt = page_h_mm * mm
            
            c = pdf_canvas.Canvas(save_path, pagesize=(page_w_pt, page_h_pt))

            for page_idx in range(max_pages):
                if page_idx > 0:
                    c.showPage()

                for cfg in configs:
                    if page_idx < len(cfg["images"]):
                        img_path = cfg["images"][page_idx]
                        x_pt = cfg["x_mm"] * mm
                        w_pt = cfg["width_mm"] * mm
                        img_ratio = get_image_aspect_ratio(img_path)
                        h_pt = w_pt * img_ratio
                        
                        y_pt = page_h_pt - (cfg["y_mm"] * mm) - h_pt 
                        
                        c.drawImage(img_path, x_pt, y_pt, width=w_pt, height=h_pt)

                pct = (page_idx + 1) / max_pages
                status_text = f"กำลังสร้างหน้าที่ {page_idx + 1} จาก {max_pages}"
                self.after(0, self.update_ui, pct, status_text)

            c.save()
            self.after(0, self.finish_generation, max_pages, save_path)

        except Exception as e:
            self.after(0, self.show_error, str(e))

    def update_ui(self, pct, status_text):
        self.progress.set(pct)
        self.lbl_status.configure(text=status_text)

    def finish_generation(self, max_pages, save_path):
        self.progress.set(1.0)
        self.lbl_status.configure(text="✅ เสร็จสิ้น!", text_color="green")
        messagebox.showinfo("สำเร็จ", f"สร้าง PDF จำนวน {max_pages} หน้า สำเร็จ!\nไฟล์ถูกบันทึกไว้ที่:\n{save_path}")
        self.btn_generate.configure(state="normal", text="🖨️ สร้างไฟล์ PDF")

    def show_error(self, error_msg):
        self.lbl_status.configure(text="❌ เกิดข้อผิดพลาด", text_color="red")
        messagebox.showerror("Error", f"เกิดข้อผิดพลาดในการสร้าง PDF:\n{error_msg}")
        self.btn_generate.configure(state="normal", text="🖨️ สร้างไฟล์ PDF")

if __name__ == "__main__":
    app = PDFGeneratorApp()
    app.mainloop()