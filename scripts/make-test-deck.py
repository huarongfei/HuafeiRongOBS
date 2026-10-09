
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# 幻灯片 1：标题 + 多级项目符号 + 多色文本
s1 = prs.slides.add_slide(prs.slide_layouts[1])
s1.shapes.title.text = "HuafeiRongOBS 自研 PPT 引擎"
tf = s1.placeholders[1].text_frame
tf.text = "第一级：实时渲染动画"
p = tf.add_paragraph(); p.text = "第二级：多画布不同页"; p.level = 1
p = tf.add_paragraph(); p.text = "第二级：讲者视图备注"; p.level = 2
p = tf.add_paragraph(); p.text = "再次一级：中文排版与字体"; p.level = 3
for para in tf.paragraphs:
    for r in para.runs:
        r.font.size = Pt(24 - para.level * 3)

# 幻灯片 2：色块 + 图片 + 表格
s2 = prs.slides.add_slide(prs.slide_layouts[5])
s2.shapes.title.text = "图形与表格"
box = s2.shapes.add_shape(1, Inches(0.6), Inches(1.6), Inches(3.0), Inches(1.6))  # rectangle
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0x2E, 0x86, 0xDE)
box.text_frame.text = "自研 GPU 渲染"
for r in box.text_frame.paragraphs[0].runs:
    r.font.size = Pt(20); r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

# 生成一张 PNG 作为图片素材
import struct, zlib
def png_solid(w, h, rgb):
    raw = b''.join(b'\x00' + bytes(rgb) * w for _ in range(h))
    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw))
            + chunk(b'IEND', b''))
img_path = os.path.join(os.environ.get('TEMP', '.'), 'hfr_test_img.png')
with open(img_path, 'wb') as f:
    f.write(png_solid(320, 180, (0xE7, 0x4C, 0x3C)))
s2.shapes.add_picture(img_path, Inches(4.2), Inches(1.6), Inches(3.2), Inches(1.8))

rows, cols = 3, 3
tbl = s2.shapes.add_table(rows, cols, Inches(0.6), Inches(4.0), Inches(6.0), Inches(1.8)).table
for r in range(rows):
    for c in range(cols):
        tbl.cell(r, c).text = f"R{r+1}C{c+1}"

# 幻灯片 3：旋转形状 + 渐变填充 + 居中艺术字
from pptx.enum.shapes import MSO_SHAPE
s3 = prs.slides.add_slide(prs.slide_layouts[6])
sh = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.0), Inches(1.0), Inches(4.0), Inches(2.0))
sh.rotation = 15
sh.fill.gradient()
sh.text_frame.text = "渐变 + 旋转"
tb = s3.shapes.add_textbox(Inches(1.0), Inches(4.0), Inches(8.0), Inches(1.2))
tp = tb.text_frame.paragraphs[0]
tp.alignment = PP_ALIGN.CENTER
run = tp.add_run(); run.text = "中文居中标题 ABC 123"; run.font.size = Pt(40); run.font.bold = True

out = r"D:\HuafeirongOBS\tools\test\rich-deck.pptx"
prs.save(out)
print("saved:", out, "slides:", len(prs.slides.__iter__.__self__._sldIdLst))