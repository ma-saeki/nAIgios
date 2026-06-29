#!/usr/bin/env python3
"""
nAIgios - UserPromptSubmit hook
オープンクエスチョンを検知し、prompt-perfect 自動起動を Claude に指示する。
"""
import glob
import json
import os
import subprocess
import sys

FLAG_FILE = os.path.expanduser("~/.claude/.naigios_active")
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
EVAL_PROMPT_FILE = os.path.join(SKILL_DIR, "eval_prompt.txt")
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
CONFIG_FILE = os.path.expanduser("~/.claude/.naigios_config")
OPEN_THRESHOLD = 70
LOG_FILE = os.path.expanduser("~/.claude/.naigios_debug.log")


def get_model(transcript_path: str) -> str:
    """モデル解決: 設定ファイル → transcript自動検出 → デフォルト"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("model="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            pass
    if transcript_path:
        try:
            with open(transcript_path, encoding="utf-8") as f:
                lines = [l.strip() for l in f if l.strip()]
            for line in reversed(lines):
                entry = json.loads(line)
                if entry.get("type") == "assistant":
                    model = entry.get("message", {}).get("model")
                    if model:
                        return model
        except Exception:
            pass
    return DEFAULT_MODEL


def log(msg: str) -> None:
    import datetime
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")


def get_last_assistant_text(transcript_path: str) -> str:
    """transcript JSONL から直前の assistant メッセージのテキストを取得する。"""
    last_text = ""
    try:
        with open(transcript_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "assistant":
                        content = entry.get("message", {}).get("content", [])
                        if isinstance(content, list):
                            texts = [
                                c["text"] for c in content
                                if isinstance(c, dict) and c.get("type") == "text"
                            ]
                            if texts:
                                last_text = " ".join(texts)
                except Exception:
                    continue
    except Exception:
        pass
    return last_text


def main() -> None:
    # 再帰ループ防止: このプロセス自身が claude -p から呼ばれた場合はスキップ
    if os.environ.get("NAIGIOS_EVALUATING"):
        sys.exit(0)

    log("hook invoked")

    # nAIgios が有効か確認
    if not os.path.exists(FLAG_FILE):
        sys.exit(0)

    # stdin から hook イベント JSON を読む
    try:
        event = json.load(sys.stdin)
        prompt = event.get("prompt", "")
        transcript_path = event.get("transcript_path", "")
    except Exception as e:
        log(f"exit: stdin parse error: {e}")
        sys.exit(0)

    log(f"prompt: {prompt[:50]!r}")

    # スキップ条件: 空・スラッシュコマンド
    if not prompt or prompt.strip().startswith("/"):
        log("exit: skip condition")
        sys.exit(0)

    # 直前の assistant メッセージを取得してコンテキストとして渡す
    prev_assistant = ""
    if transcript_path:
        prev_assistant = get_last_assistant_text(transcript_path)
        log(f"prev_assistant: {prev_assistant[:60]!r}")

    # 評価プロンプトを読み込み、コンテキストとユーザーメッセージを挿入する
    try:
        with open(EVAL_PROMPT_FILE, encoding="utf-8") as f:
            template = f.read()
        eval_prompt = template.replace("$prev_assistant", prev_assistant or "（なし）") + prompt
    except Exception as e:
        log(f"exit: eval_prompt read error: {e}")
        sys.exit(0)

    # claude CLI のパスを特定
    # 優先順: CLAUDE_CODE_EXECPATH env var → VSCode 拡張 glob → PATH
    claude_bin = None
    execpath = os.environ.get("CLAUDE_CODE_EXECPATH", "")
    if execpath and os.path.isfile(execpath):
        claude_bin = execpath
    if not claude_bin:
        candidates = glob.glob(
            os.path.expanduser("~/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")
        )
        if candidates:
            claude_bin = sorted(candidates)[-1]
    if not claude_bin:
        import shutil
        claude_bin = shutil.which("claude")
    if not claude_bin:
        log("exit: claude binary not found")
        sys.exit(0)
    log(f"claude_bin: {claude_bin}")

    # claude -p で評価
    # NAIGIOS_EVALUATING=1 を渡して hook の再帰起動を防ぐ
    env = os.environ.copy()
    env["NAIGIOS_EVALUATING"] = "1"
    try:
        model = get_model(transcript_path)
        log(f"model: {model}")
        result = subprocess.run(
            [claude_bin, "-p", eval_prompt, "--model", model],
            capture_output=True, text=True, timeout=30, env=env,
        )
        raw = result.stdout.strip()
        log(f"claude output: {raw[:80]!r}")
        if result.returncode != 0:
            log(f"claude stderr: {result.stderr[:200]!r}")
    except Exception as e:
        log(f"exit: claude run error: {e}")
        sys.exit(0)

    # レスポンスをパース
    try:
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.rsplit("```", 1)[0].strip()
        eval_result = json.loads(raw)
        verdict = eval_result["verdict"]
        score = eval_result["score"]
        reason = eval_result.get("reason", "")
        missing = eval_result.get("missing", [])
        signals = eval_result.get("signals", [])
    except Exception as e:
        log(f"exit: parse error: {e}, raw={raw[:100]!r}")
        sys.exit(0)

    log(f"verdict: {verdict}, score: {score}")
    if verdict == "OPEN":
        missing_str = "、".join(missing) if missing else "なし"
        signals_str = "、".join(signals) if signals else "なし"
        print(f"""[nAIgios ALERT] スコア {score}/100 — オープンクエスチョン検知

検出シグナル: {signals_str}
不足情報: {missing_str}
判定理由: {reason}

【指示】このアラートが表示された場合、通常の回答を行う前に、まず prompt-perfect スキルの手順に従い、ユーザーのリクエストを批評・改善してください。改善されたリクエスト案を提示したうえで、ユーザーに「このまま進めるか、fork conversation で改善版を使って再試行するか」を確認してください。
nAIgios に関する説明・補足を返答に含める場合は `[nAIgios]: <説明>` の形式で通常の返答と分離すること。""")

    sys.exit(0)


if __name__ == "__main__":
    main()
