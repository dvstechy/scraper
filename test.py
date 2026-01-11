#test.py

from paddleocr import PaddleOCR, PPStructure

ocr = PaddleOCR(use_angle_cls=True, lang='en')
table_engine = PPStructure(show_log=True)

print("✅ PaddleOCR + PPStructure loaded successfully")
