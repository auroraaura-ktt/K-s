import pathlib
import sys

target = pathlib.Path(r"D:\K's Essential Projects\Profolio - with Apps\mytask\models.py")
data = target.read_text(encoding="utf-8")
out = pathlib.Path(r"D:\K's Essential Projects\Profolio - with Apps\mytask\models_len.txt")
out.write_text("length=%d lines=%d" % (len(data), data.count("\n") + 1), encoding="utf-8")
print(out.read_text(encoding="utf-8"))
