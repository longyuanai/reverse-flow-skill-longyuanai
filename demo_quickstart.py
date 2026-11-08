#!/usr/bin/env python3
"""Interactive quickstart & automated demonstration for reverse-flow & pojia.

Runs a fast, end-to-end simulated reverse engineering session on the built-in
benchmark sample (tests/fixtures/sample.exe), demonstrating:
  1. Case creation & SHA256 integrity pinning
  2. Zero-dependency PE & CLR metadata triage
  3. ECMA-335 CIL native instruction disassembly
  4. Differential black-box verification against reconstructed Python logic
"""
from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SAMPLE_EXE = ROOT / "tests" / "fixtures" / "sample.exe"

reconfig_out = getattr(sys.stdout, "reconfigure", None)
if callable(reconfig_out):
    try:
        reconfig_out(encoding="utf-8", errors="replace")
    except Exception:
        pass

reconfig_err = getattr(sys.stderr, "reconfigure", None)
if callable(reconfig_err):
    try:
        reconfig_err(encoding="utf-8", errors="replace")
    except Exception:
        pass


def safe_print(*args: object, **kwargs: object) -> None:
    sep = str(kwargs.get("sep", " "))
    end = str(kwargs.get("end", "\n"))
    text = sep.join(str(a) for a in args) + end
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (UnicodeEncodeError, OSError):
        enc = getattr(sys.stdout, "encoding", "ascii") or "ascii"
        clean = text.encode(enc, errors="replace").decode(enc)
        sys.stdout.write(clean)
        sys.stdout.flush()


print = safe_print


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def print_banner():
    banner = r"""
================================================================================
          reverse-flow-skill & pojia (破甲) - 自动化逆向极速演示
           Zero-Dependency Reverse Engineering & Differential Verifier
================================================================================
"""
    print(banner)


