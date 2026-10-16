"""盘点调查数据规模：直接读取压缩包内 Stata .dta 文件头（不解压）。

输出每个表的：变量数（nvar）、观测数（nobs）、文件大小 —— 用于评估
"源数据规模 vs 当前已用字段"的差距，规划建模数据池。

支持格式：Stata 117/118/119（"<stata_dta>" 头）。
.rar / .7z 内文件不在本脚本范围（需外部解压工具）。

用法：
    python scripts/inspect_datasets.py
"""

import re
import struct
import sys
import zipfile
from pathlib import Path

DATASET_ROOT = Path(__file__).resolve().parents[1] / "data" / "数据集"
DATASET_DIRS = [
    DATASET_ROOT / "CFPS",
    DATASET_ROOT / "中国家庭金融调查数据库（CHFS）_20260807024654.zip",
    DATASET_ROOT / "中国小微企业调查数据库（CMES）_20260807025103.zip",
]

YEAR_RE = re.compile(r"(CFPS|chfs|CHFS|cmes|CMES)[-_]?(\d{4})")


RE_RELEASE = re.compile(rb"<release>(\d+)</release>")
RE_K = re.compile(rb"<K>(.*?)</K>", re.S)  # 变量数（二进制整数，2/4 字节）
RE_N = re.compile(rb"<N>(.*?)</N>", re.S)  # 观测数（二进制整数，4/8 字节）


def _to_int(raw: bytes) -> int:
    if len(raw) == 2:
        return struct.unpack("<H", raw)[0]
    if len(raw) == 4:
        return struct.unpack("<I", raw)[0]
    return struct.unpack("<Q", raw)[0]


def dta_meta(buf: bytes):
    """解析 Stata dta 文件头 → (release, nvar, nobs)

    Stata dta（117+）header 为标签格式：
      release/byteorder 为 ASCII 文本，nvar/nobs 存于 <K>/<N> 的**二进制**字段。
    """
    if not buf.startswith(b"<stata_dta>"):
        return None
    m_rel, m_k, m_n = RE_RELEASE.search(buf), RE_K.search(buf), RE_N.search(buf)
    if not (m_rel and m_k and m_n):
        return None
    return int(m_rel.group(1)), _to_int(m_k.group(1)), _to_int(m_n.group(1))


def scan_zip(zpath: Path, label: str) -> None:
    try:
        zf = zipfile.ZipFile(zpath)
    except zipfile.BadZipFile:
        print(f"[skip] {zpath.name}（非 zip 格式）")
        return
    rows = []
    with zf:
        for info in zf.infolist():
            if not info.filename.lower().endswith(".dta"):
                continue
            try:
                with zf.open(info) as f:
                    meta = dta_meta(f.read(2048))
            except Exception as e:  # noqa: BLE001
                print(f"    [err] {info.filename}: {e}")
                continue
            if not meta:
                continue
            rel, nvar, nobs = meta
            rows.append((info.filename, rel, nvar, nobs, info.file_size))
    print(f"\n=== {label} ===  dta 表数: {len(rows)}")
    print(f"    {'表文件':<62} {'变量数':>6} {'观测数':>9} {'大小MB':>8}")
    for fn, _rel, nvar, nobs, size in sorted(rows, key=lambda r: -r[3]):
        short = fn.split("/")[-1]
        y = YEAR_RE.search(short)
        tag = f"{y.group(1).upper()}{y.group(2)}" if y else ""
        print(f"    {short:<62} {nvar:>6} {nobs:>9} {size / 1048576:>8.1f}  {tag}")
    tot_var = sum(r[2] for r in rows)
    tot_obs = sum(r[3] for r in rows)
    print(f"    合计: 变量 {tot_var} 个 | 观测 {tot_obs:,} 行")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if "--dump" in sys.argv:
        # 调试：打印第一个 dta 的文件头字节
        zp = DATASET_ROOT / "CFPS" / "2010" / "Stata14.zip"
        zf = zipfile.ZipFile(zp)
        info = next(i for i in zf.infolist() if i.filename.endswith("cfps2010comm_201906.dta"))
        with zf.open(info) as f:
            head = f.read(64)
        print(f"file: {info.filename}")
        print(f"hex : {head.hex(' ')}")
        print(f"repr: {head!r}")
        return

    for p in DATASET_DIRS:
        if p.is_dir():
            zips = sorted(p.rglob("*.zip"))
            if not zips:
                print(f"[skip] {p} 无 zip（可能为 rar/7z，需外部工具）")
            for z in zips:
                scan_zip(z, f"{p.name} / {z.name}")
        elif p.exists():
            scan_zip(p, p.name)
        else:
            print(f"[missing] {p}")


if __name__ == "__main__":
    main()