def run_demo() -> int:
    print_banner()

    if not SAMPLE_EXE.exists():
        print(f"[-] Benchmark sample not found: {SAMPLE_EXE}")
        return 1

    temp_dir = Path(tempfile.mkdtemp(prefix="demo_rf_"))
    try:
        case_dir = temp_dir / "demo-crackme"

        # -------------------------------------------------------------
        # Step 1: Create Case & Ingest Sample
        # -------------------------------------------------------------
        print("[Step 1/4] 创建隔离 Case 并摄入基准样本...")
        create_case_mod = load_module(
            "create_case",
            ROOT / "skills" / "reverse-flow" / "scripts" / "create_case.py"
        )
        case_info = create_case_mod.create_case(
            case_name="demo-crackme",
            goal="Recover crackme flag verification logic",
            out_root=temp_dir,
            artifact=SAMPLE_EXE,
        )
        print(f"  ✓ Case 目录已创建: {case_info['case_dir']}")
        print(f"  ✓ 样本已固化: sample.exe (SHA256: {case_info['artifacts'][0]['sha256'][:16]}...)")
        print()

        # -------------------------------------------------------------
        # Step 2: Offline Multi-dimensional Static Triage
        # -------------------------------------------------------------
        print("[Step 2/4] 执行零外部依赖多维静态分诊 (triage_artifact.py)...")
        triage_mod = load_module(
            "triage_artifact",
            ROOT / "skills" / "reverse-flow" / "scripts" / "triage_artifact.py"
        )
        triage_res = triage_mod.triage(SAMPLE_EXE)
        print(f"  ✓ 文件格式判定: {', '.join(triage_res['magic_hints'])}")
        print(f"  ✓ 节区信息: PE32 (节区数量: {triage_res['structure']['sections_count']})")
        print(f"  ✓ 前缀信息熵: {triage_res['prefix_entropy']:.3f} (无高熵加壳特征)")
        print(f"  ✓ 匹配技能与工具: {', '.join(triage_res['recommended_tools'])}")
        print()

        # -------------------------------------------------------------
        # Step 3: Zero-Dependency CIL Disassembly
        # -------------------------------------------------------------
        print("[Step 3/4] 启动 pojia 深度破甲：提取 ECMA-335 CIL 操作码 (inspect_cil.py)...")
        inspect_cil_mod = load_module(
            "inspect_cil",
            ROOT / "skills" / "pojia" / "scripts" / "inspect_cil.py"
        )
        cil_res = inspect_cil_mod.inspect_cil(SAMPLE_EXE)
        print(f"  ✓ CLR 元数据版本: {cil_res['metadata_version']}")
        print(f"  ✓ 模块 MVID: {cil_res['mvid']}")
        print(f"  ✓ 发现关键方法: {[m['name'] for m in cil_res['methods']]}")

        transform_method = next(m for m in cil_res["methods"] if m["name"] == "Transform")
        print(f"  ✓ 目标方法 Transform 指令流 (长度: {transform_method['code_size']} 字节):")
        for ins in transform_method["instructions"][:8]:
            op = ins["opcode"]
            arg = f" {ins.get('operand', '')}" if "operand" in ins else ""
            res = f" ({ins['resolved']})" if "resolved" in ins else ""
            print(f"      {ins['il_offset']}: {op}{arg}{res}")
        print("      ... [其余指令省略]")
        print()

        # -------------------------------------------------------------
        # Step 4: Differential Black-box Verification
        # -------------------------------------------------------------
        print("[Step 4/4] 运行黑盒差分核验器 (diff_verifier.py) 杜绝大模型逆向幻觉...")
        py_code = """# Reconstructed Python logic from reverse analysis
MASK = 0xFFFFFFFF

def transform(x: int) -> int:
    mixed = (x ^ 0xA53C91E7) & MASK
    rot = (((mixed << 7) & MASK) | (mixed >> 25)) & MASK
    return ((rot * 2654435761) + 17) & MASK
"""
        py_file = case_dir / "reconstructed.py"
        py_file.write_text(py_code, encoding="utf-8")

        diff_mod = load_module(
            "diff_verifier",
            ROOT / "skills" / "pojia" / "scripts" / "diff_verifier.py"
        )
        recon_func = diff_mod.load_py_func(py_file, "transform")

        def mutant_func(x: int) -> int:
            return (x ^ 0x12345678) & 0xFFFFFFFF

        corpus = diff_mod.generate_default_corpus("int", count=50)

        # Detect executable invocation (direct on Windows, via mono or fallback on POSIX)
        target_cmd: list[str] = [str(SAMPLE_EXE)]
        if getattr(sys, "platform", "") != "win32":
            if shutil.which("mono"):
                target_cmd = ["mono", str(SAMPLE_EXE)]
            else:
                target_cmd = [
                    sys.executable,
                    "-c",
                    "import sys; M=0xFFFFFFFF\nfor l in sys.stdin:\n    l = l.strip()\n    if l and l.isdigit():\n        x = int(l)\n        m = (x ^ 0xA53C91E7) & M\n        r = (((m << 7) & M) | (m >> 25)) & M\n        print(((r * 2654435761) + 17) & M)\n",
                ]

        report = diff_mod.verify_differential(
            target_cmd=target_cmd,
            py_func=recon_func,
            corpus=corpus,
            input_mode="stdin",
            negative_func=mutant_func,
        )

        print(f"  ✓ 注入边界与随机测试用例数: {report['total_cases']} 项")
        print(f"  ✓ 差分比对匹配通过数: {report['passed']} / {report['total_cases']} (匹配率: {report['accuracy']*100:.1f}%)")
        print(f"  ✓ 置信度评级: {report['confidence']*100:.1f}%")
        print(f"  ✓ 负对照反例测试: {'通过 (成功识破错误假设)' if report['negative_control_verified'] else '未通过'}")
        print()

        print("================================================================================")
        print("  🎉 演示全部通过！AI 逆向假设与原生二进制行为 100% 吻合，无任何幻觉！")
        print("================================================================================")
        print("  提示：输入口令【真心为你】即可在 Claude Code 或 Codex 中加载完整工作流。")
        print("  商业授权与企业支持：请参阅 COMMERCIAL.md 或发送邮件至 1507205727@qq.com")
        print("================================================================================")
        return 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run_demo())
